from decimal import Decimal
import uuid
import logging

from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings

from .models import Booking
from bookings.services.booking_pricing_helper import (
    freeze_pricing_for_booking,
    build_pricing_from_frozen,
)

logger = logging.getLogger(__name__)

try:
    import razorpay
except Exception:
    razorpay = None


# ===========================================================
# LIST
# ===========================================================

class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = "bookings/booking_list.html"

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)


# ===========================================================
# DETAIL
# ===========================================================

class BookingDetailView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = "bookings/booking_detail.html"

    def get_object(self):
        return get_object_or_404(
            Booking,
            booking_id=self.kwargs["booking_id"],
            user=self.request.user,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        booking = self.object

        if booking.final_amount:
            pricing = build_pricing_from_frozen(booking, 0)
        else:
            pricing = None

        ctx["pricing"] = pricing
        return ctx


# ===========================================================
# CONFIRMATION (FREEZE HERE ONLY)
# ===========================================================

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)

    if booking.check_reservation_timeout():
        return HttpResponse("Reservation expired", status=400)

    pricing = freeze_pricing_for_booking(booking)

    return render(
        request,
        "bookings/confirmation.html",
        {
            "booking": booking,
            "pricing": pricing,
        },
    )


# ===========================================================
# PAYMENT (FROZEN ONLY)
# ===========================================================

@login_required
def payment_page(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)

    if booking.check_reservation_timeout():
        return HttpResponse("Reservation expired", status=400)

    # ❌ NEVER freeze here
    if booking.final_amount is None:
        return HttpResponse("Pricing not frozen. Confirm booking first.", status=400)

    pricing = build_pricing_from_frozen(booking, 0)

    gateway_amount = pricing["gateway_payable"]

    razorpay_key = settings.RAZORPAY_KEY_ID
    order_id = f"order_{uuid.uuid4().hex}"

    if razorpay and razorpay_key:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        order = client.order.create({
            "amount": int(gateway_amount * Decimal("100")),  # ✅ NO FLOAT
            "currency": "INR",
            "receipt": str(booking.booking_id),
        })

        order_id = order["id"]

    return render(
        request,
        "payments/payment.html",
        {
            "booking": booking,
            "pricing": pricing,
            "razorpay_key": razorpay_key,
            "order_id": order_id,
        },
    )
