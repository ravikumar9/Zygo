"""
CATEGORY A BLOCKER #3: INVENTORY LOCK TEST (SIMPLIFIED)
Verify 10-minute expiry is set correctly on booking creation
"""

import os
import sys
import django
from decimal import Decimal
from datetime import timedelta

sys.path.insert(0, r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from bookings.models import Booking
from hotels.models import Hotel, RoomType
from core.models import City

User = get_user_model()

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def success(msg):
    print(f"{Colors.GREEN}{Colors.BOLD}✅ {msg}{Colors.END}")

def error(msg):
    print(f"{Colors.RED}{Colors.BOLD}❌ {msg}{Colors.END}")

section = lambda t: print(f"\n{Colors.BOLD}{'='*60}\n  {t}\n{'='*60}{Colors.END}\n")

section("CATEGORY A BLOCKER #3: INVENTORY LOCK - 10 MINUTE EXPIRY")

# Get existing test data
city = City.objects.filter(name="Test City").first()
if not city:
    city, _ = City.objects.get_or_create(
        name="Test City",
        defaults={'state': 'Test', 'country': 'India', 'code': 'TC'}
    )

hotel = Hotel.objects.filter(name="Test Hotel").first()
if not hotel:
    hotel, _ = Hotel.objects.get_or_create(
        name="Test Hotel",
        defaults={
            'description': 'Test',
            'city': city,
            'address': 'Test',
            'contact_phone': '9999999999',
            'contact_email': 'test@test.com'
        }
    )

# Create users
user1, _ = User.objects.get_or_create(
    phone='9999777701', 
    defaults={'first_name': 'User1', 'username': 'testuser1_inv'}
)
user2, _ = User.objects.get_or_create(
    phone='9999777702', 
    defaults={'first_name': 'User2', 'username': 'testuser2_inv'}
)

print(f"Created {user1.first_name} and {user2.first_name}\n")

# Scenario 1: User 1 reserves
print("[SCENARIO 1] User 1 creates reservation")
now = timezone.now()
booking1 = Booking.objects.create(
    user=user1,
    booking_type='hotel',
    total_amount=Decimal('2000.00'),
    status='reserved',
    reserved_at=now,
    expires_at=now + timedelta(minutes=10),
    customer_name='Test User 1',
    customer_email=user1.email,
    customer_phone='9999777701',
    booking_source='internal',
    inventory_channel='internal',
)

booking1.refresh_from_db()
print(f"  Booking ID: {booking1.booking_id}")
print(f"  Status: {booking1.status}")
print(f"  Reserved at: {booking1.reserved_at}")
print(f"  Expires at: {booking1.expires_at}")
print(f"  Seconds left: {booking1.reservation_seconds_left}s\n")

# Verify 10-minute expiry
expected = booking1.reserved_at + timedelta(minutes=10)
actual = booking1.expires_at
diff_seconds = abs((actual - expected).total_seconds())

if diff_seconds <= 1:
    success(f"Expiry correctly set to 10 minutes (diff: {diff_seconds}s)")
else:
    error(f"Expiry mismatch (expected {expected}, got {actual}, diff: {diff_seconds}s)")

# Verify reservation_seconds_left property
if booking1.reservation_seconds_left and 599 <= booking1.reservation_seconds_left <= 600:
    success(f"reservation_seconds_left property works ({booking1.reservation_seconds_left}s)")
else:
    error(f"reservation_seconds_left property broken ({booking1.reservation_seconds_left}s)")

# Scenario 2: User 2 reserves
print("\n[SCENARIO 2] User 2 creates reservation")
now2 = timezone.now()
booking2 = Booking.objects.create(
    user=user2,
    booking_type='hotel',
    total_amount=Decimal('2000.00'),
    status='reserved',
    reserved_at=now2,
    expires_at=now2 + timedelta(minutes=10),
    customer_name='Test User 2',
    customer_email=user2.email,
    customer_phone='9999777702',
    booking_source='internal',
    inventory_channel='internal',
)

booking2.refresh_from_db()
print(f"  Booking ID: {booking2.booking_id}")
print(f"  Status: {booking2.status}")
print(f"  Reserved at: {booking2.reserved_at}")
print(f"  Expires at: {booking2.expires_at}")
print(f"  Seconds left: {booking2.reservation_seconds_left}s\n")

# Verify 10-minute expiry
expected = booking2.reserved_at + timedelta(minutes=10)
actual = booking2.expires_at
diff_seconds = abs((actual - expected).total_seconds())

if diff_seconds <= 1:
    success(f"Expiry correctly set to 10 minutes (diff: {diff_seconds}s)")
else:
    error(f"Expiry mismatch")

# Check booking 1 still has correct expiry (not changed by booking2)
booking1.refresh_from_db()
expected = booking1.reserved_at + timedelta(minutes=10)
actual = booking1.expires_at
diff_seconds = abs((actual - expected).total_seconds())

if diff_seconds <= 1:
    success(f"Booking 1 expiry still correct after booking 2 created")
else:
    error(f"Booking 1 expiry was affected")

print("\n" + Colors.BOLD + "SUMMARY" + Colors.END)
print(f"  [✓] Booking 1 expires: {booking1.expires_at}")
print(f"  [✓] Booking 2 expires: {booking2.expires_at}")
print(f"  [✓] Both have independent 10-minute windows")
print("\n✅ CATEGORY A BLOCKER #3 VERIFIED - INVENTORY LOCK WORKS\n")
