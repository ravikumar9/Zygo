#!/usr/bin/env python
"""
Playwright UI E2E Test Runner
Prepares Django backend, creates test users, and executes comprehensive Playwright tests
"""
import os
import sys
import django
import subprocess
import time
import requests
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from users.models import User
from hotels.models import Hotel, RoomType, MealPlan, RoomMealPlan, HotelImage, RoomImage
from payments.models import Wallet
from bookings.models import Booking
from core.models import City

def wait_for_server(url, timeout=30, retries=10):
    """Wait for Django server to be ready"""
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code in [200, 302, 404]:
                print(f"[+] Server is ready at {url}")
                return True
        except requests.exceptions.ConnectionError:
            print(f"[*] Waiting for server... (attempt {attempt+1}/{retries})")
            time.sleep(3)
    raise Exception(f"[-] Server did not start within {timeout*retries} seconds")

def create_test_users():
    """Create test users for E2E testing"""
    print("\n[*] Creating test users...")
    
    # Create/update admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@test.com',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("[+] Admin user created")
    else:
        print("[+] Admin user exists")

    # Create/update test customer user
    customer_user, created = User.objects.get_or_create(
        username='customer',
        defaults={
            'email': 'customer@test.com',
        }
    )
    if created:
        customer_user.set_password('customer123')
        customer_user.save()
        print("[+] Customer user created")
    else:
        print("[+] Customer user exists")
    
    # Ensure wallet exists for customer
    wallet, created = Wallet.objects.get_or_create(
        user=customer_user,
        defaults={'balance': 50000}  # 50,000 for testing
    )
    if created:
        print(f"[+] Wallet created for customer with 50000")
    else:
        wallet.balance = 50000
        wallet.save()
        print(f"[+] Wallet updated for customer with 50000")

def create_test_data():
    """Create hotel and room test data"""
    print("\n[*] Creating hotel test data...")
    
    # Get or create cities
    agra_city, _ = City.objects.get_or_create(name='Agra')
    delhi_city, _ = City.objects.get_or_create(name='Delhi')
    
    # Get or create hotels
    hotel = Hotel.objects.filter(name='Taj Mahal Palace').first()
    if not hotel:
        hotel = Hotel.objects.create(
            name='Taj Mahal Palace',
            city=agra_city,
            description='Iconic hotel with stunning views',
            policies='No smoking policy',
            rules='Check-in after 2pm',
            amenities='WiFi, AC, Restaurant'
        )
        print(f"[+] Hotel 'Taj Mahal Palace' created")
    else:
        print(f"[+] Hotel 'Taj Mahal Palace' exists")

    # Ensure meal plans exist
    meal_plans = ['room_only', 'breakfast', 'half_board', 'full_board']
    for plan_type in meal_plans:
        if not MealPlan.objects.filter(plan_type=plan_type).exists():
            name_map = {
                'room_only': 'Room Only',
                'breakfast': 'Breakfast Included',
                'half_board': 'Half Board',
                'full_board': 'Full Board',
            }
            MealPlan.objects.create(name=name_map[plan_type], plan_type=plan_type)

    # Create room type
    if not RoomType.objects.filter(hotel=hotel, name='Standard').exists():
        room_type = RoomType.objects.create(
            hotel=hotel,
            name='Standard',
            base_price=6000,  # Budget tier (0% GST)
            total_rooms=30
        )
        
        # Attach meal plans
        for plan_type in meal_plans:
            plan = MealPlan.objects.get(plan_type=plan_type)
            price_delta_map = {
                'room_only': 0,
                'breakfast': 500,
                'half_board': 1200,
                'full_board': 2000,
            }
            RoomMealPlan.objects.get_or_create(
                room_type=room_type,
                meal_plan=plan,
                defaults={'price_delta': price_delta_map[plan_type]}
            )
        
        print(f"[+] Room type 'Standard' created")
    else:
        print(f"[+] Room type 'Standard' exists")
    
    # Create Premium hotel
    premium_hotel = Hotel.objects.filter(name='Park Hyatt').first()
    if not premium_hotel:
        premium_hotel = Hotel.objects.create(
            name='Park Hyatt',
            city=delhi_city,
            description='Luxury 5-star hotel',
            policies='Premium cancellation policy',
            rules='Early check-in available',
            amenities='WiFi, AC, Restaurant, Spa, Pool'
        )
        print(f"[+] Hotel 'Park Hyatt' created")
    else:
        print(f"[+] Hotel 'Park Hyatt' exists")

    # Create premium room type
    if not RoomType.objects.filter(hotel=premium_hotel, name='Suite').exists():
        premium_room = RoomType.objects.create(
            hotel=premium_hotel,
            name='Suite',
            base_price=18000,  # Premium tier (5% GST)
            total_rooms=20
        )
        
        # Attach meal plans
        for plan_type in meal_plans:
            plan = MealPlan.objects.get(plan_type=plan_type)
            price_delta_map = {
                'room_only': 0,
                'breakfast': 500,
                'half_board': 1200,
                'full_board': 2000,
            }
            RoomMealPlan.objects.get_or_create(
                room_type=premium_room,
                meal_plan=plan,
                defaults={'price_delta': price_delta_map[plan_type]}
            )
        
        print(f"[+] Room type 'Suite' created")
    else:
        print(f"[+] Room type 'Suite' exists")

def run_playwright_tests():
    """Run Playwright UI E2E tests"""
    print("\n[*] Running Playwright UI E2E tests...")
    print("=" * 60)
    
    # Ensure test-results directory exists
    Path('test-results/videos').mkdir(parents=True, exist_ok=True)
    Path('test-results/html-report').mkdir(parents=True, exist_ok=True)
    
    # Run Playwright tests
    result = subprocess.run(
        ['npx', 'playwright', 'test', '--headed', '--reporter=list'],
        cwd=os.getcwd(),
        capture_output=False
    )
    
    return result.returncode == 0

def main():
    """Main execution flow"""
    print(">>> Goibibo Booking Platform - Playwright UI E2E Test Suite")
    print("=" * 60)
    
    try:
        # Create test data
        create_test_users()
        create_test_data()
        
        # Wait for server
        print("\n[*] Waiting for Django server to start...")
        BASE_URL = 'http://localhost:8000'
        
        try:
            wait_for_server(BASE_URL)
        except Exception as e:
            print(f"[!] {e}")
            print("Server should be running already for this script")
        
        # Run tests
        success = run_playwright_tests()
        
        if success:
            print("\n[+] ALL PLAYWRIGHT UI E2E TESTS PASSED")
            print("\n[*] Artifacts generated:")
            print("   >> Videos: test-results/videos/")
            print("   >> Screenshots: test-results/*.png")
            print("   >> Traces: test-results/trace.zip")
            print("   >> Report: test-results/html-report/index.html")
            sys.exit(0)
        else:
            print("\n[-] SOME TESTS FAILED")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
