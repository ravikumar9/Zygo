"""
CLEAN TEST DATA SEED SCRIPT - Production Ready
Only creates data that actually fits the model schema
Run with: python manage.py shell < seed_data_clean.py
"""

from users.models import User, UserProfile
from hotels.models import Hotel, RoomType
from buses.models import BusOperator, Bus, BusRoute, BusSchedule, BoardingPoint, DroppingPoint
from packages.models import Package
from core.models import City, CorporateDiscount
from django.utils import timezone
from datetime import date, timedelta

print("\n" + "="*80)
print("CLEAN TEST DATA SEEDING")
print("="*80)

# ============================================================================
# CITIES
# ============================================================================
print("\n[1] Creating cities...")
cities = {}
for city_name in ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Pune']:
    city, created = City.objects.get_or_create(
        name=city_name,
        defaults={'code': city_name[:3].upper(), 'state': 'India'}
    )
    cities[city_name] = city
    if created:
        print(f"  ✓ {city_name}")

# ============================================================================
# TEST USERS
# ============================================================================
print("\n[2] Creating test users...")

# User 1: Email verified only
user1, created = User.objects.get_or_create(
    username='qa_email_verified',
    defaults={
        'email': 'qa_email_verified@example.com',
        'first_name': 'QA',
        'last_name': 'EmailOnly'
    }
)
if created:
    user1.set_password('TestPassword123!')
    user1.save()
profile1, _ = UserProfile.objects.get_or_create(user=user1)
profile1.phone = '9876543210'
profile1.email_verified_at = timezone.now()
profile1.save()
print(f"  ✓ qa_email_verified (email-verified only)")

# User 2: Both verified
user2, created = User.objects.get_or_create(
    username='qa_both_verified',
    defaults={
        'email': 'qa_both_verified@example.com',
        'first_name': 'QA',
        'last_name': 'BothVerified'
    }
)
if created:
    user2.set_password('TestPassword123!')
    user2.save()
profile2, _ = UserProfile.objects.get_or_create(user=user2)
profile2.phone = '9876543211'
profile2.email_verified_at = timezone.now()
profile2.phone_verified_at = timezone.now()
profile2.save()
print(f"  ✓ qa_both_verified (email + mobile verified)")

# ============================================================================
# HOTELS WITH AMENITIES
# ============================================================================
print("\n[3] Creating hotels with amenities...")

hotels_config = [
    {
        'name': 'QA Premium Hotel Mumbai',
        'city': cities['Mumbai'],
        'star_rating': 5,
        'description': 'Premium 5-star hotel with all amenities',
        'amenities': {'wifi': True, 'parking': True, 'pool': True, 'gym': True, 'restaurant': True, 'spa': True}
    },
    {
        'name': 'QA Budget Hotel Bangalore',
        'city': cities['Bangalore'],
        'star_rating': 2,
        'description': 'Budget-friendly hotel for testing',
        'amenities': {'wifi': True, 'parking': False, 'pool': False, 'gym': False, 'restaurant': False, 'spa': False}
    }
]

for hotel_cfg in hotels_config:
    amenities = hotel_cfg.pop('amenities')
    hotel, created = Hotel.objects.get_or_create(
        name=hotel_cfg['name'],
        city=hotel_cfg['city'],
        defaults={
            **hotel_cfg,
            'address': f"Test Address in {hotel_cfg['city'].name}",
            'contact_phone': '9876543210',
            'contact_email': 'hotel@test.com',
            'is_active': True,
            'has_wifi': amenities['wifi'],
            'has_parking': amenities['parking'],
            'has_pool': amenities['pool'],
            'has_gym': amenities['gym'],
            'has_restaurant': amenities['restaurant'],
            'has_spa': amenities['spa'],
        }
    )
    
    if created:
        print(f"  ✓ {hotel.name} ({hotel.star_rating}★)")
        
        # Create room types
        room_configs = [
            {'name': 'Standard Room', 'price': 3000, 'max_occupancy': 2},
            {'name': 'Deluxe Room', 'price': 5000, 'max_occupancy': 2},
            {'name': 'Suite', 'price': 8000, 'max_occupancy': 4},
        ]
        
        for room_cfg in room_configs:
            room, _ = RoomType.objects.get_or_create(
                hotel=hotel,
                name=room_cfg['name'],
                defaults={
                    'base_price': room_cfg['price'],
                    'max_occupancy': room_cfg['max_occupancy'],
                    'description': f"Comfortable {room_cfg['name']} with basic amenities",
                    'total_rooms': 10,
                }
            )
            print(f"    - {room_cfg['name']} (₹{room_cfg['price']})")

# ============================================================================
# BUS INFRASTRUCTURE
# ============================================================================
print("\n[4] Creating bus operator, bus, routes, and schedules...")

# Operator
operator, created = BusOperator.objects.get_or_create(
    name='QA Test Bus Operator',
    defaults={
        'contact_phone': '9876543210',
        'contact_email': 'operator@test.com',
        'is_active': True,
    }
)
if created:
    print(f"  ✓ Bus Operator: {operator.name}")

# Bus
bus, created = Bus.objects.get_or_create(
    bus_number='QA-TEST-BUS-001',
    operator=operator,
    defaults={
        'bus_name': 'QA Test Express',
        'bus_type': 'ac_seater',
        'total_seats': 45,
        'has_ac': True,
        'has_wifi': True,
        'has_charging_point': True,
        'is_active': True,
    }
)
if created:
    print(f"  ✓ Bus: {bus.bus_name} ({bus.total_seats} seats)")

# Route - ALL REQUIRED FIELDS
route, created = BusRoute.objects.get_or_create(
    source_city=cities['Mumbai'],
    destination_city=cities['Bangalore'],
    bus=bus,
    departure_time='08:00:00',
    defaults={
        'route_name': f"{cities['Mumbai'].name} → {cities['Bangalore'].name}",
        'arrival_time': '18:00:00',
        'duration_hours': 10.0,
        'distance_km': 840.0,
        'base_fare': 1200.00,
        'is_active': True,
    }
)
if created:
    print(f"  ✓ Route: {route.route_name}")

# Boarding & Dropping Points
if not BoardingPoint.objects.filter(route=route).exists():
    BoardingPoint.objects.create(
        route=route,
        name='Mumbai Central Bus Stand',
        city=cities['Mumbai'],
        pickup_time='08:00',
        sequence_order=1,
    )
    print(f"  ✓ Boarding Point: Mumbai Central")

if not DroppingPoint.objects.filter(route=route).exists():
    DroppingPoint.objects.create(
        route=route,
        name='Bangalore Bus Station',
        city=cities['Bangalore'],
        drop_time='18:00',
        sequence_order=1,
    )
    print(f"  ✓ Dropping Point: Bangalore Station")

# Schedules for next 7 days
print(f"  ✓ Creating schedules for next 7 days...")
today = date.today()
schedule_count = 0
for i in range(7):
    travel_date = today + timedelta(days=i+1)
    schedule, created = BusSchedule.objects.get_or_create(
        route=route,
        date=travel_date,
        defaults={
            'available_seats': 40,
            'booked_seats': 0,
            'fare': 1200.00,
            'window_seat_charge': 150.00,
            'is_active': True,
        }
    )
    if created:
        schedule_count += 1

print(f"    - {schedule_count} schedules created")

# ============================================================================
# PACKAGES
# ============================================================================
print("\n[5] Creating holiday packages...")

package, created = Package.objects.get_or_create(
    name='QA Test Holiday Package',
    defaults={
        'description': 'Test package for QA verification',
        'package_type': 'adventure',
        'duration_days': 5,
        'duration_nights': 4,
        'starting_price': 12000,
        'is_active': True,
        'is_featured': True,
    }
)
if created:
    # Add destination city using many-to-many
    package.destination_cities.add(cities['Bangalore'])
    print(f"  ✓ {package.name} (5 days → Bangalore)")

# ============================================================================
# CORPORATE DISCOUNT
# ============================================================================
print("\n[6] Setting up corporate discount...")

corp, created = CorporateDiscount.objects.get_or_create(
    company_name='QA Test Corp',
    email_domain='qatest.com',
    defaults={
        'discount_type': 'percentage',
        'discount_value': 20,
        'is_active': True,
    }
)
if created:
    print(f"  ✓ Corporate: {corp.company_name} (@{corp.email_domain}) - 20% off")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("✓ TEST DATA SEEDING COMPLETE")
print("="*80)

print(f"\n✓ Users: {User.objects.count()}")
print(f"✓ Hotels: {Hotel.objects.count()}")
print(f"✓ Room Types: {RoomType.objects.count()}")
print(f"✓ Buses: {Bus.objects.count()}")
print(f"✓ Routes: {BusRoute.objects.count()}")
print(f"✓ Schedules: {BusSchedule.objects.count()}")
print(f"✓ Packages: {Package.objects.count()}")
print(f"✓ Cities: {City.objects.count()}")

print("\n" + "="*80)
print("TEST CREDENTIALS")
print("="*80)

print("\nUser 1 (Email-verified only):")
print("  Email: qa_email_verified@example.com")
print("  Password: TestPassword123!")
print("  Verified: Email ✓, Mobile ✗")

print("\nUser 2 (Both verified):")
print("  Email: qa_both_verified@example.com")
print("  Password: TestPassword123!")
print("  Verified: Email ✓, Mobile ✓")

print("\n✓ Ready for UI testing!")
print("="*80 + "\n")
