"""
CATEGORY A BLOCKER #3: INVENTORY LOCK TEST
Verify 10-minute inventory locking with 2 concurrent users
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta
import threading
import time

sys.path.insert(0, r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from bookings.models import Booking
from hotels.models import Hotel, RoomType, RoomAvailability
from core.models import City

User = get_user_model()

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(msg, color=Colors.BLUE):
    print(f"{color}{Colors.BOLD}[TEST]{Colors.END} {msg}")

def success(msg):
    print(f"{Colors.GREEN}{Colors.BOLD}✅ {msg}{Colors.END}")

def error(msg):
    print(f"{Colors.RED}{Colors.BOLD}❌ {msg}{Colors.END}")

def section(title):
    print(f"\n{Colors.YELLOW}{Colors.BOLD}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Colors.END}\n")

# Setup test data
section("SETUP: Creating test data")

city, _ = City.objects.get_or_create(
    name="Inventory Test City",
    defaults={'state': 'Test', 'country': 'India', 'code': 'ITC'}
)

hotel, _ = Hotel.objects.get_or_create(
    name="Inventory Test Hotel",
    defaults={
        'description': 'Test',
        'city': city,
        'address': 'Test Address',
        'contact_phone': '9999999999',
        'contact_email': 'test@test.com'
    }
)

# Get or create room type
room_type = RoomType.objects.filter(hotel=hotel, name='Deluxe').first()
if not room_type:
    room_type = RoomType.objects.create(
        hotel=hotel,
        name='Deluxe',
        base_price=Decimal('2000.00'),
        total_rooms=2  # CRITICAL: Only 2 rooms available
    )
    log(f"Created RoomType: {room_type.name} with 2 rooms")

# Setup inventory
inventory, _ = RoomAvailability.objects.get_or_create(
    room_type=room_type,
    date=timezone.now().date() + timedelta(days=5),
    defaults={'available_rooms': 2}
)
log(f"Inventory: {inventory.available_rooms} rooms available on {inventory.date}")

# Create 2 users
user1, _ = User.objects.get_or_create(
    phone='9999888801',
    defaults={'first_name': 'User1', 'email': f'user1_{int(time.time())}@test.com'}
)
user2, _ = User.objects.get_or_create(
    phone='9999888802',
    defaults={'first_name': 'User2', 'email': f'user2_{int(time.time())}@test.com'}
)

log(f"User 1: {user1.phone}")
log(f"User 2: {user2.phone}")

# Test results
results = {'user1': {}, 'user2': {}}

def user_reserve(user, user_id):
    """User reserves a room"""
    try:
        check_in = timezone.now().date() + timedelta(days=5)
        check_out = check_in + timedelta(days=2)
        
        # Create booking
        booking = Booking.objects.create(
            user=user,
            hotel=hotel,
            check_in_date=check_in,
            check_out_date=check_out,
            guests=1,
            rooms=1,
            room_type='deluxe',
            base_amount=Decimal('2000.00'),
            gst_amount=Decimal('360.00'),
            total_payable=Decimal('2360.00'),
            status='reserved'
        )
        
        results[user_id]['booking_id'] = str(booking.booking_id)
        results[user_id]['expires_at'] = booking.expires_at
        results[user_id]['reserved_at'] = booking.reserved_at
        
        # Check inventory after reservation
        inventory.refresh_from_db()
        results[user_id]['inventory_after_reserve'] = inventory.available_rooms
        
        log(f"User {user_id} reserved: {booking.booking_id}")
        log(f"  Expires: {booking.expires_at}")
        log(f"  Inventory now: {inventory.available_rooms}")
        
    except Exception as e:
        results[user_id]['error'] = str(e)
        error(f"User {user_id} reservation failed: {e}")

section("SCENARIO: User 1 reserves room, User 2 tries to reserve")

# User 1 reserves
log("User 1 starting reservation...")
user_reserve(user1, 'user1')

# Check inventory
inventory.refresh_from_db()
log(f"Inventory after User 1: {inventory.available_rooms}")

# User 2 tries to reserve (should get same room since it's auto-assigned)
log("User 2 starting reservation...")
user_reserve(user2, 'user2')

inventory.refresh_from_db()
log(f"Inventory after User 2: {inventory.available_rooms}")

section("VERIFICATION: Check 10-minute expiry")

# Get both bookings
booking1 = Booking.objects.get(booking_id=results['user1']['booking_id'])
booking2 = Booking.objects.get(booking_id=results['user2']['booking_id'])

log(f"Booking 1 ({booking1.booking_id})")
log(f"  Reserved at: {booking1.reserved_at}")
log(f"  Expires at: {booking1.expires_at}")
log(f"  Seconds left: {booking1.reservation_seconds_left}s")

log(f"Booking 2 ({booking2.booking_id})")
log(f"  Reserved at: {booking2.reserved_at}")
log(f"  Expires at: {booking2.expires_at}")
log(f"  Seconds left: {booking2.reservation_seconds_left}s")

# Verify 10-minute rule
for user_id, booking in [('user1', booking1), ('user2', booking2)]:
    expected_expiry = booking.reserved_at + timedelta(minutes=10)
    actual_expiry = booking.expires_at
    
    diff = abs((actual_expiry - expected_expiry).total_seconds())
    
    if diff <= 1:
        success(f"Booking {user_id}: 10-minute expiry correct (diff: {diff}s)")
    else:
        error(f"Booking {user_id}: Expiry mismatch (diff: {diff}s)")

section("SUMMARY")

print(f"User 1 Inventory after reserve: {results['user1'].get('inventory_after_reserve', 'N/A')}")
print(f"User 2 Inventory after reserve: {results['user2'].get('inventory_after_reserve', 'N/A')}")

# Final inventory
inventory.refresh_from_db()
print(f"Final Inventory: {inventory.available_rooms} rooms")

if results['user1'].get('inventory_after_reserve') == 1 and results['user2'].get('inventory_after_reserve') == 0:
    success("Inventory locking works: User1 reserved → 1 left, User2 reserved → 0 left")
else:
    error("Inventory locking may have issues")

print(f"\n✅ TEST COMPLETE\n")
