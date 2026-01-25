"""
COMPREHENSIVE SEED SCRIPT - ALL DATA REQUIRED FOR GOEXPLORER
Creates: Users, Hotels, Rooms, Meal Plans, Images, Availability, Buses, Routes, Schedules
"""
import os
import django
from decimal import Decimal
from datetime import datetime, timedelta
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from hotels.models import (
    City, Hotel, RoomType, MealPlan, RoomMealPlan, 
    RoomAvailability, HotelImage, RoomImage
)
from buses.models import Bus, BusRoute, BusSchedule, BusOperator
from property_owners.models import PropertyOwner, UserRole
from core.models import CorporateAccount

User = get_user_model()

def create_users():
    """Create all required users"""
    print("\n📝 Creating users...")
    
    # Admin
    admin, _ = User.objects.get_or_create(
        username='admin',
        email='admin@goexplorer.com',
        defaults={
            'is_staff': True,
            'is_superuser': True,
            'email_verified': True,
            'email_verified_at': timezone.now(),
            'phone': '9999999999'
        }
    )
    if _:
        admin.set_password('admin123')
        admin.save()
        print("  ✓ Admin user created")
    
    # Normal user
    user, _ = User.objects.get_or_create(
        username='testuser@test.com',
        email='testuser@test.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '9876543210',
            'email_verified': True,
            'email_verified_at': timezone.now()
        }
    )
    if _:
        user.set_password('test123')
        user.save()
        print("  ✓ Normal user created")
    
    # Property owner
    owner_user, _ = User.objects.get_or_create(
        username='owner@goexplorer.com',
        email='owner@goexplorer.com',
        defaults={
            'first_name': 'Property',
            'last_name': 'Owner',
            'phone': '9876543211',
            'email_verified': True,
            'email_verified_at': timezone.now()
        }
    )
    if _:
        owner_user.set_password('owner123')
        owner_user.save()
        print("  ✓ Property owner user created")
    
    # Create owner role and profile
    UserRole.objects.get_or_create(
        user=owner_user,
        defaults={'role': 'property_owner'}
    )
    
    bangalore = City.objects.filter(name__icontains='Bangalore').first()
    if not bangalore:
        bangalore = City.objects.create(name='Bangalore', state='Karnataka')
    
    PropertyOwner.objects.get_or_create(
        user=owner_user,
        defaults={
            'business_name': 'Premium Hotels Group',
            'owner_name': owner_user.get_full_name(),
            'owner_phone': owner_user.phone,
            'owner_email': owner_user.email,
            'city': bangalore,
            'address': '123 MG Road, Bangalore',
            'pincode': '560001',
            'description': 'Premium hotel chain',
            'verification_status': 'approved'
        }
    )
    print("  ✓ Property owner profile created")
    
    # Corporate user
    corp_user, _ = User.objects.get_or_create(
        username='corporate@company.com',
        email='corporate@company.com',
        defaults={
            'first_name': 'Corporate',
            'last_name': 'Account',
            'phone': '9876543212',
            'email_verified': True,
            'email_verified_at': timezone.now()
        }
    )
    if _:
        corp_user.set_password('corp123')
        corp_user.save()
        print("  ✓ Corporate user created")
    
    CorporateAccount.objects.get_or_create(
        email_domain='company.com',
        defaults={
            'company_name': 'TechCorp India',
            'gst_number': 'GST123456789',
            'contact_person_name': corp_user.get_full_name(),
            'contact_email': corp_user.email,
            'contact_phone': corp_user.phone,
            'admin_user': corp_user,
            'account_type': 'business',
            'status': 'approved'
        }
    )
    print("  ✓ Corporate account created")
    
    # Bus operator
    operator_user, _ = User.objects.get_or_create(
        username='operator@buses.com',
        email='operator@buses.com',
        defaults={
            'first_name': 'Bus',
            'last_name': 'Operator',
            'phone': '9876543213',
            'email_verified': True,
            'email_verified_at': timezone.now()
        }
    )
    if _:
        operator_user.set_password('operator123')
        operator_user.save()
        print("  ✓ Bus operator user created")
    
    UserRole.objects.get_or_create(
        user=operator_user,
        defaults={'role': 'bus_operator'}
    )
    
    BusOperator.objects.get_or_create(
        user=operator_user,
        defaults={
            'name': 'FastTrack Travels',
            'contact_phone': operator_user.phone,
            'contact_email': operator_user.email,
            'verification_status': 'verified',
            'company_legal_name': 'FastTrack Travels Pvt Ltd',
            'operator_office_address': 'Transport Nagar, Bangalore'
        }
    )
    print("  ✓ Bus operator profile created")
    
    return {
        'admin': admin,
        'user': user,
        'owner': owner_user,
        'corporate': corp_user,
        'operator': operator_user
    }


def create_cities():
    """Create cities"""
    print("\n🌆 Creating cities...")
    cities = {}
    city_data = [
        ('Bangalore', 'Karnataka'),
        ('Hyderabad', 'Telangana'),
        ('Mumbai', 'Maharashtra'),
        ('Delhi', 'Delhi'),
        ('Chennai', 'Tamil Nadu')
    ]
    
    for name, state in city_data:
        city, _ = City.objects.get_or_create(
            name=name,
            defaults={'state': state}
        )
        cities[name] = city
        if _:
            print(f"  ✓ Created {name}")
    
    return cities


def create_meal_plans():
    """Create global meal plans"""
    print("\n🍽️ Creating meal plans...")
    
    meal_plans = {}
    plans = [
        ('room_only', 'Room Only', 'Basic room accommodation'),
        ('breakfast', 'Breakfast Included', 'Room + Daily Breakfast'),
        ('half_board', 'Half Board', 'Room + Breakfast + Dinner'),
        ('full_board', 'Full Board', 'Room + All Meals')
    ]
    
    for plan_type, name, desc in plans:
        mp, created = MealPlan.objects.get_or_create(
            name=name,
            defaults={
                'plan_type': plan_type,
                'description': desc,
                'inclusions': [desc]
            }
        )
        meal_plans[plan_type.upper()] = mp
        if created:
            print(f"  ✓ Created {name}")
    
    return meal_plans


def create_hotels_complete(cities, meal_plans):
    """Create hotels with rooms, images, meal plans, and availability"""
    print("\n🏨 Creating hotels with complete data...")
    
    bangalore = cities['Bangalore']
    hyderabad = cities['Hyderabad']
    
    hotels_data = [
        {
            'name': 'Taj Mahal Palace',
            'city': bangalore,
            'star_rating': 5,
            'room_base_price': 8000,
            'description': 'Luxury heritage hotel with premium amenities',
            'has_wifi': True,
            'has_parking': True,
            'has_pool': True,
            'has_gym': True,
            'has_restaurant': True
        },
        {
            'name': 'The Oberoi',
            'city': bangalore,
            'star_rating': 5,
            'room_base_price': 9000,
            'description': 'Contemporary luxury with spa and fine dining',
            'has_wifi': True,
            'has_parking': True,
            'has_pool': True,
            'has_gym': True,
            'has_spa': True,
            'has_restaurant': True
        },
        {
            'name': 'ITC Windsor',
            'city': bangalore,
            'star_rating': 5,
            'room_base_price': 7500,
            'description': 'Colonial charm meets modern luxury',
            'has_wifi': True,
            'has_parking': True,
            'has_gym': True,
            'has_restaurant': True
        },
        {
            'name': 'Taj Falaknuma Palace',
            'city': hyderabad,
            'star_rating': 5,
            'room_base_price': 12000,
            'description': 'Historic palace hotel with royal experience',
            'has_wifi': True,
            'has_parking': True,
            'has_pool': True,
            'has_gym': True,
            'has_spa': True,
            'has_restaurant': True
        }
    ]
    
    created_hotels = []
    
    for hotel_data in hotels_data:
        city = hotel_data.pop('city')
        room_base_price = hotel_data.pop('room_base_price')
        hotel, created = Hotel.objects.get_or_create(
            name=hotel_data['name'],
            city=city,
            defaults={
                **hotel_data,
                'address': f"Sample Address, {city.name}",
                'property_type': 'hotel',
                'is_active': True,
                'review_rating': Decimal('4.5'),
                'review_count': 150,
                'contact_phone': '+91-9876543210',
                'contact_email': 'info@goexplorer.com'
            }
        )
        
        if created:
            print(f"  ✓ Created hotel: {hotel.name}")
            
            # Create rooms for this hotel
            room_types = [
                {
                    'name': 'Standard Room',
                    'base_price': room_base_price,
                    'max_adults': 2,
                    'room_type': 'standard',
                    'bed_type': 'queen',
                    'room_size': 280
                },
                {
                    'name': 'Deluxe Room',
                    'base_price': room_base_price + 2000,
                    'max_adults': 2,
                    'room_type': 'deluxe',
                    'bed_type': 'king',
                    'room_size': 350,
                    'has_balcony': True
                },
                {
                    'name': 'Executive Suite',
                    'base_price': room_base_price + 4000,
                    'max_adults': 3,
                    'room_type': 'suite',
                    'bed_type': 'king',
                    'room_size': 500,
                    'has_balcony': True,
                    'has_minibar': True
                },
                {
                    'name': 'Presidential Suite',
                    'base_price': room_base_price + 8000,
                    'max_adults': 4,
                    'room_type': 'suite',
                    'bed_type': 'king',
                    'room_size': 800,
                    'has_balcony': True,
                    'has_minibar': True,
                    'has_safe': True
                }
            ]
            
            for room_data in room_types:
                room = RoomType.objects.create(
                    hotel=hotel,
                    is_available=True,
                    total_rooms=10,
                    **room_data
                )
                
                # Attach meal plans to room
                RoomMealPlan.objects.create(
                    room_type=room,
                    meal_plan=meal_plans['ROOM_ONLY'],
                    price_delta=0,
                    is_default=True
                )
                RoomMealPlan.objects.create(
                    room_type=room,
                    meal_plan=meal_plans['BREAKFAST'],
                    price_delta=500,
                    is_default=False
                )
                RoomMealPlan.objects.create(
                    room_type=room,
                    meal_plan=meal_plans['HALF_BOARD'],
                    price_delta=1200,
                    is_default=False
                )
                
                # Create availability for next 60 days
                today = timezone.now().date()
                for i in range(60):
                    date = today + timedelta(days=i)
                    RoomAvailability.objects.create(
                        room_type=room,
                        date=date,
                        available_rooms=10,
                        price=room.base_price
                    )
            
            print(f"    ✓ Created 4 room types with meal plans and 60 days availability")
        
        created_hotels.append(hotel)
    
    return created_hotels


def create_buses_complete(cities):
    """Create buses with routes and schedules"""
    print("\n🚌 Creating buses with routes and schedules...")
    
    operator = BusOperator.objects.first()
    if not operator:
        print("  ⚠️ No operator found, skipping buses")
        return []
    
    bangalore = cities['Bangalore']
    hyderabad = cities['Hyderabad']
    
    # Create buses
    bus_types = [
        {'bus_name': 'Volvo AC Sleeper', 'type': 'sleeper', 'total_seats': 40},
        {'bus_name': 'Mercedes Multi-Axle', 'type': 'seater', 'total_seats': 50},
        {'bus_name': 'Scania AC Seater', 'type': 'seater', 'total_seats': 45}
    ]
    
    buses = []
    for bus_data in bus_types:
        bus, created = Bus.objects.get_or_create(
            bus_name=bus_data['bus_name'],
            operator=operator,
            defaults={
                'bus_number': f"KA-{bus_types.index(bus_data)+1:02d}-{1000+bus_types.index(bus_data)}",
                'bus_type': bus_data['type'],
                'total_seats': bus_data['total_seats'],
                'is_active': True,
                'has_ac': True,
                'has_wifi': True,
                'has_charging_point': True,
                'has_water_bottle': True
            }
        )
        buses.append(bus)
        if created:
            print(f"  ✓ Created bus: {bus.bus_name}")
    
    # Create BLR-HYD route
    route, _ = BusRoute.objects.get_or_create(
        source_city=bangalore,
        destination_city=hyderabad,
        defaults={
            'distance_km': 570,
            'estimated_duration': timedelta(hours=10),
            'base_fare': Decimal('800')
        }
    )
    
    if _:
        print(f"  ✓ Created route: {route}")
        
        # Create schedules for next 30 days
        today = timezone.now().date()
        departure_times = ['21:00:00', '22:00:00', '23:00:00']
        
        for bus in buses:
            for time_str in departure_times:
                for day_offset in range(30):
                    travel_date = today + timedelta(days=day_offset)
                    
                    BusSchedule.objects.get_or_create(
                        bus=bus,
                        route=route,
                        departure_time=time_str,
                        travel_date=travel_date,
                        defaults={
                            'available_seats': bus.total_seats,
                            'price_per_seat': route.base_fare,
                            'is_active': True
                        }
                    )
        
        print(f"    ✓ Created schedules for 3 buses x 3 times x 30 days = 270 schedules")
    
    return buses


def ensure_all_rooms_have_meal_plans(meal_plans):
    """CRITICAL: Ensure every room has at least one default meal plan"""
    print("\n🔧 ENSURING ALL ROOMS HAVE MEAL PLANS...")
    
    rooms_without_plans = []
    for room in RoomType.objects.all():
        if not room.meal_plans.exists():
            rooms_without_plans.append(room)
    
    if rooms_without_plans:
        print(f"  ⚠️  Found {len(rooms_without_plans)} rooms without meal plans - fixing...")
        for room in rooms_without_plans:
            # Add Room Only as default
            RoomMealPlan.objects.create(
                room_type=room,
                meal_plan=meal_plans['ROOM_ONLY'],
                price_delta=0,
                is_default=True
            )
            # Add Breakfast as option
            RoomMealPlan.objects.create(
                room_type=room,
                meal_plan=meal_plans['BREAKFAST'],
                price_delta=500,
                is_default=False
            )
            # Add Half Board as option
            RoomMealPlan.objects.create(
                room_type=room,
                meal_plan=meal_plans['HALF_BOARD'],
                price_delta=1200,
                is_default=False
            )
        print(f"  ✓ Fixed {len(rooms_without_plans)} rooms with meal plans")
    else:
        print("  ✓ All rooms already have meal plans")
    
    # Verify every room has exactly ONE default meal plan
    rooms_fixed = 0
    for room in RoomType.objects.all():
        defaults = room.meal_plans.filter(is_default=True)
        if defaults.count() == 0:
            # No default - make ROOM_ONLY default
            room_only_plan = meal_plans['ROOM_ONLY']
            rmp, _ = RoomMealPlan.objects.get_or_create(
                room_type=room,
                meal_plan=room_only_plan,
                defaults={'price_delta': 0, 'is_default': True}
            )
            if not rmp.is_default:
                rmp.is_default = True
                rmp.save()
            rooms_fixed += 1
        elif defaults.count() > 1:
            # Multiple defaults - keep only first one
            for idx, rmp in enumerate(defaults):
                if idx > 0:
                    rmp.is_default = False
                    rmp.save()
            rooms_fixed += 1
    
    if rooms_fixed > 0:
        print(f"  ✓ Fixed {rooms_fixed} rooms to have exactly 1 default meal plan")
    
    return True


def verify_seed_data():
    """Verify all seed data exists"""
    print("\n✅ VERIFYING SEED DATA...")
    
    checks = {
        'Users': User.objects.count(),
        'Cities': City.objects.count(),
        'Hotels': Hotel.objects.count(),
        'Room Types': RoomType.objects.count(),
        'Meal Plans': MealPlan.objects.count(),
        'Room-Meal Links': RoomMealPlan.objects.count(),
        'Availability Records': RoomAvailability.objects.count(),
        'Buses': Bus.objects.count(),
        'Bus Routes': BusRoute.objects.count(),
        'Bus Schedules': BusSchedule.objects.count(),
        'Property Owners': PropertyOwner.objects.count(),
        'Corporate Accounts': CorporateAccount.objects.count()
    }
    
    all_good = True
    for name, count in checks.items():
        status = "✓" if count > 0 else "❌"
        print(f"  {status} {name}: {count}")
        if count == 0:
            all_good = False
    
    # Verify meal plan defaults
    default_meals = RoomMealPlan.objects.filter(is_default=True).count()
    total_rooms = RoomType.objects.count()
    print(f"\n  Default meal plans: {default_meals} (should equal rooms: {total_rooms})")
    
    if default_meals != total_rooms:
        print("  ❌ CRITICAL: Not all rooms have default meal plans!")
        all_good = False
    else:
        print("  ✅ All rooms have exactly 1 default meal plan")
    
    return all_good


def main():
    print("="*60)
    print("🚀 COMPREHENSIVE SEED SCRIPT - GOEXPLORER")
    print("="*60)
    
    users = create_users()
    cities = create_cities()
    meal_plans = create_meal_plans()
    hotels = create_hotels_complete(cities, meal_plans)
    buses = create_buses_complete(cities)
    
    # CRITICAL: Ensure ALL rooms (including pre-existing) have meal plans
    ensure_all_rooms_have_meal_plans(meal_plans)
    
    success = verify_seed_data()
    
    print("\n" + "="*60)
    if success:
        print("✅ SEED COMPLETE - ALL DATA VERIFIED")
    else:
        print("❌ SEED FAILED - CRITICAL DATA MISSING")
    print("="*60)
    
    print("\n📝 Login Credentials:")
    print("  Admin: admin@goexplorer.com / admin123")
    print("  User: testuser@test.com / test123")
    print("  Owner: owner@goexplorer.com / owner123")
    print("  Corporate: corporate@company.com / corp123")
    print("  Operator: operator@buses.com / operator123")


if __name__ == '__main__':
    main()
