from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, DetailView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.conf import settings
from .models import Booking
import uuid
from decimal import Decimal
import json
import logging

logger = logging.getLogger(__name__)
try:
    import razorpay
except Exception:
    razorpay = None

class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'bookings/booking_list.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        from bookings.pricing_calculator import calculate_pricing
        context = super().get_context_data(**kwargs)
        for booking in context.get('object_list', []):
            pricing = calculate_pricing(
                booking=booking,
                promo_code=booking.promo_code,
                wallet_apply_amount=None,
                user=self.request.user,
            )
            booking.display_total_payable = pricing['total_payable']
            booking.display_taxes_and_fees = pricing['taxes_and_fees']
            booking.gst_rate_percent = int(pricing['gst_rate'] * 100)
        return context


@login_required
def my_bookings(request):
    """Function wrapper to provide a named view for My Bookings navigation."""
    return BookingListView.as_view()(request)

class BookingDetailView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = 'bookings/booking_detail.html'

    def get_object(self, queryset=None):
        booking_id = self.kwargs.get('booking_id')
        booking = get_object_or_404(Booking, booking_id=booking_id, user=self.request.user)
        # Enforce expiry on access so UI reflects actual state
        booking.check_reservation_timeout()
        return booking
    
    def get_context_data(self, **kwargs):
        from bookings.pricing_calculator import calculate_pricing
        from payments.models import Wallet
        from decimal import Decimal
        
        context = super().get_context_data(**kwargs)
        booking = self.object
        
        # Calculate pricing using unified calculator
        pricing = calculate_pricing(
            booking=booking,
            promo_code=booking.promo_code,
            wallet_apply_amount=None,  # Don't apply wallet on detail page
            user=self.request.user
        )
        logger.info("[DETAIL_PAGE_PRICING] booking=%s base=%.2f promo=%.2f subtotal=%.2f gst=%.2f total=%.2f status=%s",
                    booking.booking_id, pricing['base_amount'], pricing['promo_discount'],
                    pricing['subtotal_after_promo'], pricing['gst_amount'], pricing['total_payable'],
                    booking.status)
        
        # Get wallet balance for display
        wallet_balance = Decimal('0.00')
        try:
            wallet = Wallet.objects.get(user=self.request.user, is_active=True)
            wallet_balance = wallet.balance
        except Wallet.DoesNotExist:
            pass
        
        context.update({
            'base_amount': pricing['base_amount'],
            'promo_discount': pricing['promo_discount'],
            'subtotal_after_promo': pricing['subtotal_after_promo'],
            'platform_fee': pricing['platform_fee'],
            'gst_rate_percent': int(pricing['gst_rate'] * 100),
            'gst_amount': pricing['gst_amount'],
            'taxes_and_fees': pricing['taxes_and_fees'],
            'total_payable': pricing['total_payable'],
            'wallet_balance': wallet_balance,
        })
        
        return context



def booking_confirmation(request, booking_id):
    """Show booking confirmation and proceed to payment.

    Accepts UUID booking_id. Works for both authenticated and unauthenticated users.
    
    RULE: Guest booking does NOT require login
    - Unauthenticated users can complete booking as guests
    - Login shown as optional upsell (better offers, order history)
    - Email-verified users see full confirmation page
    - Guests see minimal confirmation + payment button
    
    POST from this page redirects to the payment page.
    """
    from django.contrib import messages
    from django.contrib.messages import get_messages
    from bookings.pricing_calculator import calculate_pricing
    from core.models import PromoCode
    from payments.models import Wallet
    
    # Clear any auth/login messages before entering booking flow
    if request.user.is_authenticated:
        storage = get_messages(request)
        storage.used = True
    
    # Get booking (works for both authenticated and unauthenticated)
    try:
        booking = get_object_or_404(Booking, booking_id=booking_id)
    except:
        messages.error(request, 'Booking not found. Please check your booking ID.')
        return redirect('hotels:hotel_list')
    
    # IMPORTANT: Ensure booking belongs to current user (if authenticated)
    if request.user.is_authenticated and booking.user and booking.user != request.user:
        messages.error(request, 'You do not have permission to view this booking.')
        return redirect('hotels:hotel_list')
    
    # EMAIL VERIFICATION: OPTIONAL FOR GUESTS (not required)
    # If user is authenticated but not email-verified, ask them to verify
    if request.user.is_authenticated and not request.user.email_verified_at:
        messages.warning(request, 'Verify your email to unlock exclusive offers and booking history.')
        # Still allow booking continuation (don't block)
    
    # BLOCKER FIX: If already confirmed, redirect to detail
    if booking.status == 'confirmed':
        if request.user.is_authenticated:
            return redirect('bookings:booking-detail', booking_id=booking.booking_id)
        else:
            # For guests, show confirmation page anyway
            pass

    if booking.check_reservation_timeout():
        messages.error(request, 'Reservation hold expired. Please start a new booking.')
        target_hotel = getattr(getattr(booking, 'hotel_details', None), 'room_type', None)
        if target_hotel and target_hotel.hotel_id:
            return redirect('hotels:hotel_detail', pk=target_hotel.hotel_id)
        return redirect('hotels:hotel_list')

    # Handle promo code application (AJAX or POST)
    promo_code = None
    promo_error = None
    if request.method == 'POST' and 'remove_promo' in request.POST:
        booking.promo_code = None
        booking.save(update_fields=['promo_code'])
        logger.info("[CONFIRM_PROMO_REMOVED] booking=%s", booking.booking_id)
    elif request.method == 'POST' and 'promo_code' in request.POST:
        promo_code_str = request.POST.get('promo_code', '').strip().upper()
        if promo_code_str:
            try:
                promo_code = PromoCode.objects.get(code=promo_code_str, is_active=True)
                is_valid, error_msg = promo_code.is_valid()
                if not is_valid:
                    promo_error = error_msg
                    promo_code = None
                    logger.warning("[CONFIRM_PROMO_INVALID] booking=%s code=%s error=%s", booking.booking_id, promo_code_str, error_msg)
                else:
                    # Save promo to booking
                    booking.promo_code = promo_code
                    booking.save(update_fields=['promo_code'])
                    logger.info("[CONFIRM_PROMO_APPLIED] booking=%s code=%s", booking.booking_id, promo_code_str)
            except PromoCode.DoesNotExist:
                promo_error = "Invalid promo code"
                logger.warning("[CONFIRM_PROMO_NOT_FOUND] booking=%s code=%s", booking.booking_id, promo_code_str)
    elif booking.promo_code:
        promo_code = booking.promo_code

    # Calculate pricing using unified function
    pricing = calculate_pricing(
        booking=booking,
        promo_code=promo_code,
        wallet_apply_amount=None,  # Not applied on confirm page
        user=request.user
    )
    
    # Get wallet balance for display
    wallet_balance = Decimal('0.00')
    try:
        wallet = Wallet.objects.get(user=request.user, is_active=True)
        wallet_balance = wallet.balance
    except Wallet.DoesNotExist:
        pass
    
    logger.info("[CONFIRM_PAGE_PRICING] booking=%s base=%.2f promo=%.2f subtotal=%.2f gst=%.2f total=%.2f wallet_balance=%.2f", 
                booking.booking_id, pricing['base_amount'], pricing['promo_discount'], 
                pricing['subtotal_after_promo'], pricing['gst_amount'], pricing['total_payable'],
                wallet_balance)

    if request.method == 'POST' and 'proceed_to_payment' in request.POST:
        return redirect(reverse('bookings:booking-payment', kwargs={'booking_id': booking.booking_id}))

    # Build return URL preserving context (dates, room, guests, rooms, meal plan)
    booking_return_url = None
    hotel_booking = getattr(booking, 'hotel_details', None)
    if hotel_booking and getattr(hotel_booking, 'room_type', None):
        query_parts = [
            f"checkin={hotel_booking.check_in}",
            f"checkout={hotel_booking.check_out}",
            f"room_type={hotel_booking.room_type.id}",
            f"guests={hotel_booking.number_of_adults}",
            f"rooms={hotel_booking.number_of_rooms}",
        ]
        if hotel_booking.meal_plan:
            query_parts.append(f"meal_plan_id={hotel_booking.meal_plan.id}")
        booking_return_url = f"/hotels/{hotel_booking.room_type.hotel_id}/?" + "&".join(query_parts)

    # Derive line items for transparency
    room_line_amount = pricing['base_amount']
    meal_plan_total = Decimal('0.00')
    meal_plan_name = None
    nights = getattr(hotel_booking, 'total_nights', None) or 0
    rooms = getattr(hotel_booking, 'number_of_rooms', None) or 0
    base_room_amount = pricing['base_amount']
    if hotel_booking and getattr(hotel_booking, 'room_type', None):
        try:
            base_room_amount = Decimal(str(hotel_booking.room_type.get_effective_price())) * rooms * nights
        except Exception:
            base_room_amount = pricing['base_amount']

    room_line_amount = base_room_amount
    if hotel_booking and hotel_booking.meal_plan:
        try:
            total_plan_price = hotel_booking.meal_plan.calculate_total_price(rooms, nights)
            meal_plan_total = max(Decimal(str(total_plan_price)) - base_room_amount, Decimal('0.00'))
        except Exception:
            meal_plan_total = Decimal('0.00')
        # CRITICAL FIX: meal_plan is RoomMealPlan object, access .meal_plan.name
        meal_plan_name = hotel_booking.meal_plan.meal_plan.name if hasattr(hotel_booking.meal_plan, 'meal_plan') else str(hotel_booking.meal_plan)

    # Normalize so room + meal plan equals base amount even after discounts
    items_sum = room_line_amount + meal_plan_total
    if items_sum != pricing['base_amount']:
        room_line_amount = pricing['base_amount'] - meal_plan_total

    context = {
        'booking': booking,
        'base_amount': pricing['base_amount'],
        'promo_discount': pricing['promo_discount'],
        'subtotal_after_promo': pricing['subtotal_after_promo'],
        'platform_fee': pricing['platform_fee'],
        'gst_rate_percent': int(pricing['gst_rate'] * 100),
        'gst_amount': pricing['gst_amount'],
        'taxes_and_fees': pricing['taxes_and_fees'],
        'total_payable': pricing['total_payable'],
        'wallet_balance': wallet_balance,
        'promo_code': promo_code,
        'promo_error': promo_error,
        'booking_return_url': booking_return_url,
        'room_line_amount': room_line_amount,
        'meal_plan_total': meal_plan_total,
        'meal_plan_name': meal_plan_name,
        'line_nights': nights,
        'line_rooms': rooms,
    }
    return render(request, 'bookings/confirmation.html', context)




def payment_page(request, booking_id):
    """Render the payment page with a Razorpay order (test-friendly).

    Works for both authenticated and guest users.
    - Authenticated users can use wallet + other payment methods
    - Guests can only use direct payment (card/UPI/net banking)
    
    RULE: Guest booking does NOT require login
    Email verification is OPTIONAL (not required)
    
    If Razorpay credentials are not configured, fall back to a dummy order id so
    the template renders without breaking local flows.
    
    BLOCKER FIX: Block access if booking is already confirmed.
    """
    # Clear any auth/login messages before payment flow
    from django.contrib.messages import get_messages
    from django.contrib import messages
    from bookings.pricing_calculator import calculate_pricing
    if request.user.is_authenticated:
        storage = get_messages(request)
        storage.used = True
    
    from payments.models import Wallet
    from decimal import Decimal
    
    # Get booking (works for both authenticated and unauthenticated)
    try:
        booking = get_object_or_404(Booking, booking_id=booking_id)
    except:
        messages.error(request, 'Booking not found.')
        return redirect('hotels:hotel_list')
    
    # Ensure booking belongs to current user (if authenticated)
    if request.user.is_authenticated and booking.user and booking.user != request.user:
        messages.error(request, 'You do not have permission to access this booking.')
        return redirect('hotels:hotel_list')

    # HARD GUARD: Block payment if booking is already confirmed/completed (403 Forbidden)
    if booking.status in ['confirmed', 'completed', 'cancelled', 'expired', 'refunded', 'deleted']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(
            f'Booking is in {booking.get_status_display()} status. Payment is no longer allowed.'
        )

    if booking.check_reservation_timeout():
        messages.error(request, 'Reservation hold expired. Please start a new booking.')
        target_hotel = getattr(getattr(booking, 'hotel_details', None), 'room_type', None)
        if target_hotel and target_hotel.hotel_id:
            return redirect('hotels:hotel_detail', pk=target_hotel.hotel_id)
        return redirect('hotels:hotel_list')

    # Get wallet and determine wallet application amount
    wallet_balance = Decimal('0.00')
    wallet_apply_amount = Decimal('0.00')
    available_cashback = Decimal('0.00')
    
    try:
        wallet = Wallet.objects.get(user=request.user, is_active=True)
        wallet_balance = wallet.balance
        available_cashback = wallet.get_available_balance() - wallet_balance
    except Wallet.DoesNotExist:
        pass

    # Default behaviour: auto-apply wallet when available unless explicitly disabled
    use_wallet_param = request.GET.get('use_wallet')
    use_wallet = True if (use_wallet_param is None and wallet_balance > Decimal('0.00')) else use_wallet_param == 'true'

    # First pass: pricing without wallet to know payable
    pricing_preview = calculate_pricing(
        booking=booking,
        promo_code=booking.promo_code,
        wallet_apply_amount=Decimal('0.00'),
        user=request.user
    )

    if use_wallet and wallet_balance > Decimal('0.00'):
        wallet_apply_amount = min(wallet_balance, pricing_preview['total_payable'])

    # Final pricing with wallet applied if any
    pricing = calculate_pricing(
        booking=booking,
        promo_code=booking.promo_code,
        wallet_apply_amount=wallet_apply_amount,
        user=request.user
    )
    logger.info("[PAYMENT_PAGE_PRICING] booking=%s base=%.2f promo=%.2f subtotal=%.2f gst=%.2f total=%.2f wallet_balance=%.2f wallet_applied=%.2f gateway=%.2f use_wallet=%s",
                booking.booking_id, pricing['base_amount'], pricing['promo_discount'],
                pricing['subtotal_after_promo'], pricing['gst_amount'], pricing['total_payable'],
                wallet_balance, pricing['wallet_applied'], pricing['gateway_payable'], use_wallet)

    # ASSERTION: Verify UI condition will be correct
    logger.info("[PAYMENT_UI_ASSERT] booking=%s wallet_balance=%.2f wallet_applied=%.2f total=%.2f gateway_payable=%.2f WILL_SHOW_GATEWAY=%s",
                booking.booking_id, wallet_balance, pricing['wallet_applied'], pricing['total_payable'],
                pricing['gateway_payable'], pricing['gateway_payable'] > Decimal('0.01'))

    razorpay_key = settings.RAZORPAY_KEY_ID or 'rzp_test_dummy_key'
    order_id = f"order_{uuid.uuid4().hex[:20]}"

    # Create real order if keys and SDK are available (use gateway_payable)
    if razorpay and settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order = client.order.create(data={
                'amount': int(float(pricing['gateway_payable']) * 100),  # Gateway amount (after wallet)
                'currency': 'INR',
                'receipt': str(booking.booking_id),
                'notes': {'booking_id': str(booking.booking_id), 'user_id': str(request.user.id)}
            })
            order_id = order.get('id', order_id)
        except Exception:
            # Keep fallback order_id for non-blocking local runs
            pass

    # Include hotel booking details (room type and meal plan)
    hotel_booking = getattr(booking, 'hotel_details', None)
    room_type = getattr(hotel_booking, 'room_type', None) if hotel_booking else None
    meal_plan = getattr(hotel_booking, 'meal_plan', None) if hotel_booking else None

    context = {
        'booking': booking,
        'hotel_booking': hotel_booking,
        'room_type': room_type,
        'meal_plan': meal_plan,
        'base_amount': pricing['base_amount'],
        'promo_discount': pricing['promo_discount'],
        'subtotal_after_promo': pricing['subtotal_after_promo'],
        'platform_fee': pricing['platform_fee'],
        'gst_rate_percent': int(pricing['gst_rate'] * 100),
        'gst_amount': pricing['gst_amount'],
        'taxes_and_fees': pricing['taxes_and_fees'],
        'total_payable': pricing['total_payable'],
        'wallet_balance': wallet_balance,
        'wallet_applied': pricing['wallet_applied'],
        'gateway_payable': pricing['gateway_payable'],
        'available_cashback': available_cashback,
        'razorpay_key': razorpay_key,
        'order_id': order_id,
        'use_wallet': use_wallet,
        'reservation_seconds_left': booking.reservation_seconds_left,  # Timer persistence (property, not method)
    }
    return render(request, 'payments/payment.html', context)


@login_required
def cancel_booking(request, booking_id):
    """Cancel a booking with refund + inventory release (idempotent, atomic)."""
    from django.contrib import messages
    from django.db import transaction
    from django.utils import timezone
    from decimal import Decimal
    from payments.models import Wallet, WalletTransaction
    from hotels.channel_manager_service import release_inventory_on_failure

    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)

    # Idempotent guards
    if booking.status == 'cancelled':
        messages.info(request, 'Booking is already cancelled.')
        return redirect('bookings:booking-detail', booking_id=booking.booking_id)
    if booking.status in ['expired', 'deleted', 'refunded', 'completed']:
        messages.error(request, f'Cannot cancel booking in {booking.get_status_display()} status')
        return redirect('bookings:booking-detail', booking_id=booking.booking_id)

    # Only allow cancellation of confirmed, reserved, or payment_pending
    if booking.status not in ['confirmed', 'payment_pending', 'reserved']:
        messages.error(request, f'Cannot cancel booking in {booking.get_status_display()} status')
        return redirect('bookings:booking-detail', booking_id=booking.booking_id)

    # Check cancellation rules
    hotel_booking = getattr(booking, 'hotel_details', None) or getattr(booking, 'hotel_booking', None)
    check_in_date = hotel_booking.check_in if hotel_booking else None
    hotel = hotel_booking.room_type.hotel if hotel_booking and hotel_booking.room_type else None

    if not hotel_booking or not hotel or not check_in_date:
        messages.error(request, 'Unable to determine hotel or check-in date')
        return redirect('bookings:booking-detail', booking_id=booking.booking_id)

    can_cancel, reason = hotel.can_cancel_booking(check_in_date)
    if not can_cancel:
        messages.error(request, f'Cannot cancel: {reason}')
        return redirect('bookings:booking-detail', booking_id=booking.booking_id)

    # Process cancellation atomically
    try:
        with transaction.atomic():
            # Lock booking row
            booking = Booking.objects.select_for_update().get(pk=booking.pk)

            if booking.status == 'cancelled':
                messages.info(request, 'Booking is already cancelled.')
                return redirect('bookings:booking-detail', booking_id=booking.booking_id)
            if booking.status in ['expired', 'deleted', 'refunded', 'completed']:
                messages.error(request, f'Cannot cancel booking in {booking.get_status_display()} status')
                return redirect('bookings:booking-detail', booking_id=booking.booking_id)

            # Calculate refund
            refund_amount = Decimal(str(booking.paid_amount)) * Decimal(hotel.refund_percentage) / Decimal('100')

            # Update booking
            booking.status = 'cancelled'
            booking.cancelled_at = timezone.now()
            booking.save(update_fields=['status', 'cancelled_at', 'updated_at'])

            # Refund to wallet if amount > 0
            if refund_amount > 0 and hotel.refund_mode == 'WALLET':
                wallet, _ = Wallet.objects.select_for_update().get_or_create(user=request.user, defaults={'balance': Decimal('0.00')})
                balance_before = wallet.balance
                wallet.balance += refund_amount
                wallet.save(update_fields=['balance', 'updated_at'])

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='refund',
                    amount=refund_amount,
                    balance_before=balance_before,
                    balance_after=wallet.balance,
                    description=f'Cancellation refund for booking {booking.booking_id}',
                    booking=booking,
                    status='success',
                    payment_gateway='internal',
                )

            # Release inventory regardless of status
            release_inventory_on_failure(booking)

            # MANDATORY LOG: Prove state changed
            logger.info("[BOOKING_CANCELLED] booking=%s old_status=%s new_status=cancelled refund_amount=%.2f refund_mode=%s inventory_released=true",
                        booking.booking_id, booking.status, refund_amount, hotel.refund_mode)

        payload = {
            'event': 'booking_cancelled',
            'booking_id': str(booking.booking_id),
            'refund_amount': float(refund_amount),
            'refund_mode': hotel.refund_mode,
        }
        logger.info("[NOTIFICATION_EMAIL] payload=%s", payload)
        logger.info("[NOTIFICATION_SMS] payload=%s", payload)
        logger.info("[NOTIFICATION_WHATSAPP] payload=%s", payload)

        messages.success(request, f'Booking cancelled. Refund of ₹{refund_amount} processed to wallet.')
        return redirect('bookings:booking-detail', booking_id=booking.booking_id)

    except Exception as e:
        messages.error(request, f'Cancellation failed: {str(e)}')
        return redirect('bookings:booking-detail', booking_id=booking.booking_id)


def create_razorpay_order(request):
    # Inform callers to use the dedicated payments endpoints
    return JsonResponse({"status": "error", "message": "Use payments:create-payment-order API"}, status=405)


def verify_payment(request):
    # Inform callers to use the dedicated payments endpoints
    return JsonResponse({"status": "error", "message": "Use payments:verify-payment API"}, status=405)


@login_required
@require_http_methods(["POST"])
def confirm_wallet_only_booking(request, booking_id):
    """Confirm booking when wallet balance covers full amount (no gateway needed).
    
    CRITICAL: Uses unified finalize_booking_payment() function.
    No duplicate payment logic anywhere.
    """
    import json
    from bookings.payment_finalization import finalize_booking_payment
    from bookings.pricing_calculator import calculate_pricing
    
    try:
        data = json.loads(request.body)
        wallet_applied = Decimal(str(data.get('wallet_applied', 0)))
        
        booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
        
        # Calculate pricing to verify amounts
        pricing = calculate_pricing(
            booking=booking,
            promo_code=booking.promo_code,
            wallet_apply_amount=wallet_applied,
            user=request.user
        )
        
        # Verify wallet covers full amount (no gateway needed)
        if pricing['gateway_payable'] > Decimal('0.01'):
            return JsonResponse({
                'status': 'error',
                'message': f'Wallet does not cover full amount. Gateway payment required: ₹{pricing["gateway_payable"]}'
            }, status=400)
        
        # Use unified finalization function
        result = finalize_booking_payment(
            booking=booking,
            payment_mode='wallet',
            wallet_applied=wallet_applied,
            gateway_amount=Decimal('0.00'),
            user=request.user
        )
        
        if result['status'] == 'success':
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error("[WALLET_ONLY_CONFIRM_ERROR] booking=%s error=%s", booking_id, str(e), exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Server error. Please try again.'}, status=500)



def get_booking_timer(request, booking_id):
    """API endpoint to get current booking timer status."""
    from django.http import JsonResponse
    from django.utils import timezone
    
    try:
        booking = Booking.objects.get(booking_id=booking_id, user=request.user)

        if booking.status in ['reserved', 'payment_pending']:
            deadline = booking.reservation_deadline
            if not deadline:
                return JsonResponse({'status': booking.status, 'remaining_seconds': 0})

            now = timezone.now()
            if deadline > now:
                remaining_seconds = int((deadline - now).total_seconds())
                return JsonResponse({
                    'status': 'active',
                    'expires_at': deadline.isoformat(),
                    'remaining_seconds': remaining_seconds,
                    'formatted_time': f"{remaining_seconds // 60}:{remaining_seconds % 60:02d}"
                })

            # Expired – mark, release inventory, and log
            booking.status = 'expired'
            booking.expires_at = deadline
            booking.save(update_fields=['status', 'expires_at'])
            from hotels.channel_manager_service import release_inventory_on_failure
            release_inventory_on_failure(booking)
            logger.info("[BOOKING_EXPIRED] booking=%s status=expired deadline=%s", booking.booking_id, deadline)
            return JsonResponse({'status': 'expired', 'remaining_seconds': 0})

        return JsonResponse({'status': booking.status, 'remaining_seconds': 0})

    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
