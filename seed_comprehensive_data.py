#!/usr/bin/env python
"""
FIX-6: COMPREHENSIVE DATA SEEDING
Populates cities, landmarks, hotels, rooms, buses with realistic data
"""
import os
import sys
import django
from decimal import Decimal
from datetime import date, time, timedelta
from io import BytesIO
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from core.models import City
from property_owners.models import PropertyOwner, Property, PropertyRoomType, PropertyRoomImage
from hotels.models import Hotel, RoomType, RoomImage, RoomMealPlan
from buses.models import Bus, BusSchedule, BusRoute

User = get_user_model()

def create_test_image(name="test.jpg", color=(255, 0, 0)):
    """Generate a test image."""
    img = Image.new('RGB', (400, 300), color=color)
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return SimpleUploadedFile(name, img_io.getvalue(), content_type='image/jpeg')

# ============================================================================
# PHASE 1: CITIES & AREAS
# ============================================================================
print("\n" + "=" * 80)
print("PHASE 1: SEEDING CITIES & AREAS")
print("=" * 80)

city_data = {
    'Bangalore': {
        'state': 'Karnataka',
        'code': 'BLR',
        'lat': 12.9716,
        'lng': 77.5946,
        'is_popular': True,
    },
    'Mumbai': {
        'state': 'Maharashtra',
        'code': 'MUM',
        'lat': 19.0760,
        'lng': 72.8777,
        'is_popular': True,
    },
    'Coorg': {
        'state': 'Karnataka',
        'code': 'COO',
        'lat': 12.3381,
        'lng': 75.7408,
        'is_popular': True,
    },
    'Ooty': {
        'state': 'Tamil Nadu',
        'code': 'OOT',
        'lat': 11.4102,
        'lng': 76.6955,
        'is_popular': True,
    },
    'Goa': {
        'state': 'Goa',
        'code': 'GOA',
        'lat': 15.2993,
        'lng': 73.8243,
        'is_popular': True,
    }
}

cities = {}
for city_name, city_info in city_data.items():
    city, created = City.objects.get_or_create(
        name=city_name,
        defaults={
            'state': city_info['state'],
            'code': city_info['code'],
            'is_popular': city_info['is_popular'],
        }
    )
    cities[city_name] = city
    status = "✓ Created" if created else "→ Exists"
    print(f"{status}: {city_name} ({city.state})")

# ============================================================================
# PHASE 2: LANDMARKS (Tourism Cities)
# ============================================================================
print("\n" + "=" * 80)
print("PHASE 2: LANDMARKS (Stored as Hotel Descriptions)")
print("=" * 80)
print("Note: Area/Landmark models to be created in future phase")

# ============================================================================
# PHASE 3: HOTELS & ROOMS
# ============================================================================
print("\n" + "=" * 80)
print("PHASE 3: SEEDING HOTELS & ROOMS")
print("=" * 80)

# Create a property owner for seeded hotels
owner_user, _ = User.objects.get_or_create(
    username='seedowner',
    defaults={'email': 'seedowner@goexplorer.com', 'first_name': 'Seed', 'last_name': 'Owner'}
)
owner, _ = PropertyOwner.objects.get_or_create(
    user=owner_user,
    defaults={
        'business_name': 'Seed Hotels Network',
        'owner_name': 'Seed Owner',
        'owner_phone': '9999999999',
        'owner_email': 'seedowner@goexplorer.com',
        'city': cities['Bangalore'],
        'address': 'Tech Park, Bangalore',
        'pincode': '560001',
    }
)

hotel_data = {
    'Bangalore': [
        {
            'name': 'Tech City Hotel',
            'lat': 12.9698,
            'lng': 77.7499,
            'base_price': 2500,
            'rooms': [
                {'name': 'Standard Room', 'base_price': 2500, 'occupancy': 2, 'beds': 1, 'amenities': ['tv', 'ac', 'wifi']},
                {'name': 'Deluxe Room', 'base_price': 4000, 'occupancy': 2, 'beds': 1, 'amenities': ['balcony', 'tv', 'minibar', 'safe']},
                {'name': 'Suite', 'base_price': 6500, 'occupancy': 4, 'beds': 2, 'amenities': ['balcony', 'tv', 'minibar', 'safe']},
            ]
        },
        {
            'name': 'Airport Comfort Inn',
            'lat': 13.1939,
            'lng': 77.7064,
            'base_price': 2000,
            'rooms': [
                {'name': 'Economy Room', 'base_price': 2000, 'occupancy': 1, 'beds': 1, 'amenities': ['tv', 'ac']},
                {'name': 'Standard Room', 'base_price': 2800, 'occupancy': 2, 'beds': 1, 'amenities': ['tv', 'ac', 'wifi']},
            ]
        },
    ],
    'Mumbai': [
        {
            'name': 'BKC Business Hotel',
            'lat': 19.0176,
            'lng': 72.8479,
            'base_price': 3500,
            'rooms': [
                {'name': 'Business Room', 'base_price': 3500, 'occupancy': 2, 'beds': 1, 'amenities': ['tv', 'wifi', 'safe']},
                {'name': 'Deluxe', 'base_price': 5500, 'occupancy': 2, 'beds': 1, 'amenities': ['balcony', 'tv', 'minibar']},
            ]
        },
    ],
    'Coorg': [
        {
            'name': 'Coorg Heritage Resort',
            'lat': 12.4381,
            'lng': 75.7408,
            'base_price': 3000,
            'rooms': [
                {'name': 'Cottage', 'base_price': 3000, 'occupancy': 2, 'beds': 1, 'amenities': ['balcony', 'tv', 'ac']},
                {'name': 'Deluxe Cottage', 'base_price': 4500, 'occupancy': 2, 'beds': 1, 'amenities': ['balcony', 'tv', 'minibar']},
                {'name': 'Suite', 'base_price': 6000, 'occupancy': 4, 'beds': 2, 'amenities': ['balcony', 'tv', 'minibar', 'safe']},
            ]
        },
    ],
    'Ooty': [
        {
            'name': 'Nilgiri Hill Resort',
            'lat': 11.3534,
            'lng': 76.8122,
            'base_price': 2500,
            'rooms': [
                {'name': 'Hill View Room', 'base_price': 2500, 'occupancy': 2, 'beds': 1, 'amenities': ['balcony', 'tv', 'ac']},
                {'name': 'Luxury Suite', 'base_price': 5000, 'occupancy': 3, 'beds': 2, 'amenities': ['balcony', 'tv', 'minibar', 'safe']},
            ]
        },
    ],
    'Goa': [
        {
            'name': 'Goa Beach Resort',
            'lat': 15.5833,
            'lng': 73.8333,
            'base_price': 3500,
            'rooms': [
                {'name': 'Beach View Room', 'base_price': 3500, 'occupancy': 2, 'beds': 1, 'amenities': ['balcony', 'tv', 'ac', 'wifi']},
                {'name': 'Beachfront Suite', 'base_price': 6000, 'occupancy': 4, 'beds': 2, 'amenities': ['balcony', 'tv', 'minibar', 'safe']},
            ]
        },
    ],
}

amenity_map = {
    'tv': 'has_tv',
    'balcony': 'has_balcony',
    'minibar': 'has_minibar',
    'safe': 'has_safe',
    'ac': None,  # Property level
    'wifi': None,  # Property level
}

hotel_count = 0
for city_name, hotels in hotel_data.items():
    city = cities[city_name]
    for hotel_info in hotels:
        hotel, created = Hotel.objects.get_or_create(
            name=hotel_info['name'],
            city=city,
            defaults={
                'description': f'Beautiful {hotel_info["name"]} in {city_name}',
                'address': f'{hotel_info["name"]}, {city_name}',
                'latitude': Decimal(str(hotel_info['lat'])),
                'longitude': Decimal(str(hotel_info['lng'])),
                'property_type': 'hotel',
                'star_rating': 4,
                'contact_phone': '9876543210',
                'contact_email': f'{hotel_info["name"].lower().replace(" ", ".")}@hotel.com',
                'has_wifi': True,
                'has_ac': True,
                'has_parking': True,
                'has_pool': True,
                'cancellation_type': 'UNTIL_CHECKIN',
                'refund_percentage': 100,
            }
        )
        hotel_count += 1
        status = "✓ Created" if created else "→ Exists"
        print(f"\n{status}: {hotel.name} ({city.name})")
        
        # Create rooms
        for room_info in hotel_info['rooms']:
            room, room_created = RoomType.objects.get_or_create(
                hotel=hotel,
                name=room_info['name'],
                defaults={
                    'description': f'{room_info["name"]} in {hotel.name}',
                    'room_type': 'standard',
                    'max_occupancy': room_info['occupancy'],
                    'number_of_beds': room_info['beds'],
                    'base_price': Decimal(str(room_info['base_price'])),
                    'total_rooms': 3,
                    'has_tv': 'tv' in room_info['amenities'],
                    'has_balcony': 'balcony' in room_info['amenities'],
                    'has_minibar': 'minibar' in room_info['amenities'],
                    'has_safe': 'safe' in room_info['amenities'],
                }
            )
            room_status = "  ✓ Room" if room_created else "  → Room"
            print(f"{room_status}: {room.name} (₹{room.base_price}/night)")
            
            # Add room images
            if room_created or room.images.count() == 0:
                for i in range(2):
                    img = RoomImage.objects.create(
                        room_type=room,
                        image=create_test_image(f"{hotel.name}_{room.name}_{i}.jpg", color=(0, 100 + i * 50, 200)),
                        is_primary=(i == 0),
                        display_order=i
                    )
                    print(f"    ✓ Image {i+1}")

print(f"\n✅ Hotels seeded: {hotel_count}")

# ============================================================================
# PHASE 4: BUSES
# ============================================================================
print("\n" + "=" * 80)
print("PHASE 4: SEEDING BUSES")
print("=" * 80)

from buses.models import BusOperator

# Create operator
operator, _ = BusOperator.objects.get_or_create(
    name='GoExplorer Buses',
    defaults={
        'contact_phone': '9876543210',
        'contact_email': 'buses@goexplorer.com',
        'registered_address': 'Bangalore',
    }
)

bus_data = [
    {
        'name': 'Express AC - BLR to Coorg',
        'source': 'Bangalore',
        'destination': 'Coorg',
        'bus_type': 'AC',
        'seats': 40,
        'price': 800,
        'departure_time': '20:00',
    },
    {
        'name': 'Super Luxury - Bangalore to Ooty',
        'source': 'Bangalore',
        'destination': 'Ooty',
        'bus_type': 'AC',
        'seats': 32,
        'price': 1200,
        'departure_time': '18:00',
    },
    {
        'name': 'Non-AC Budget - Bangalore to Goa',
        'source': 'Bangalore',
        'destination': 'Goa',
        'bus_type': 'Non-AC',
        'seats': 50,
        'price': 600,
        'departure_time': '22:00',
    },
]

for bus_info in bus_data:
    source_city = cities.get(bus_info['source'])
    dest_city = cities.get(bus_info['destination'])
    
    if not source_city or not dest_city:
        continue
    
    bus_num = f"GE{bus_data.index(bus_info)+1:04d}"
    
    bus, created = Bus.objects.get_or_create(
        operator=operator,
        bus_number=bus_num,
        defaults={
            'bus_name': bus_info['name'],
            'bus_type': 'ac_seater' if bus_info['bus_type'] == 'AC' else 'seater',
            'total_seats': bus_info['seats'],
            'registration_number': f"KA01AB{bus_data.index(bus_info)+1:04d}",
            'manufacturing_year': 2022,
            'has_ac': bus_info['bus_type'] == 'AC',
            'has_wifi': True,
            'has_charging_point': True,
            'has_emergency_exit': True,
            'has_first_aid': True,
            'is_active': True,
        }
    )
    
    status = "✓ Created" if created else "→ Exists"
    print(f"\n{status}: {bus.bus_name}")
    print(f"  Type: {bus.bus_type} | Seats: {bus.total_seats}")
    
    # Create route
    route, route_created = BusRoute.objects.get_or_create(
        bus=bus,
        route_name=bus_info['name'],
        defaults={
            'source_city': source_city,
            'destination_city': dest_city,
            'departure_time': time(int(bus_info['departure_time'].split(':')[0]), int(bus_info['departure_time'].split(':')[1])),
            'arrival_time': time((int(bus_info['departure_time'].split(':')[0]) + 4) % 24, int(bus_info['departure_time'].split(':')[1])),
            'duration_hours': Decimal('4.0'),
            'distance_km': Decimal('250.0'),
            'base_fare': Decimal(str(bus_info['price'])),
            'is_active': True,
        }
    )
    
    # Create schedule for next 7 days
    for day_offset in range(7):
        schedule_date = date.today() + timedelta(days=day_offset)
        
        BusSchedule.objects.get_or_create(
            route=route,
            date=schedule_date,
            defaults={
                'available_seats': bus_info['seats'],
                'booked_seats': 0,
                'fare': Decimal(str(bus_info['price'])),
                'is_active': True,
            }
        )
    print(f"  ✓ Route & 7-day schedule created")

# ============================================================================
# VERIFICATION
# ============================================================================
print("\n" + "=" * 80)
print("VERIFICATION & SUMMARY")
print("=" * 80)

print(f"\n✅ Cities: {City.objects.count()}")
print(f"✅ Hotels: {Hotel.objects.count()}")
print(f"✅ Room Types: {RoomType.objects.count()}")
print(f"✅ Room Images: {RoomImage.objects.count()}")
print(f"✅ Buses: {Bus.objects.count()}")
print(f"✅ Bus Schedules: {BusSchedule.objects.count()}")

print("\n" + "=" * 80)
print("🎉 FIX-6 DATA SEEDING COMPLETE")
print("=" * 80)
print("\nAll data is ready for search, suggestions, and near-me features!")
