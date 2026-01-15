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

    context = {
        'booking': booking,
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


def create_razorpay_order(request):
    # Inform callers to use the dedicated payments endpoints
    return JsonResponse({"status": "error", "message": "Use payments:create-payment-order API"}, status=405)


def verify_payment(request):
    # Inform callers to use the dedicated payments endpoints
    return JsonResponse({"status": "error", "message": "Use payments:verify-payment API"}, status=405)

