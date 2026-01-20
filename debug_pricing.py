"""
DEBUG: Check why pricing calculator returns different amount
"""

import os
import sys
import django
from decimal import Decimal

sys.path.insert(0, r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from bookings.models import Booking
from bookings.pricing_calculator import calculate_pricing

# Get the booking
booking = Booking.objects.filter(booking_id='b9f25ee4-fc75-4a46-a3e4-e9143f1b7d6f').first()

print(f"\nBooking: {booking.booking_id}")
print(f"Stored total_amount: ₹{booking.total_amount}")
print(f"Booking type: {booking.booking_type}")

# Call pricing calculator
pricing = calculate_pricing(
    booking=booking,
    promo_code=booking.promo_code,
    wallet_apply_amount=Decimal('0.00'),
    user=booking.user
)

print("\n" + "="*70)
print("PRICING CALCULATOR RESULT")
print("="*70)
for key, value in pricing.items():
    if isinstance(value, Decimal):
        print(f"{key}: ₹{value}")
    else:
        print(f"{key}: {value}")

print("\n" + "="*70)
print("MISMATCH ANALYSIS")
print("="*70)
print(f"Stored in DB: ₹{booking.total_amount}")
print(f"Calculated fresh: ₹{pricing['total_payable']}")
print(f"Difference: ₹{pricing['total_payable'] - booking.total_amount}")

if hasattr(booking, 'hotel_booking') and booking.hotel_booking:
    hb = booking.hotel_booking
    print(f"\nHotel Booking:")
    print(f"  Room type: {hb.room_type.name}")
    print(f"  Nights: {hb.total_nights}")
    print(f"  Rooms: {hb.number_of_rooms}")
    if hasattr(hb, 'meal_plan') and hb.meal_plan:
        print(f"  Meal plan: {hb.meal_plan.name}")
        print(f"  Meal price/night: ₹{hb.meal_plan.price_per_night}")
