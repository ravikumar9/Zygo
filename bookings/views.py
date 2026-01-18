from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, DetailView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.conf import settings
from .models import Booking
import uuid
from decimal import Decimal
import json
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


@login_required
def my_bookings(request):
    """Function wrapper to provide a named view for My Bookings navigation."""
    return BookingListView.as_view()(request)

class BookingDetailView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = 'bookings/booking_detail.html'

    def get_object(self, queryset=None):
        booking_id = self.kwargs.get('booking_id')
        return get_object_or_404(Booking, booking_id=booking_id, user=self.request.user)

@login_required
def booking_confirmation(request, booking_id):
    """Show booking confirmation and proceed to payment.

    Accepts only UUID booking_id and ensures the booking belongs to the user.
    CRITICAL: User must have email_verified_at (mobile optional/deferred).
    POST from this page redirects to the payment page.
    """
    # Clear any auth/login messages before entering booking flow
    from django.contrib.messages import get_messages
    storage = get_messages(request)
    storage.used = True
    
    # ENFORCE EMAIL VERIFICATION (mobile optional/deferred)
    if not request.user.email_verified_at:
        from django.contrib import messages
        messages.error(request, 'Please verify your email before booking. Check your inbox for OTP.')
        request.session['pending_user_id'] = request.user.id
        request.session['pending_email'] = request.user.email
        request.session['pending_phone'] = getattr(request.user, 'phone', '')
        return redirect('users:verify-registration-otp')
    
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)

    if booking.check_reservation_timeout():
        from django.contrib import messages
        messages.error(request, 'Reservation hold expired. Please start a new booking.')
        target_hotel = getattr(getattr(booking, 'hotel_details', None), 'room_type', None)
        if target_hotel and target_hotel.hotel_id:
            return redirect('hotels:hotel_detail', pk=target_hotel.hotel_id)
        return redirect('hotels:hotel_list')

    if request.method == 'POST':
        return redirect(reverse('bookings:booking-payment', kwargs={'booking_id': booking.booking_id}))

    return render(request, 'bookings/confirmation.html', {
        'booking': booking,
    })


@login_required
def payment_page(request, booking_id):
    """Render the payment page with a Razorpay order (test-friendly).

    CRITICAL: User must have email_verified_at (mobile optional/deferred).
    If Razorpay credentials are not configured, fall back to a dummy order id so
    the template renders without breaking local flows.
    """
    # Clear any auth/login messages before payment flow
    from django.contrib.messages import get_messages
    storage = get_messages(request)
    storage.used = True
    
    # ENFORCE EMAIL VERIFICATION (mobile optional/deferred)
    if not request.user.email_verified_at:
        from django.contrib import messages
        messages.error(request, 'Please verify your email before booking. Check your inbox for OTP.')
        request.session['pending_user_id'] = request.user.id
        request.session['pending_email'] = request.user.email
        request.session['pending_phone'] = getattr(request.user, 'phone', '')
        return redirect('users:verify-registration-otp')
    
    from payments.models import Wallet
    from decimal import Decimal
    
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)

    # Block payment if booking is not payable
    if booking.status in ['cancelled', 'expired', 'completed', 'refunded', 'deleted', 'confirmed']:
        from django.contrib import messages
        messages.error(request, f'Booking is in {booking.get_status_display()} status and cannot be paid.')
        return redirect('bookings:booking-detail', booking_id=booking.booking_id)

    if booking.check_reservation_timeout():
        from django.contrib import messages
        messages.error(request, 'Reservation hold expired. Please start a new booking.')
        target_hotel = getattr(getattr(booking, 'hotel_details', None), 'room_type', None)
        if target_hotel and target_hotel.hotel_id:
            return redirect('hotels:hotel_detail', pk=target_hotel.hotel_id)
        return redirect('hotels:hotel_list')

    razorpay_key = settings.RAZORPAY_KEY_ID or 'rzp_test_dummy_key'
    order_id = f"order_{uuid.uuid4().hex[:20]}"

    # Create real order if keys and SDK are available
    if razorpay and settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order = client.order.create(data={
                'amount': int(float(booking.total_amount) * 100),
                'currency': 'INR',
                'receipt': str(booking.booking_id),
                'notes': {'booking_id': str(booking.booking_id), 'user_id': str(request.user.id)}
            })
            order_id = order.get('id', order_id)
        except Exception:
            # Keep fallback order_id for non-blocking local runs
            pass

    # Derive corporate discount from booking metadata (if any)
    corp_discount_amount = Decimal('0.00')
    corp_label = 'Corporate Discount'
    try:
        if booking.channel_reference:
            data = json.loads(booking.channel_reference)
            if isinstance(data, dict) and data.get('type') == 'corp':
                corp_discount_amount = Decimal(str(data.get('discount_amount', 0)))
                company = data.get('company') or data.get('domain')
                if company:
                    corp_label = f"Corporate Discount ({company})"
    except Exception:
        # Never block payment page due to malformed metadata
        corp_discount_amount = Decimal('0.00')
        corp_label = 'Corporate Discount'

    base_amount = Decimal(str(booking.total_amount)) + corp_discount_amount

    # Get wallet balance and available cashback
    wallet_balance = Decimal('0.00')
    available_cashback = Decimal('0.00')
    try:
        wallet = Wallet.objects.get(user=request.user, is_active=True)
        wallet_balance = wallet.balance
        available_cashback = wallet.get_available_balance() - wallet_balance
    except Wallet.DoesNotExist:
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
        'total_amount': booking.total_amount,
        'base_amount': base_amount,
        'gst_amount': 0,
        'discount_amount': corp_discount_amount,
        'discount_label': corp_label,
        'razorpay_key': razorpay_key,
        'order_id': order_id,
        'wallet_balance': wallet_balance,
        'available_cashback': available_cashback,
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
    check_in_date = None
    if hasattr(booking, 'hotel_booking') and booking.hotel_booking:
        check_in_date = booking.hotel_booking.check_in

    hotel = None
    if check_in_date and hasattr(booking, 'hotel_booking') and booking.hotel_booking:
        hotel = booking.hotel_booking.room_type.hotel

    if not hotel or not check_in_date:
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

