#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from bookings.models import Booking

b = Booking.objects.filter(customer_email='test@example.com').first()
if b:
    print(f"✓ Booking found: {b.booking_id}")
    print(f"  User: {b.user}")
    print(f"  Customer Email: {b.customer_email}")
    print(f"  Status: {b.status}")
    print(f"  Type: {b.booking_type}")
    print(f"\n✅ GUEST BOOKING CREATED SUCCESSFULLY")
else:
    print("✗ Booking not found")
