Timestamp: 2026-02-11 00:17:50

CHANGE 1
Reason: Remove print() logging in favor of structured logging.
Path: bookings/services/core_pricing.py
---------------------------------------

```python
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

SERVICE_FEE_RATE = Decimal("0.05")
SERVICE_FEE_CAP = Decimal("500")
GST_THRESHOLD = Decimal("7500")
GST_LOW = Decimal("0.05")
GST_HIGH = Decimal("0.18")


class CorePricing:

    @staticmethod
    def calculate(room_price, nights, meal_delta=0, wallet_amount=0):

        room_price = Decimal(room_price or 0)
        meal_delta = Decimal(meal_delta or 0)
        nights = max(int(nights), 0)

        # -------- Base (room + meals) --------
        base = (room_price + meal_delta) * nights

        # -------- Service Fee (ONLY on room base, capped) --------
        room_base = room_price * nights
        service_fee = min(room_base * SERVICE_FEE_RATE, SERVICE_FEE_CAP)

        # -------- GST (ONLY on room base, slab on base) --------
        gst_rate = GST_LOW if room_base < GST_THRESHOLD else GST_HIGH
        gst = room_base * gst_rate

        # -------- Totals --------
        taxes = service_fee + gst
        total = base + taxes

        wallet = min(Decimal(wallet_amount or 0), total)
        payable = total - wallet

        logger.info(
            "[CORE_PRICING] base=%s fee=%s gst=%s total=%s",
            base,
            service_fee,
            gst,
            total,
        )

        return {
            "base_amount": base,
            "service_fee": service_fee,
            "gst_amount": gst,
            "taxes_total": taxes,
            "total_before_wallet": total,
            "wallet_applied": wallet,
            "gateway_payable": payable,
        }
```

CHANGE 2
Reason: Prevent crash when booking.user is NULL.
Path: bookings/models.py
------------------------

```python
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TimeStampedModel
from hotels.models import Hotel, RoomType, RoomCancellationPolicy
from buses.models import BusSchedule, SeatLayout, BusRoute
from packages.models import PackageDeparture
import uuid
import json
from datetime import timedelta, datetime, time


class Booking(TimeStampedModel):
    """Base booking model"""
    BOOKING_STATUS = [
        ('reserved', 'Reserved'),           # Booking created, awaiting payment (30 min timeout)
        ('payment_pending', 'Payment Pending'),  # Legacy - being phased out
        ('confirmed', 'Confirmed'),         # Payment succeeded, inventory locked
        ('payment_failed', 'Payment Failed'),    # Payment attempt failed
        ('expired', 'Expired'),              # 30 min timeout without payment
        ('cancelled', 'Cancelled'),          # User cancelled
        ('completed', 'Completed'),          # Journey/stay complete
        ('refunded', 'Refunded'),            # Refund issued
        ('deleted', 'Deleted'),              # Admin deleted
    ]
    
    BOOKING_TYPES = [
        ('hotel', 'Hotel'),
        ('bus', 'Bus'),
        ('package', 'Package'),
    ]

    INVENTORY_CHANNELS = [
        ('internal_cm', 'Internal CM'),
        ('external_cm', 'External CM'),
    ]
    
    booking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)
    
    # Channel / External integration fields
    external_booking_id = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    channel_name = models.CharField(max_length=100, null=True, blank=True)
    channel_reference = models.CharField(max_length=200, null=True, blank=True)
    sync_status = models.CharField(max_length=50, default='pending', choices=[('pending','Pending'), ('synced','Synced'), ('failed','Failed')])
    last_synced_at = models.DateTimeField(null=True, blank=True)
    booking_source = models.CharField(max_length=20, choices=[('internal','Internal'), ('external','External')], default='internal')
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPES)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='reserved')
    
    # State transition timestamps
    reserved_at = models.DateTimeField(null=True, blank=True)  # When booking was created
    confirmed_at = models.DateTimeField(null=True, blank=True)  # When payment succeeded
    expires_at = models.DateTimeField(null=True, blank=True)  # When reservation expires (30 min after reserved_at)
    completed_at = models.DateTimeField(null=True, blank=True)  # When journey/stay completed

    inventory_channel = models.CharField(max_length=20, choices=INVENTORY_CHANNELS, default='internal_cm')
    lock_id = models.CharField(max_length=128, blank=True)
    cm_booking_id = models.CharField(max_length=128, blank=True)
    payment_reference = models.CharField(max_length=128, blank=True)
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    service_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    taxes_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Promo code (optional)
    promo_code = models.ForeignKey(
        'core.PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings_with_promo'
    )
    
    # Wallet traceability (for admin visibility)
    wallet_balance_before = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Wallet balance before payment")
    wallet_balance_after = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Wallet balance after payment")
    
    # Contact details
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=15)
    
    # NOTE: PII should be encrypted in the DB in production. For now we provide mask helpers.
    def masked_phone(self):
        if not self.customer_phone:
            return ''
        s = str(self.customer_phone)
        if len(s) <= 4:
            return '****'
        return s[:2] + '*' * (len(s) - 4) + s[-2:]

    def masked_email(self):
        if not self.customer_email:
            return ''
        parts = self.customer_email.split('@')
        if len(parts[0]) <= 2:
            local = '*' * len(parts[0])
        else:
            local = parts[0][0] + '*' * (len(parts[0]) - 2) + parts[0][-1]
        return f"{local}@{parts[1]}"

    @property
    def hotel_booking(self):
        """Backward-compatible alias for hotel booking relation."""
        return getattr(self, 'hotel_details', None)
    
    special_requests = models.TextField(blank=True)
    
    # Cancellation
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Soft delete tracking
    is_deleted = models.BooleanField(default=False)
    deleted_reason = models.TextField(blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_bookings')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        username = self.user.username if self.user else "guest"
        return f"{self.booking_id} - {username} - {self.booking_type}"
    
    def soft_delete(self, user=None, reason=''):
        """Soft delete booking"""
        self.is_deleted = True
        self.status = 'deleted'
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.deleted_reason = reason
        self.save()

    def restore(self, user=None):
        """Restore soft-deleted booking"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.deleted_reason = ''
        # Revert status from 'deleted' to 'confirmed' or 'reserved' based on payment
        if self.paid_amount > 0:
            self.status = 'confirmed'
        else:
            self.status = 'reserved'
        self.save()

    def is_eligible_for_review(self):
        """Check if user can write review for this booking (must be COMPLETED with payment)."""
        return self.status == 'completed' and self.paid_amount > 0

    def mark_completed(self):
        """Mark booking as completed (allows reviews)."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])

    def check_reservation_timeout(self):
        """Check if 10-minute reservation timeout has expired. Marks booking expired and releases locks."""
        if self.status not in ['reserved', 'payment_pending']:
            return False
        deadline = self.reservation_deadline
        if not deadline:
            return False
        if timezone.now() >= deadline:
            self.status = 'expired'
            self.expires_at = deadline
            self.save(update_fields=['status', 'expires_at'])
            self.release_inventory_lock()
            # Restore nightly inventory for expired reservations
            hotel_booking = getattr(self, 'hotel_details', None)
            if hotel_booking:
                try:
                    from bookings.inventory_utils import restore_inventory
                    restore_inventory(
                        room_type=hotel_booking.room_type,
                        check_in=hotel_booking.check_in,
                        check_out=hotel_booking.check_out,
                        num_rooms=hotel_booking.number_of_rooms or 1,
                    )
                except Exception:
                    pass
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info("[BOOKING_EXPIRED] booking=%s status=expired deadline=%s", self.booking_id, deadline)
                payload = {'booking_id': str(self.booking_id), 'event': 'booking_expired'}
                logger.info("[NOTIFICATION_EMAIL] payload=%s", payload)
                logger.info("[NOTIFICATION_SMS] payload=%s", payload)
                logger.info("[NOTIFICATION_WHATSAPP] payload=%s", payload)
            except Exception:
                pass
            return True
        return False

    @property
    def reservation_deadline(self):
        """Return when the reservation expires."""
        if self.expires_at:
            return self.expires_at
        if self.reserved_at:
            return self.reserved_at + timedelta(minutes=10)
        return None

    @property
    def reservation_seconds_left(self):
        """Seconds remaining before the reservation expires (0 if expired)."""
        if self.status != 'reserved':
            return None
        deadline = self.reservation_deadline
        if not deadline:
            return None
        remaining = int((deadline - timezone.now()).total_seconds())
        return remaining if remaining > 0 else 0

    def release_inventory_lock(self):
        """Release any held inventory lock when a reservation expires."""
        lock = getattr(self, 'inventory_lock', None)
        if not lock:
            return

        try:
            if lock.source == 'internal_cm':
                from hotels.channel_manager_service import InternalInventoryService
                InternalInventoryService(lock.hotel).release_lock(lock)
            elif lock.source == 'external_cm':
                from hotels.channel_manager_service import ExternalChannelManagerClient, InventoryLockError
                try:
                    ExternalChannelManagerClient(provider=lock.provider).release_lock(lock.lock_id or lock.reference_id)
                except InventoryLockError:
                    # Ignore failures; status will still be marked expired
                    pass
            lock.status = 'expired'
            lock.save(update_fields=['status', 'updated_at'])
        except Exception:
            # Defensive: never break booking save flows if lock release fails
            pass


class HotelBooking(TimeStampedModel):
    """Hotel booking details"""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='hotel_details')
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT)
    meal_plan = models.ForeignKey('hotels.RoomMealPlan', on_delete=models.PROTECT, related_name='bookings', null=True, blank=True)
    cancellation_policy = models.ForeignKey(
        RoomCancellationPolicy,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings'
    )
    
    # SNAPSHOT FIELDS (RULE D): Freeze room/pricing data at booking time (prevents legal issues if admin edits room)
    room_snapshot = models.JSONField(null=True, blank=True, help_text="Frozen room specifications at booking time")
    price_snapshot = models.JSONField(null=True, blank=True, help_text="Frozen pricing breakdown at booking time")

    POLICY_TYPES = [
        ('FREE', 'Free Cancellation'),
        ('PARTIAL', 'Partial Refund'),
        ('NON_REFUNDABLE', 'Non-Refundable'),
    ]
    policy_type = models.CharField(max_length=20, choices=POLICY_TYPES, default='NON_REFUNDABLE')
    policy_free_cancel_until = models.DateTimeField(null=True, blank=True)
    policy_refund_percentage = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    policy_text = models.TextField(blank=True)
    policy_locked_at = models.DateTimeField(null=True, blank=True)
    
    check_in = models.DateField()
    check_out = models.DateField()
    
    number_of_rooms = models.IntegerField(default=1)
    number_of_adults = models.IntegerField(default=1)
    number_of_children = models.IntegerField(default=0)
    
    total_nights = models.IntegerField()
    
    def lock_cancellation_policy(self, policy: RoomCancellationPolicy):
        """Freeze cancellation policy snapshot on the booking if not already locked."""
        if self.policy_locked_at or not policy:
            return

        self.cancellation_policy = policy
        self.policy_type = policy.policy_type
        self.policy_free_cancel_until = policy.free_cancel_until
        self.policy_refund_percentage = policy.refund_percentage
        self.policy_text = policy.policy_text or ''
        self.policy_locked_at = timezone.now()
        self.save(
            update_fields=[
                'cancellation_policy',
                'policy_type',
                'policy_free_cancel_until',
                'policy_refund_percentage',
                'policy_text',
                'policy_locked_at',
                'updated_at',
            ]
        )
    
    def get_cancellation_deadline(self):
        """Calculate cancellation deadline as 2 PM on check-in date."""
        from datetime import time
        return datetime.combine(
            self.check_in,
            time(14, 0),  # 2 PM
            tzinfo=timezone.get_current_timezone()
        )
    
    def __str__(self):
        return f"Hotel Booking - {self.booking.booking_id}"


class BusBooking(TimeStampedModel):
    """Bus booking details"""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='bus_details')
    bus_schedule = models.ForeignKey(BusSchedule, on_delete=models.PROTECT)
    bus_route = models.ForeignKey(BusRoute, on_delete=models.PROTECT, null=True, blank=True)
    
    journey_date = models.DateField()
    boarding_point = models.CharField(max_length=200, blank=True)
    dropping_point = models.CharField(max_length=200, blank=True)
    
    # Snapshot fields (data contract compliance - immutable booking data)
    operator_name = models.CharField(max_length=200, blank=True, help_text="Operator name at booking time")
    bus_name = models.CharField(max_length=100, blank=True, help_text="Bus number/name at booking time")
    route_name = models.CharField(max_length=200, blank=True, help_text="Route description at booking time")
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Contact phone at booking time")
    departure_time_snapshot = models.CharField(max_length=20, blank=True, help_text="Departure time at booking time")
    
    def __str__(self):
        return f"Bus Booking - {self.booking.booking_id}"
    
    @property
    def bus_number(self):
        """Get bus number from schedule (live data, not snapshot)"""
        return self.bus_schedule.route.bus.bus_number if self.bus_schedule else self.bus_name
    
    @property
    def total_seats_booked(self):
        """Get total seats booked"""
        return self.seats.count()


class BusBookingSeat(models.Model):
    """Seats booked for bus"""
    bus_booking = models.ForeignKey(BusBooking, on_delete=models.CASCADE, related_name='seats')
    seat = models.ForeignKey(SeatLayout, on_delete=models.PROTECT)
    
    passenger_name = models.CharField(max_length=200)
    passenger_age = models.IntegerField()
    passenger_gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female')])
    
    class Meta:
        unique_together = ['bus_booking', 'seat']
    
    def __str__(self):
        return f"{self.bus_booking.booking.booking_id} - Seat {self.seat.seat_number}"


class PackageBooking(TimeStampedModel):
    """Package booking details"""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='package_details')
    package_departure = models.ForeignKey(PackageDeparture, on_delete=models.PROTECT)
    
    number_of_travelers = models.IntegerField(default=1)
    
    def __str__(self):
        return f"Package Booking - {self.booking.booking_id}"


class PackageBookingTraveler(models.Model):
    """Travelers for package booking"""
    package_booking = models.ForeignKey(PackageBooking, on_delete=models.CASCADE, related_name='travelers')
    
    name = models.CharField(max_length=200)
    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')])
    passport_number = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return f"{self.package_booking.booking.booking_id} - {self.name}"


class Review(TimeStampedModel):
    """Review for bookings"""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    
    is_approved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Review for {self.booking.booking_id} - {self.rating} stars"


class BookingAuditLog(TimeStampedModel):
    """Audit log for booking changes"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='audit_logs')
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    
    action = models.CharField(max_length=50, default='updated', help_text='updated, deleted, restored, etc.')
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Log for {self.booking.booking_id} - {self.field_name} by {self.edited_by}"


class InventoryLock(TimeStampedModel):
    """Track inventory locks for both external and internal channel managers."""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('confirmed', 'Confirmed'),
        ('released', 'Released'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ]

    SOURCE_CHOICES = [
        ('external_cm', 'External Channel Manager'),
        ('internal_cm', 'Internal Channel Manager'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_lock')
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='inventory_locks')
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='inventory_locks')

    reference_id = models.CharField(max_length=80, unique=True)
    lock_id = models.CharField(max_length=128, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    provider = models.CharField(max_length=100, blank=True)

    check_in = models.DateField()
    check_out = models.DateField()
    num_rooms = models.IntegerField(default=1)

    expires_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Lock {self.reference_id} ({self.get_status_display()})"
```

CHANGE 3
Reason: Enforce reservation timeout checks in confirmation and payment flows.
Path: bookings/views.py
-----------------------

```python
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
```
