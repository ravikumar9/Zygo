#!/usr/bin/env python
"""Test OTP enforcement in booking views"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from bookings.models import Booking

User = get_user_model()
client = Client()

# Get or create unverified user
unverified_user, _ = User.objects.get_or_create(
    email='test_unverified@goexplorer.com',
    defaults={
        'username': 'test_unverified',
        'phone': '9876543210'
    }
)
unverified_user.set_password('testpass123')
unverified_user.save()

# Get a booking
booking = Booking.objects.first()
if not booking:
    print("✗ No bookings in database")
else:
    # Login as unverified user
    client.login(username='test_unverified@goexplorer.com', password='testpass123')
    
    # Try to access booking confirmation
    response = client.get(f'/bookings/{booking.booking_id}/')
    
    print(f"Booking: {booking.booking_id}")
    print(f"User: {unverified_user.email}")
    print(f"email_verified_at: {unverified_user.email_verified_at}")
    print(f"phone_verified_at: {unverified_user.phone_verified_at}")
    print(f"\nResponse status: {response.status_code}")
    print(f"Redirected to: {response.url if response.status_code == 302 else 'N/A'}")
    
    if response.status_code == 302:
        print("✓ OTP verification redirected correctly")
    else:
        print("✗ No redirect")
