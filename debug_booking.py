#!/usr/bin/env python
"""
SIMPLE DEBUG TEST FOR GUEST BOOKING

Just check if we can POST and what response we get.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from hotels.models import Hotel, RoomType
from datetime import datetime, timedelta

client = Client()

hotel = Hotel.objects.filter(is_active=True).first()
if not hotel:
    print("No active hotel")
    sys.exit(1)

room_type = hotel.room_types.first()
if not room_type:
    print("No room types")
    sys.exit(1)

print(f"Hotel: {hotel.name} (ID: {hotel.id})")
print(f"Room: {room_type.name} (ID: {room_type.id})")

today = datetime.now().date()
checkin = today + timedelta(days=5)
checkout = today + timedelta(days=7)

print(f"\nDates:")
print(f"  Today: {today}")
print(f"  Check-in: {checkin} (format: {checkin.strftime('%Y-%m-%d')})")
print(f"  Check-out: {checkout} (format: {checkout.strftime('%Y-%m-%d')})")

data = {
    'room_type_id': str(room_type.id),
    'check_in': checkin.strftime('%Y-%m-%d'),
    'check_out': checkout.strftime('%Y-%m-%d'),
    'num_guests': '2',
    'number_of_rooms': '1',
    'guest_name': 'Test Guest',
    'guest_email': 'test@example.com',
    'guest_phone': '+919999999999',
}

url = f'/hotels/{hotel.id}/book/'
print(f"\nPOSTing to {url} as unauthenticated user...")
print(f"Data: {data}")

response = client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

print(f"\nStatus: {response.status_code}")
print(f"Response: {response.content.decode()[:500]}")
