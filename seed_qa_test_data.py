"""
Test data seeding script for QA verification
Run with: python manage.py shell < seed_qa_test_data.py
"""

from django.contrib.auth.models import User as DjangoUser
from users.models import User, UserProfile  # Use custom User model
from hotels.models import Hotel, RoomType, HotelImage
from buses.models import BusOperator, Bus, BusRoute, BusSchedule, BoardingPoint, DroppingPoint
from packages.models import Package
from core.models import City, CorporateDiscount
from django.utils import timezone
from datetime import date, timedelta
import json

print("\n" + "="*80)
print("QA TEST DATA SEEDING SCRIPT")
print("="*80)

# ============================================================================
# SETUP: Create base cities
# ============================================================================
print("\n[SETUP] Creating base cities...")
cities = {}
for city_name in ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Pune']:
    city, created = City.objects.get_or_create(
        name=city_name,
        defaults={'code': city_name[:3].upper(), 'state': 'Test State'}
    )
    cities[city_name] = city
    if created:
        print(f"  ✓ Created city: {city_name}")

# ============================================================================
# TEST USER 1: Email verified only (mobile optional)
# ============================================================================
print("\n[USER 1] Creating test user with email verified only...")
user1, created = User.objects.get_or_create(
    username='qa_email_verified',
    defaults={
        'email': 'qa_email_verified@test.com',
        'first_name': 'QA',
        'last_name': 'Tester1'
    }
)
if created:
    user1.set_password('TestPassword123!')
    user1.save()

profile1, _ = UserProfile.objects.get_or_create(user=user1)
profile1.phone = '9876543210'
profile1.email_verified = True
profile1.email_verified_at = timezone.now()
profile1.phone_verified = False
profile1.phone_verified_at = None
profile1.save()
print(f"  ✓ Created user: {user1.username}")
print(f"    - Email verified: {profile1.email_verified_at is not None}")
print(f"    - Mobile verified: {profile1.phone_verified_at is not None}")

# ============================================================================
# TEST USER 2: Both verified (for comparison)
# ============================================================================
print("\n[USER 2] Creating test user with both verified...")
user2, created = User.objects.get_or_create(
    username='qa_both_verified',
    defaults={
        'email': 'qa_both_verified@test.com',
        'first_name': 'QA',
        'last_name': 'Tester2'
    }
)
if created:
    user2.set_password('TestPassword123!')
    user2.save()

profile2, _ = UserProfile.objects.get_or_create(user=user2)
profile2.phone = '9876543211'
profile2.email_verified = True
profile2.email_verified_at = timezone.now()
profile2.phone_verified = True
profile2.phone_verified_at = timezone.now()
profile2.save()
print(f"  ✓ Created user: {user2.username}")

# ============================================================================
# HOTELS with images
# ============================================================================
print("\n[HOTELS] Creating test hotels with images...")
hotel_data = [
    {
        'name': 'QA Test Hotel Mumbai',
        'city': cities['Mumbai'],
        'description': 'Premium test hotel with full amenities',
        'star_rating': 5,
        'has_wifi': True,
        'has_parking': True,
        'has_pool': True,
        'has_gym': True,
        'has_restaurant': True,
        'is_featured': True,
        'gst_percentage': 18,
    },
    {
        'name': 'QA Test Hotel Bangalore',
        'city': cities['Bangalore'],
        'description': 'Comfortable test hotel',
        'star_rating': 3,
        'has_wifi': True,
        'has_parking': True,
        'has_pool': False,
        'has_gym': True,
        'has_restaurant': True,
        'is_featured': False,
        'gst_percentage': 18,
    }
]

hotels = []
for data in hotel_data:
    hotel, created = Hotel.objects.get_or_create(
        name=data['name'],
        city=data['city'],
        defaults=data
    )
    if created:
        print(f"  ✓ Created hotel: {hotel.name}")
    
    # Create room types
    room_types = [
        {'name': 'Single Room', 'base_price': 3000},
        {'name': 'Double Room', 'base_price': 5000},
        {'name': 'Suite', 'base_price': 8000},
    ]
    for rt_data in room_types:
        RoomType.objects.get_or_create(
            hotel=hotel,
            name=rt_data['name'],
            defaults={'base_price': rt_data['base_price']}
        )
    
    hotels.append(hotel)
    print(f"    - Created {len(room_types)} room types")

# ============================================================================
# BUSES with schedules
# ============================================================================
print("\n[BUSES] Creating test bus operator, buses, and schedules...")

# Create operator
operator, created = BusOperator.objects.get_or_create(
    name='QA Test Bus Operator',
    defaults={
        'contact_phone': '1234567890',
        'contact_email': 'operator@test.com',
        'verification_status': 'verified',
        'verified_at': timezone.now(),
        'is_active': True,
    }
)
if created:
    print(f"  ✓ Created operator: {operator.name}")

# Create bus
bus, created = Bus.objects.get_or_create(
    bus_number='QA-TEST-001',
    operator=operator,
    defaults={
        'bus_name': 'QA Test Bus',
        'bus_type': 'ac_seater',
        'total_seats': 45,
        'has_ac': True,
        'has_wifi': True,
        'has_charging_point': True,
        'is_active': True,
    }
)
if created:
    print(f"  ✓ Created bus: {bus.bus_name}")

# Create route
route, created = BusRoute.objects.get_or_create(
    source_city=cities['Mumbai'],
    destination_city=cities['Bangalore'],
    bus=bus,
    defaults={
        'route_name': f"{cities['Mumbai'].name} to {cities['Bangalore'].name}",
        'total_distance': 840,
        'is_active': True,
    }
)
if created:
    print(f"  ✓ Created route: {route.route_name}")

# Create boarding and dropping points
if not BoardingPoint.objects.filter(route=route).exists():
    BoardingPoint.objects.create(
        route=route,
        name='Mumbai Central',
        city=cities['Mumbai'],
        pickup_time='08:00',
        sequence_order=1,
    )
    print(f"  ✓ Created boarding point: Mumbai Central")

if not DroppingPoint.objects.filter(route=route).exists():
    DroppingPoint.objects.create(
        route=route,
        name='Bangalore Kempegowda',
        city=cities['Bangalore'],
        drop_time='18:00',
        sequence_order=1,
    )
    print(f"  ✓ Created dropping point: Bangalore Kempegowda")

# Create schedules
today = date.today()
for i in range(5):
    travel_date = today + timedelta(days=i+1)
    schedule, created = BusSchedule.objects.get_or_create(
        route=route,
        date=travel_date,
        defaults={
            'available_seats': 40,
            'booked_seats': 0,
            'fare': 1500.00,
            'window_seat_charge': 200.00,
            'is_active': True,
        }
    )
    if created:
        print(f"  ✓ Created schedule for {travel_date}")

# ============================================================================
# PACKAGES
# ============================================================================
print("\n[PACKAGES] Creating test packages...")
package, created = Package.objects.get_or_create(
    name='QA Test Package',
    defaults={
        'description': 'Test holiday package',
        'package_type': 'adventure',
        'duration_days': 5,
        'duration_nights': 4,
        'starting_price': 15000,
        'destination': cities['Bangalore'],
        'is_active': True,
        'is_featured': True,
    }
)
if created:
    print(f"  ✓ Created package: {package.name}")

# ============================================================================
# CORPORATE DISCOUNT
# ============================================================================
print("\n[CORPORATE] Setting up corporate discount...")
corp_discount, created = CorporateDiscount.objects.get_or_create(
    company_name='QA Test Corporation',
    email_domain='qa-test.com',
    defaults={
        'discount_type': 'percentage',
        'discount_value': 15,
        'service_types': ['all'],
        'is_active': True,
        'notes': 'QA test corporate discount',
    }
)
if created:
    print(f"  ✓ Created corporate discount for {corp_discount.email_domain}")
    print(f"    - Discount: {corp_discount.discount_value}% off")

# ============================================================================
# VERIFY SETUP
# ============================================================================
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

print(f"\n✓ Users created: {User.objects.count()}")
print(f"✓ Hotels created: {Hotel.objects.count()}")
print(f"✓ Buses created: {Bus.objects.count()}")
print(f"✓ Bus routes created: {BusRoute.objects.count()}")
print(f"✓ Bus schedules created: {BusSchedule.objects.count()}")
print(f"✓ Packages created: {Package.objects.count()}")
print(f"✓ Corporate discounts created: {CorporateDiscount.objects.count()}")

print("\n" + "="*80)
print("TEST DATA SEEDING COMPLETE")
print("="*80)

print("\n✅ Test data ready for QA verification!")
print("\nLogins for testing:")
print("  User 1 (email-verified only):")
print("    - Username: qa_email_verified")
print("    - Email: qa_email_verified@test.com")
print("    - Password: TestPassword123!")
print("\n  User 2 (both verified):")
print("    - Username: qa_both_verified")
print("    - Email: qa_both_verified@test.com")
print("    - Password: TestPassword123!")
