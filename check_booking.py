"""Check booking relations"""
import os, sys, django
sys.path.insert(0, r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from bookings.models import Booking, HotelBooking

b = Booking.objects.filter(status='confirmed').last()
print(f"Booking: {b.booking_id}")
print(f"Type: {b.booking_type}")

try:
    hb = b.hotel_booking
    print(f"Has hotel_booking: Yes - {hb}")
    print(f"  Room type: {hb.room_type.name}")
    print(f"  Hotel: {hb.room_type.hotel.name}")
except Exception as e:
    print(f"Has hotel_booking: No - {e}")

try:
    hb = HotelBooking.objects.get(booking=b)
    print(f"HotelBooking exists: Yes - ID={hb.id}")
except Exception as e:
    print(f"HotelBooking exists: No - {e}")
