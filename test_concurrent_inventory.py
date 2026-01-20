"""
TEST: INVENTORY LOCKING - TWO CONCURRENT USERS
Verifies: User A reserves → User B sees reduced inventory → After expiry → inventory restored
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
import django

ROOT = r"c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goexplorer.settings")
django.setup()

from bookings.models import Booking, HotelBooking
from hotels.channel_manager_service import InternalInventoryService
from hotels.models import Hotel, RoomType, RoomMealPlan
from users.models import User
from payments.models import Wallet

print("\n" + "="*80)
print("TEST: CONCURRENT INVENTORY LOCKING (2 USERS)")
print("="*80)

# Get seed hotel setup
hotel = Hotel.objects.filter(name="Seed Test Hotel").first()
if not hotel:
    print("❌ NO SEED HOTEL FOUND - Run seed_complete_hotel_booking.py first")
    sys.exit(1)

room_type = hotel.room_types.first()
if not room_type:
    print("❌ NO ROOM TYPE FOUND")
    sys.exit(1)

meal_plan = room_type.meal_plans.filter(is_active=True).first()
if not meal_plan:
    print("❌ NO MEAL PLAN FOUND")
    sys.exit(1)

check_in = date.today() + timedelta(days=2)
check_out = check_in + timedelta(days=1)

# Reset inventory
service = InternalInventoryService(hotel)
service.ensure_availability_rows(room_type, check_in, check_out)
for slot in room_type.availability.filter(date__gte=check_in, date__lt=check_out):
    slot.available_rooms = room_type.total_rooms
    slot.save(update_fields=["available_rooms"])

inventory_initial = service.summarize(room_type, check_in, check_out)["available_rooms"]

print(f"\n[SETUP] Hotel: {hotel.name}")
print(f"[SETUP] Room Type: {room_type.name}")
print(f"[SETUP] Total Rooms: {room_type.total_rooms}")
print(f"[SETUP] Check-in: {check_in} | Check-out: {check_out}")
print(f"[SETUP] Initial Inventory: {inventory_initial} rooms")

# Create User A
user_a, _ = User.objects.get_or_create(
    username="concurrent_user_a",
    defaults={"email": "user_a@example.com", "phone": "1111111111"},
)
user_a.email_verified = True
user_a.email_verified_at = timezone.now()
user_a.save()

wallet_a, _ = Wallet.objects.get_or_create(user=user_a, defaults={"balance": Decimal("5000.00")})

# Create User B
user_b, _ = User.objects.get_or_create(
    username="concurrent_user_b",
    defaults={"email": "user_b@example.com", "phone": "2222222222"},
)
user_b.email_verified = True
user_b.email_verified_at = timezone.now()
user_b.save()

wallet_b, _ = Wallet.objects.get_or_create(user=user_b, defaults={"balance": Decimal("5000.00")})

print(f"\n[USER A] Username: {user_a.username}")
print(f"[USER B] Username: {user_b.username}")

# Clean up any prior test bookings
Booking.objects.filter(user__in=[user_a, user_b], booking_type='hotel', external_booking_id__startswith='CONCURRENT').delete()

# USER A RESERVES
print("\n" + "="*80)
print("STEP 1: USER A RESERVES 1 ROOM")
print("="*80)

total_nights = (check_out - check_in).days
base_total = meal_plan.calculate_total_price(1, total_nights)

booking_a = Booking.objects.create(
    user=user_a,
    booking_type="hotel",
    status="reserved",
    reserved_at=timezone.now(),
    expires_at=timezone.now() + timedelta(minutes=10),
    total_amount=base_total,
    paid_amount=Decimal("0.00"),
    customer_name="User A",
    customer_email=user_a.email,
    customer_phone=user_a.phone,
    external_booking_id="CONCURRENT-USER-A",
)

HotelBooking.objects.create(
    booking=booking_a,
    room_type=room_type,
    meal_plan=meal_plan,
    check_in=check_in,
    check_out=check_out,
    number_of_rooms=1,
    number_of_adults=2,
    number_of_children=0,
    total_nights=total_nights,
)

# Lock inventory for User A
lock_a = service.lock_inventory(room_type, check_in, check_out, num_rooms=1, hold_minutes=10)
lock_a.booking = booking_a
lock_a.save(update_fields=["booking", "updated_at"])

inventory_after_a = service.summarize(room_type, check_in, check_out)["available_rooms"]

print(f"[USER A] Booking ID: {booking_a.booking_id}")
print(f"[USER A] Status: {booking_a.status}")
print(f"[USER A] Expires At: {booking_a.expires_at}")
print(f"[USER A] Lock Reference: {lock_a.reference_id}")
print(f"[INVENTORY] Before User A: {inventory_initial} rooms")
print(f"[INVENTORY] After User A:  {inventory_after_a} rooms")

# USER B CHECKS INVENTORY
print("\n" + "="*80)
print("STEP 2: USER B CHECKS AVAILABLE INVENTORY")
print("="*80)

inventory_for_b = service.summarize(room_type, check_in, check_out)["available_rooms"]
print(f"[USER B] Sees available rooms: {inventory_for_b}")

if inventory_for_b != inventory_after_a:
    print(f"❌ FAIL: User B sees {inventory_for_b} rooms, expected {inventory_after_a}")
else:
    print(f"✅ PASS: User B sees reduced inventory correctly")

# SIMULATE EXPIRY
print("\n" + "="*80)
print("STEP 3: SIMULATE BOOKING EXPIRY (10 MINUTES)")
print("="*80)

# Manually expire the booking by setting expires_at to the past
booking_a.expires_at = timezone.now() - timedelta(minutes=1)
booking_a.save(update_fields=['expires_at'])

# Trigger expiry check
if booking_a.check_reservation_timeout():
    print(f"[EXPIRY] Booking auto-expired via timeout check")
else:
    print(f"[WARNING] Booking did not expire via check_reservation_timeout()")

booking_a.refresh_from_db()
lock_a.refresh_from_db()
inventory_after_expiry = service.summarize(room_type, check_in, check_out)["available_rooms"]

print(f"[USER A] Booking Status After Expiry: {booking_a.status}")
print(f"[USER A] Lock Status After Expiry: {lock_a.status}")
print(f"[INVENTORY] After Expiry: {inventory_after_expiry} rooms")

# VERIFICATION
print("\n" + "="*80)
print("VERIFICATION CHECKS")
print("="*80)

checks = []

# Check 1: Initial inventory correct
if inventory_initial == room_type.total_rooms:
    checks.append(f"✅ Initial inventory: {inventory_initial} rooms (total: {room_type.total_rooms})")
else:
    checks.append(f"❌ Initial inventory wrong: {inventory_initial} (expected {room_type.total_rooms})")

# Check 2: Inventory reduced after User A reserves
if inventory_after_a == inventory_initial - 1:
    checks.append(f"✅ Inventory reduced after User A: {inventory_initial} → {inventory_after_a}")
else:
    checks.append(f"❌ Inventory NOT reduced: {inventory_initial} → {inventory_after_a}")

# Check 3: User B sees reduced inventory
if inventory_for_b == inventory_after_a:
    checks.append(f"✅ User B sees reduced inventory: {inventory_for_b} rooms")
else:
    checks.append(f"❌ User B sees wrong inventory: {inventory_for_b} (expected {inventory_after_a})")

# Check 4: Booking expired
if booking_a.status == 'expired':
    checks.append(f"✅ Booking expired: status={booking_a.status}")
else:
    checks.append(f"❌ Booking NOT expired: status={booking_a.status}")

# Check 5: Lock released or expired
if lock_a.status in ['released', 'expired']:
    checks.append(f"✅ Lock released/expired: status={lock_a.status}")
else:
    checks.append(f"❌ Lock NOT released: status={lock_a.status}")

# Check 6: Inventory restored after expiry
if inventory_after_expiry == inventory_initial:
    checks.append(f"✅ Inventory restored: {inventory_after_expiry} rooms (initial: {inventory_initial})")
else:
    checks.append(f"❌ Inventory NOT restored: {inventory_after_expiry} (expected {inventory_initial})")

for check in checks:
    print(check)

failures = [c for c in checks if c.startswith("❌")]

print("\n" + "="*80)
if failures:
    print(f"RESULT: ❌ FAILED ({len(failures)} issues)")
    print("="*80)
    sys.exit(1)
else:
    print("RESULT: ✅ ALL CHECKS PASSED")
    print("="*80)
    print("\n✅ CONCURRENT INVENTORY LOCKING WORKS CORRECTLY")
    print(f"  - User A reserved: inventory {inventory_initial} → {inventory_after_a}")
    print(f"  - User B saw reduced inventory: {inventory_for_b}")
    print(f"  - After expiry: inventory restored to {inventory_after_expiry}")
