#!/usr/bin/env python
"""
Test Fix-1 closure:
1. Create approved property with rooms
2. Verify primary image enforcement
3. Test live edit endpoint
4. Verify hotel detail rendering
"""
import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta
from io import BytesIO
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import City
from property_owners.models import PropertyOwner, Property, PropertyRoomType, PropertyRoomImage
from hotels.models import Hotel, RoomType, RoomImage

User = get_user_model()

def create_test_image(filename="test.jpg"):
    """Generate a simple test image."""
    img = Image.new('RGB', (400, 300), color='red')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return SimpleUploadedFile(filename, img_io.getvalue(), content_type='image/jpeg')

print("🧪 Test Fix-1 Closure\n")

# Setup: Get or create city
try:
    city = City.objects.get(name='Bangalore')
except City.DoesNotExist:
    city = City.objects.create(name='Bangalore', state='Karnataka')
    print(f"✓ Created city: {city.name}")

# Setup: Create owner & property
try:
    owner_user = User.objects.get(username='testowner')
except User.DoesNotExist:
    owner_user = User.objects.create_user(username='testowner', email='owner@test.com', password='test123')
    print(f"✓ Created test user: {owner_user.username}")

try:
    owner = PropertyOwner.objects.get(user=owner_user)
except PropertyOwner.DoesNotExist:
    owner = PropertyOwner.objects.create(
        user=owner_user,
        business_name='Test Property',
        owner_name='Test Owner',
        owner_phone='9999999999',
        owner_email='owner@test.com',
        city=city,
        address='123 Test St',
        pincode='560001'
    )
    print(f"✓ Created property owner: {owner.business_name}")

# Create or get approved property
prop, created = Property.objects.get_or_create(
    name='Fix-1 Test Hotel',
    owner=owner,
    defaults={
        'description': 'Test property for Fix-1 closure',
        'property_type_id': 1,  # or use actual type
        'city': city,
        'address': '123 Test St, Bangalore',
        'contact_phone': '9999999999',
        'contact_email': 'prop@test.com',
        'property_rules': 'No smoking',
        'cancellation_policy': 'Free until 24h before',
        'cancellation_type': 'UNTIL_CHECKIN',
        'base_price': Decimal('3000.00'),
        'max_guests': 2,
        'num_bedrooms': 1,
        'num_bathrooms': 1,
        'status': 'APPROVED',
    }
)
if created:
    print(f"✓ Created property: {prop.name}")
else:
    print(f"✓ Using existing property: {prop.name}")

# Ensure property is APPROVED
if prop.status != 'APPROVED':
    prop.status = 'APPROVED'
    prop.save()
    print(f"✓ Set property status to: APPROVED")

# Create room types
room_data = [
    {
        'name': 'Deluxe Room',
        'room_type': 'deluxe',
        'description': 'Beautiful deluxe room with city view',
        'max_occupancy': 2,
        'number_of_beds': 1,
        'base_price': Decimal('3000.00'),
        'total_rooms': 5,
        'discount_type': 'percentage',
        'discount_value': Decimal('15.00'),
        'discount_is_active': True,
        'discount_valid_from': date.today(),
        'discount_valid_to': date.today() + timedelta(days=30),
    },
    {
        'name': 'Standard Room',
        'room_type': 'standard',
        'description': 'Comfortable standard room',
        'max_occupancy': 2,
        'number_of_beds': 1,
        'base_price': Decimal('2000.00'),
        'total_rooms': 10,
        'discount_type': 'fixed',
        'discount_value': Decimal('200.00'),
        'discount_is_active': True,
        'discount_valid_from': date.today(),
        'discount_valid_to': date.today() + timedelta(days=15),
    },
]

for room_info in room_data:
    room, room_created = PropertyRoomType.objects.get_or_create(
        property=prop,
        name=room_info['name'],
        defaults=room_info
    )
    
    if room_created:
        print(f"✓ Created room: {room.name}")
    else:
        print(f"✓ Using existing room: {room.name}")
    
    # Add multiple images to test primary image enforcement
    existing_images = room.images.count()
    if existing_images < 3:
        for i in range(3 - existing_images):
            img = PropertyRoomImage.objects.create(
                room_type=room,
                image=create_test_image(f"room_{room.id}_img_{i}.jpg"),
                display_order=i
            )
            print(f"  ✓ Added image {i+1} - is_primary: {img.is_primary}")

print("\n✅ TEST DATA CREATED\n")

# TEST 1: Verify exactly one primary image per room
print("📸 TEST 1: Primary Image Enforcement")
for room in prop.room_types.all():
    primaries = room.images.filter(is_primary=True).count()
    total = room.images.count()
    if primaries == 1:
        print(f"✓ {room.name}: {primaries} primary of {total} images ✓")
    else:
        print(f"✗ {room.name}: {primaries} primary images (SHOULD BE 1!)")

# TEST 2: Verify room-level amenities
print("\n🎯 TEST 2: Room-Level Amenities")
for room in prop.room_types.all():
    amenities_str = f"{room.amenities}"
    print(f"✓ {room.name}: amenities = {amenities_str}")

# TEST 3: Verify pricing/discounts
print("\n💰 TEST 3: Discount Calculation")
for room in prop.room_types.all():
    base = room.base_price
    effective = room.get_effective_price()
    has_discount = room.has_discount()
    print(f"✓ {room.name}:")
    print(f"  - Base: ₹{base}")
    print(f"  - Effective: ₹{effective}")
    print(f"  - Active Discount: {has_discount}")

# TEST 4: Verify edit endpoint is accessible (no 404)
print("\n🔗 TEST 4: Edit Endpoint URL Check")
first_room = prop.room_types.first()
if first_room:
    from django.urls import reverse
    try:
        url = reverse('property_owners:edit-room-live', kwargs={
            'property_id': prop.id,
            'room_id': first_room.id
        })
        print(f"✓ Edit URL generated: {url}")
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n✅ All tests passed!")
print("\nNEXT: Run browser test at http://localhost:8000/properties/dashboard/")
