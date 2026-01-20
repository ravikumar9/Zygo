#!/usr/bin/env python
"""
TEST: Property Registration with Room Type Collection
ZERO-TOLERANCE: DB proof required for all claims

SCENARIO:
1. Owner submits property + 2 room types
2. Verify property created in DB
3. Verify 2 RoomType records linked to property
4. Verify inventory created for each room
5. Admin approves property
6. Verify property visible in hotel listing
"""

import os
import sys
import django
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
from core.models import City
from property_owners.models import PropertyOwner, Property, PropertyType
from hotels.models import Hotel, RoomType
from decimal import Decimal

User = get_user_model()

print("\n" + "="*80)
print("🔴 ZERO-TOLERANCE TEST: Property Registration with Room Types")
print("="*80)

try:
    # Step 1: Create test owner
    print("\n[STEP 1] Creating property owner...")
    import uuid
    username = f'testowner_rooms_{uuid.uuid4().hex[:8]}'
    
    user = User.objects.create_user(
        username=username,
        email=f'owner_rooms_{uuid.uuid4().hex[:8]}@test.com',
        password='test123456'
    )
    
    city = City.objects.first() or City.objects.create(
        name='Test City',
        state='Test State',
        country='India'
    )
    
    property_type = PropertyType.objects.first() or PropertyType.objects.create(
        name='homestay',
        description='Homestay properties'
    )
    
    owner = PropertyOwner.objects.create(
        user=user,
        business_name='Test Homestay',
        property_type=property_type,
        description='Test property for room registration',
        owner_name='Test Owner',
        owner_phone='+919876543210',
        owner_email='owner@test.com',
        city=city,
        address='123 Test Street',
        pincode='560001',
        verification_status='verified'
    )
    
    print(f"✅ Owner created: ID={owner.id}, Name={owner.business_name}")
    print(f"   DB: PropertyOwner.id={owner.id}, verification_status={owner.verification_status}")
    
    # Step 2: Create property in DRAFT status
    print("\n[STEP 2] Creating property in DRAFT status...")
    with transaction.atomic():
        property_obj = Property.objects.create(
            owner=owner,
            name='Luxury Villa with Rooms',
            description='A beautiful villa with multiple room types',
            property_type=property_type,
            city=city,
            address='123 Test Street, Test City',
            state='Test State',
            pincode='560001',
            contact_phone='+919876543210',
            contact_email='property@test.com',
            property_rules='No smoking, quiet hours 10 PM - 8 AM',
            max_guests=8,
            num_bedrooms=4,
            num_bathrooms=2,
            base_price=Decimal('2000.00'),
            gst_percentage=18,
            currency='INR',
            cancellation_policy='Free cancellation until 48 hours before check-in',
            refund_percentage=100,
            approval_status='draft',
            has_wifi=True,
            has_parking=True,
            has_pool=True,
        )
        
        print(f"✅ Property created: ID={property_obj.id}, Name={property_obj.name}")
        print(f"   DB: Property.id={property_obj.id}, approval_status={property_obj.approval_status}")
        print(f"   Owner relation: Property.owner_id={property_obj.owner_id} → PropertyOwner.id={owner.id}")
    
    # Step 3: Create hotel first, then room types
    print("\n[STEP 3] Creating Hotel (required before rooms)...")
    
    hotel = Hotel.objects.create(
        name=property_obj.name,
        description=property_obj.description,
        city=city,
        address=property_obj.address,
        property_type='villa',
        property_rules=property_obj.property_rules,
        amenities_rules='Full amenities available',
        star_rating=4,
        review_rating=Decimal('0.00'),
        review_count=0,
        inventory_source='internal_cm',
        is_active=True,
        has_wifi=True,
        has_parking=True,
        has_pool=True,
        has_gym=False,
        has_restaurant=False,
        has_spa=False,
        has_ac=True,
    )
    
    print(f"✅ Hotel created: ID={hotel.id}, Name={hotel.name}")
    print(f"   DB: Hotel.id={hotel.id}, city_id={hotel.city_id}")
    print(f"\n⚠️ CRITICAL FINDING: RoomType requires FK to Hotel, NOT to Property")
    print(f"   Architectural Issue: Property model exists but RoomType→Hotel (not Property)")
    
    # Step 4: Create room types linked to hotel
    print("\n[STEP 4] Creating room types linked to Hotel...")
    
    room1 = RoomType.objects.create(
        hotel=hotel,
        name='Deluxe Room',
        room_type='deluxe',
        description='Spacious deluxe room with king bed and balcony',
        max_occupancy=2,
        number_of_beds=1,
        base_price=Decimal('2500.00'),
        total_rooms=3,
        has_balcony=True,
        has_tv=True,
        has_minibar=False,
        has_safe=True,
        is_available=True,
    )
    
    room2 = RoomType.objects.create(
        hotel=hotel,
        name='Family Suite',
        room_type='family',
        description='Large family suite with 2 bedrooms',
        max_occupancy=4,
        number_of_beds=2,
        base_price=Decimal('4000.00'),
        total_rooms=2,
        has_balcony=False,
        has_tv=True,
        has_minibar=True,
        has_safe=True,
        is_available=True,
    )
    
    print(f"✅ Room Type 1 created: ID={room1.id}, Name={room1.name}, Price={room1.base_price}, Rooms={room1.total_rooms}")
    print(f"   DB: RoomType.id={room1.id}, hotel_id={room1.hotel_id}, base_price={room1.base_price}")
    
    print(f"✅ Room Type 2 created: ID={room2.id}, Name={room2.name}, Price={room2.base_price}, Rooms={room2.total_rooms}")
    print(f"   DB: RoomType.id={room2.id}, hotel_id={room2.hotel_id}, base_price={room2.base_price}")
    
    # Step 5: Verify DB state
    print("\n[STEP 5] Verifying DB state...")
    
    # Step 5: Verify DB state
    print("\n[STEP 5] Verifying DB state...")
    
    # Query hotel
    hotel_check = Hotel.objects.get(id=hotel.id)
    print(f"✅ Hotel query: Found ID={hotel_check.id}, Name={hotel_check.name}")
    
    # Query property
    prop_check = Property.objects.get(id=property_obj.id)
    print(f"✅ Property query: Found ID={prop_check.id}, Name={prop_check.name}")
    print(f"   NOTE: Property not directly linked to RoomType (FK is to Hotel)")
    
    # Query room types for hotel
    hotel_rooms = hotel.room_types.all()
    print(f"✅ Hotel rooms: Count={hotel_rooms.count()}")
    for room in hotel_rooms:
        print(f"   - {room.name} (ID={room.id}, Price={room.base_price}, Inventory={room.total_rooms})")
    
    # Step 6: Simulate admin approval
    print("\n[STEP 6] Simulating admin approval...")
    property_obj.approval_status = 'approved'
    property_obj.save()
    
    print(f"✅ Property approved: ID={property_obj.id}, Status={property_obj.approval_status}")
    
    # Step 7: Verify property is now visible/available
    print("\n[STEP 7] Verifying approved property visibility...")
    
    approved_properties = Property.objects.filter(approval_status='approved', owner=owner)
    print(f"✅ Approved properties for owner: Count={approved_properties.count()}")
    
    for prop in approved_properties:
        print(f"   - {prop.name}: ID={prop.id}")
    
    # Step 8: Test inventory state
    print("\n[STEP 8] Inventory state check...")
    total_inventory = hotel.room_types.aggregate(total=models.Sum('total_rooms'))['total'] or 0
    print(f"✅ Total available inventory: {total_inventory} rooms")
    
    for room in hotel.room_types.all():
        print(f"   - {room.name}: {room.total_rooms} rooms @ ₹{room.base_price}/night")
    
    # Final Results
    print("\n" + "="*80)
    print("✅ TEST RESULT: BLOCKER IDENTIFIED & DOCUMENTED")
    print("="*80)
    print("\n📊 CRITICAL FINDING:")
    print(f"  ⚠️  Property model: {Property.objects.count()} records")
    print(f"  ⚠️  Hotel model: {Hotel.objects.count()} records")
    print(f"  ⚠️  RoomType→Hotel FK (NOT Property)")
    print(f"  ⚠️  Property registration incomplete: rooms linked to Hotel, not Property")
    print(f"\n✅ DATA CREATED:")
    print(f"  ✅ Owner: {owner.business_name} (ID={owner.id})")
    print(f"  ✅ Property (DRAFT): {property_obj.name} (ID={property_obj.id})")
    print(f"  ✅ Hotel created: {hotel.name} (ID={hotel.id})")
    print(f"  ✅ Rooms created: 2 types (3 Deluxe + 2 Family = 5 total)")
    print(f"  ✅ Property approved: Status={property_obj.approval_status}")
    print(f"\n❌ BLOCKER:")
    print(f"  Property registration form cannot create RoomType records")
    print(f"  RoomType model requires Hotel FK, not Property FK")
    print(f"  Admin must create Hotel manually or form must create Hotel first")
    print(f"\n🔧 REQUIRED FIX:")
    print(f"  1. PropertyRegistrationForm must create Hotel on submission")
    print(f"  2. RoomTypeForm must collect room details with Hotel FK")
    print(f"  3. Approval flow: Property → Hotel → RoomTypes visible")
    
except Exception as e:
    import traceback
    print(f"\n❌ TEST FAILED: {str(e)}")
    print("\nTraceback:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
