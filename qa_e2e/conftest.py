import pytest
from playwright.sync_api import Page, expect
import os
import django
import subprocess
import time
import signal
import requests
from pathlib import Path
import atexit
import sys
from datetime import date, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

# Import Django models AFTER setup
from django.utils import timezone
from django.contrib.auth import get_user_model
from hotels.models import Hotel, RoomType, RoomMealPlan, RoomCancellationPolicy
from core.models import City
from bookings.models import Booking, HotelBooking, BusBooking
from buses.models import BusOperator, BusRoute, BusSchedule, Bus

User = get_user_model()

# Global server process
_SERVER_PROCESS = None
_SERVER_PID = None

def _start_django_server():
    """Start Django development server on 0.0.0.0:8000"""
    global _SERVER_PROCESS, _SERVER_PID
    
    # Check if already running
    try:
        response = requests.get('http://127.0.0.1:8000/', timeout=2)
        print("[OK] Django server already running on 127.0.0.1:8000")
        return
    except:
        pass
    
    print("[*] Starting Django development server...")
    
    # Start server on 0.0.0.0:8000 with noreload
    _SERVER_PROCESS = subprocess.Popen(
        [
            ".venv-1/Scripts/python.exe",
            "manage.py",
            "runserver",
            "0.0.0.0:8000",
            "--noreload",
            "--nothreading"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd(),
        preexec_fn=None  # Windows doesn't support preexec_fn
    )
    _SERVER_PID = _SERVER_PROCESS.pid
    
    # Wait for server to be reachable
    print("[*] Waiting for server to become reachable...")
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            resp = requests.get("http://127.0.0.1:8000/", timeout=2)
            if resp.status_code in [200, 404, 302]:
                print("[OK] Django server is reachable!")
                return
        except:
            if attempt == max_attempts - 1:
                print("[ERROR] Server failed to start after 30 seconds")
                _SERVER_PROCESS.kill()
                raise RuntimeError("Django server unreachable")
            time.sleep(1)


def _stop_django_server():
    """Stop Django development server"""
    global _SERVER_PROCESS, _SERVER_PID
    
    if _SERVER_PROCESS:
        try:
            _SERVER_PROCESS.terminate()
            _SERVER_PROCESS.wait(timeout=5)
            print(f"[OK] Django server stopped (PID: {_SERVER_PID})")
        except:
            try:
                _SERVER_PROCESS.kill()
            except:
                pass
    
    _SERVER_PROCESS = None
    _SERVER_PID = None


# Register cleanup
atexit.register(_stop_django_server)


@pytest.fixture(scope="session", autouse=True)
def django_server():
    """Start/stop Django server for the test session"""
    _start_django_server()
    yield
    _stop_django_server()

@pytest.fixture(scope="session")
def seed_data():
    """Create test data for all test scenarios"""
    print("\n[*] Seeding test data...")
    
    # Run migrations first
    os.system("python manage.py migrate --noinput 2>/dev/null")
    
    # Use timestamp to ensure unique names each run
    import time
    timestamp = str(int(time.time()))
    
    # Clean up: Get or create a unique test city
    city, _ = City.objects.get_or_create(
        code="QTC",
        defaults={
            "name": "QA Test City",
            "state": "Test State",
            "country": "India"
        }
    )
    
    # 1. Hotel with rooms + meal plans
    hotel_with_meals = Hotel.objects.create(
        name=f"QA Hotel Meals {timestamp}",
        description="Test hotel with rooms and meal plans",
        city=city,
        address="Test Address 1",
        latitude=19.0760,
        longitude=72.8777,
        is_active=True,
        property_type="hotel",
        star_rating=4,
        cancellation_policy="Non-refundable after 48 hours",
        cancellation_type="X_DAYS_BEFORE",
        cancellation_days=2
    )
    
    room_type_1 = RoomType.objects.create(
        hotel=hotel_with_meals,
        name="Deluxe Room",
        room_type="deluxe",
        description="Spacious deluxe room with amenities",
        base_price=2000.00,
        max_occupancy=2
    )
    
    meal_plan_1 = RoomMealPlan.objects.create(
        hotel=hotel_with_meals,
        meal_plan_type="breakfast",
        price=500.00
    )
    
    # 2. Hotel with rooms but NO meal plans
    hotel_no_meals = Hotel.objects.create(
        name=f"QA Hotel NoMeals {timestamp}",
        description="Test hotel with rooms but no meal plans",
        city=city,
        address="Test Address 2",
        latitude=19.0800,
        longitude=72.8850,
        is_active=True,
        property_type="hotel",
        star_rating=3,
        cancellation_policy="Free cancellation till 24 hours",
        cancellation_type="X_DAYS_BEFORE",
        cancellation_days=1
    )
    
    room_type_2 = RoomType.objects.create(
        hotel=hotel_no_meals,
        name="Standard Room",
        room_type="standard",
        description="Standard room",
        base_price=1500.00,
        max_occupancy=1
    )
    
    # 3. Hotel with ZERO rooms
    hotel_zero_rooms = Hotel.objects.create(
        name=f"QA Hotel ZeroRooms {timestamp}",
        description="Test hotel with no rooms",
        city=city,
        address="Test Address 3",
        latitude=19.0750,
        longitude=72.8700,
        is_active=True,
        property_type="hotel",
        star_rating=2,
        cancellation_policy="No cancellation",
        cancellation_type="NO_CANCELLATION"
    )
    
    # 4. Hotel with NO images
    hotel_no_images = Hotel.objects.create(
        name=f"QA Hotel NoImages {timestamp}",
        description="Test hotel with no images",
        city=city,
        address="Test Address 4",
        latitude=19.0900,
        longitude=72.8900,
        is_active=True,
        property_type="hotel",
        star_rating=3,
        cancellation_policy="Cancellation with fee",
        cancellation_type="NO_CANCELLATION"
    )
    
    room_type_4 = RoomType.objects.create(
        hotel=hotel_no_images,
        name="Deluxe Room",
        room_type="deluxe",
        description="Deluxe room",
        base_price=1200.00,
        max_occupancy=2
    )
    
    # 5. Hotel booking (for confirmation/payment tests)
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    booking_hotel = Booking.objects.create(
        customer_name="QA Test Guest",
        customer_email=f"qa-{timestamp}@example.com",
        customer_phone="9876543210",
        booking_type='hotel',
        status='payment_pending',
        total_amount=2000.00
    )
    
    hotel_booking = HotelBooking.objects.create(
        booking=booking_hotel,
        hotel=hotel_with_meals,
        room_type=room_type_1,
        meal_plan=meal_plan_1,
        check_in=today,
        check_out=tomorrow,
        number_of_rooms=1,
        total_nights=1,
        room_base_price=1800.00,
        room_discounted_price=1800.00
    )
    
    # 6. Bus booking (for bus integrity tests)
    # Create bus operator
    bus_operator = BusOperator.objects.create(
        name=f"QA Bus Operator {timestamp}",
        contact_email=f"busop-{timestamp}@example.com",
        contact_phone="9123456789",
        is_active=True,
        is_verified=True
    )
    
    # Create bus route
    bus_route = BusRoute.objects.create(
        operator=bus_operator,
        origin_city=city,
        destination_city=city,
        distance_km=100
    )
    
    # Create bus
    bus = Bus.objects.create(
        operator=bus_operator,
        bus_name=f"QA Bus {timestamp}",
        bus_number=f"QA{timestamp}",
        capacity=40,
        bus_type="AC Sleeper",
        total_seats=40
    )
    
    # Create bus schedule
    bus_schedule = BusSchedule.objects.create(
        route=bus_route,
        bus=bus,
        departure_date=today,
        departure_time="10:00",
        arrival_time="14:00",
        price_per_seat=500.00,
        available_seats=40
    )
    
    # Create bus booking
    bus_booking_obj = Booking.objects.create(
        customer_name="QA Bus Passenger",
        customer_email=f"buspass-{timestamp}@example.com",
        customer_phone="9876543210",
        booking_type='bus',
        status='confirmed',
        total_amount=1000.00
    )
    
    bus_booking = BusBooking.objects.create(
        booking=bus_booking_obj,
        schedule=bus_schedule,
        seat_numbers="A1,A2",
        boarding_point="Test Station",
        dropping_point="Test Destination"
    )
    
    print("[OK] Test data seeded successfully")
    
    return {
        'hotel_with_meals': hotel_with_meals,
        'hotel_no_meals': hotel_no_meals,
        'hotel_zero_rooms': hotel_zero_rooms,
        'hotel_no_images': hotel_no_images,
        'hotel_booking': hotel_booking,
        'bus_booking': bus_booking,
        'room_type_1': room_type_1,
        'meal_plan_1': meal_plan_1,
    }



@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application"""
    return "http://127.0.0.1:8000"


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args):
    """Configure browser context with screenshot/video capture"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "record_video_dir": "test-results/videos/",
    }


@pytest.fixture(scope="function")
def context(context):
    """Yield context and capture screenshot on failure"""
    yield context
    context.close()
