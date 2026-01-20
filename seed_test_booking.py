"""
SEED: Create a reserved booking for testing
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
from bookings.models import Booking, HotelBooking
from hotels.models import Hotel, RoomType, RoomMealPlan
from payments.models import Wallet

User = get_user_model()

# Get or create test user
user, created = User.objects.get_or_create(
    phone='9999888801',
    defaults={'username': 'walletuser1', 'first_name': 'WalletUser1', 'email': 'wallet@test.com', 'email_verified_at': timezone.now()}
)
if created:
    print(f"Created user: {user.phone}")

# Ensure wallet
wallet, _ = Wallet.objects.get_or_create(user=user, defaults={'balance': Decimal('5000.00')})
wallet.balance = Decimal('5000.00')
wallet.save()
print(f"Wallet balance: ₹{wallet.balance}")

# Get existing hotel and room
hotel = Hotel.objects.first()
room_type = RoomType.objects.filter(hotel=hotel).first()
meal_plan = RoomMealPlan.objects.filter(room_type=room_type, is_active=True).first()

if not hotel or not room_type or not meal_plan:
    print("ERROR: Need hotel, room_type, and meal_plan in database")
    sys.exit(1)

# Create booking
booking = Booking.objects.create(
    user=user,
    booking_type='hotel',
    total_amount=Decimal('2000.00'),  # Base amount (GST will be added on payment)
    status='reserved',
    reserved_at=timezone.now(),
    customer_name=user.first_name,
    customer_email=user.email,
    customer_phone=user.phone,
    booking_source='internal',
    inventory_channel='internal_cm',
)

HotelBooking.objects.create(
    booking=booking,
    room_type=room_type,
    meal_plan=meal_plan,
    check_in=timezone.now().date() + timedelta(days=7),
    check_out=timezone.now().date() + timedelta(days=9),
    number_of_rooms=1,
    number_of_adults=2,
    total_nights=2,
)

print(f"\n✅ Created booking: {booking.booking_id}")
print(f"   Status: {booking.status}")
print(f"   Total (base): ₹{booking.total_amount}")
print(f"   Expires: {booking.expires_at}")
print(f"   User: {user.phone}")
print(f"   Wallet: ₹{wallet.balance}")
