"""
Seed script to create a fully-linked hotel booking with wallet + inventory.
Outputs: Booking ID, Hotel ID, RoomType ID, inventory before/after reserve.
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal

import django
from django.utils import timezone

# Django setup
ROOT = r"c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goexplorer.settings")
django.setup()

from bookings.models import Booking, HotelBooking  # noqa: E402
from core.models import City  # noqa: E402
from hotels.channel_manager_service import InternalInventoryService  # noqa: E402
from hotels.models import Hotel, RoomMealPlan, RoomType  # noqa: E402
from payments.models import Wallet  # noqa: E402
from users.models import User  # noqa: E402


SEED_CODE = "SEED-COMPLETE-HOTEL"
TARGET_WALLET_BALANCE = Decimal("5000.00")


def ensure_user():
    user, created = User.objects.get_or_create(
        username="seed_user",
        defaults={
            "email": "seed_user@example.com",
            "phone": "9999999999",
        },
    )
    if created:
        user.set_password("password123")
    user.email_verified = True
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified", "email_verified_at", "password"])
    return user


def ensure_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={"balance": Decimal("0.00")})
    delta = TARGET_WALLET_BALANCE - wallet.balance
    if delta > Decimal("0.00"):
        wallet.add_balance(delta, description="Seed top-up for complete hotel booking")
    elif delta < Decimal("0.00"):
        wallet.balance = TARGET_WALLET_BALANCE
        wallet.save(update_fields=["balance", "updated_at"])
    return wallet


def ensure_city():
    city, _ = City.objects.get_or_create(
        code="TESTCITY",
        defaults={"name": "Test City", "state": "TS", "country": "India"},
    )
    return city


def ensure_hotel(city):
    hotel, _ = Hotel.objects.get_or_create(
        name="Seed Test Hotel",
        city=city,
        defaults={
            "description": "Seed hotel for end-to-end testing",
            "address": "123 Seed Street",
            "contact_phone": "1800123123",
            "contact_email": "seed_hotel@example.com",
        },
    )
    return hotel


def ensure_room_type(hotel):
    room_type, _ = RoomType.objects.get_or_create(
        hotel=hotel,
        name="Seed Deluxe",
        defaults={
            "room_type": "deluxe",
            "description": "Seed deluxe room",
            "max_occupancy": 2,
            "number_of_beds": 1,
            "room_size": 200,
            "base_price": Decimal("2000.00"),
            "total_rooms": 5,
            "is_available": True,
        },
    )
    return room_type


def ensure_meal_plan(room_type):
    meal_plan, _ = RoomMealPlan.objects.get_or_create(
        room_type=room_type,
        plan_type="room_only",
        defaults={
            "name": "Room Only",
            "description": "No meals included",
            "price_per_night": Decimal("2000.00"),
            "is_active": True,
            "display_order": 1,
        },
    )
    return meal_plan


def reset_inventory(room_type, check_in, check_out):
    service = InternalInventoryService(room_type.hotel)
    service.ensure_availability_rows(room_type, check_in, check_out)
    for slot in room_type.availability.filter(date__gte=check_in, date__lt=check_out):
        slot.available_rooms = room_type.total_rooms
        slot.save(update_fields=["available_rooms"])
    summary = service.summarize(room_type, check_in, check_out)
    return service, summary["available_rooms"]


def create_booking(user, room_type, meal_plan, check_in, check_out, available_before):
    total_nights = (check_out - check_in).days
    num_rooms = 1
    base_total = meal_plan.calculate_total_price(num_rooms, total_nights)

    # Clean up any prior seed booking
    Booking.objects.filter(external_booking_id=SEED_CODE).delete()

    booking = Booking.objects.create(
        user=user,
        booking_type="hotel",
        status="reserved",
        reserved_at=timezone.now(),
        expires_at=timezone.now() + timedelta(minutes=10),
        total_amount=base_total,
        paid_amount=Decimal("0.00"),
        promo_code=None,
        customer_name="Seed User",
        customer_email=user.email,
        customer_phone=user.phone,
        external_booking_id=SEED_CODE,
    )

    hotel_booking = HotelBooking.objects.create(
        booking=booking,
        room_type=room_type,
        meal_plan=meal_plan,
        check_in=check_in,
        check_out=check_out,
        number_of_rooms=num_rooms,
        number_of_adults=2,
        number_of_children=0,
        total_nights=total_nights,
    )

    service = InternalInventoryService(room_type.hotel)
    lock = service.lock_inventory(room_type, check_in, check_out, num_rooms=num_rooms, hold_minutes=10)
    lock.booking = booking
    lock.save(update_fields=["booking", "updated_at"])

    available_after = service.summarize(room_type, check_in, check_out)["available_rooms"]

    print("\nSEED DATA CREATED")
    print("Booking ID:", booking.booking_id)
    print("Hotel ID:", room_type.hotel.id)
    print("RoomType ID:", room_type.id)
    print(f"Inventory BEFORE reserve: {available_before} rooms")
    print(f"Inventory AFTER reserve:  {available_after} rooms")
    print(f"Check-in: {check_in} | Check-out: {check_out} | Nights: {total_nights}")
    print(f"Base Amount: ₹{base_total}")
    print(f"Wallet Balance: ₹{user.wallet.balance}")
    print(f"Lock Reference: {lock.reference_id} (status={lock.status})")

    return booking


def main():
    user = ensure_user()
    wallet = ensure_wallet(user)
    city = ensure_city()
    hotel = ensure_hotel(city)
    room_type = ensure_room_type(hotel)
    meal_plan = ensure_meal_plan(room_type)

    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=1)

    service, available_before = reset_inventory(room_type, check_in, check_out)
    booking = create_booking(user, room_type, meal_plan, check_in, check_out, available_before)

    print("\nREADY FOR PAYMENT TESTING")
    print("Use finalize_booking_payment() with this booking to confirm and then cancel.")


if __name__ == "__main__":
    main()
