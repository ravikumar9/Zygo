#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.models import Hotel, HotelImage

print("=== HOTEL IMAGES DATA AUDIT ===\n")
for hotel in Hotel.objects.all()[:5]:
    print(f"\nHotel: {hotel.name} (ID: {hotel.id})")
    print(f"  image field: {hotel.image}")
    print(f"  display_image_url: {hotel.display_image_url}")
    
    images = HotelImage.objects.filter(hotel=hotel)
    print(f"  HotelImage records: {images.count()}")
    for img in images:
        print(f"    - {img.id}: {img.image.name if img.image else 'NO FILE'} | is_primary={img.is_primary}")

print("\n=== OTP VERIFICATION STATE ===\n")
from users.models import User
users_sample = User.objects.all()[:3]
for user in users_sample:
    print(f"User: {user.email}")
    print(f"  email_verified_at: {user.email_verified_at}")
    print(f"  phone_verified_at: {user.phone_verified_at}")
    print()

print("\n=== BOOKING STATUS CHECK ===\n")
from bookings.models import Booking
from django.utils import timezone
from datetime import timedelta

now = timezone.now()
ten_mins_ago = now - timedelta(minutes=10)

reserved_bookings = Booking.objects.filter(status='reserved')
for booking in reserved_bookings[:3]:
    print(f"Booking: {booking.booking_id}")
    print(f"  Status: {booking.status}")
    print(f"  reserved_at: {booking.reserved_at}")
    if booking.reserved_at and booking.reserved_at < ten_mins_ago:
        print(f"  ⚠️  SHOULD BE EXPIRED (>{10 * 60}s old)")
    print()
