#!/usr/bin/env python
"""Check if hotel 8 has Suite room type"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.models import Hotel, RoomType

hotel8 = Hotel.objects.get(id=8)
print(f'Hotel 8: {hotel8.name}')
print('Room types:')
for rt in hotel8.room_types.all():
    print(f'  - {rt.room_type} ({rt.name})')

# Check if Suite exists
suite = hotel8.room_types.filter(room_type='suite').first()
if suite:
    print(f'\n✓ Suite found: {suite.name}')
else:
    print('\n✗ No Suite room type - creating one...')
    suite = RoomType.objects.create(
        hotel=hotel8,
        room_type='suite',
        name='Premium Suite',
        description='Luxurious suite with separate living area',
        base_price=12000,
        max_occupancy=4,
        is_active=True,
        approval_status='APPROVED'
    )
    print(f'✓ Created Suite: {suite.name}')
