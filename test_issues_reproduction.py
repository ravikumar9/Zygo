#!/usr/bin/env python
"""
ISSUE REPRODUCTION SCRIPT
Systematically reproduces all 8 reported issues before fixing
"""
import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goexplorer.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from hotels.models import Hotel, RoomType, HotelImage
from bookings.models import Booking
from payments.models import Wallet, WalletTransaction
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
import os

User = get_user_model()
client = Client()

print("=" * 80)
print("GOEXPLORER - ISSUE REPRODUCTION TEST SUITE")
print("=" * 80)

# Test user setup
test_user = User.objects.filter(email='test.user@example.com').first()
if not test_user:
    test_user = User.objects.create_user(
        username='testuser',
        email='test.user@example.com',
        password='test123456',
        first_name='Test',
        last_name='User'
    )
    test_user.email_verified_at = timezone.now()
    test_user.save()
    print(f"✓ Created test user: {test_user.email}")
else:
    print(f"✓ Using existing test user: {test_user.email}")

# Ensure test user has wallet
wallet, _ = Wallet.objects.get_or_create(user=test_user)
if wallet.balance < Decimal('10000'):
    wallet.balance = Decimal('10000')
    wallet.save()
    print(f"✓ Wallet balance set to ₹{wallet.balance}")

# Get test hotel and room
hotel = Hotel.objects.first()
if not hotel:
    print("✗ No hotels in database. Cannot proceed with tests.")
    sys.exit(1)

room_type = RoomType.objects.filter(hotel=hotel).first()
if not room_type:
    print("✗ No room types for test hotel. Cannot proceed with tests.")
    sys.exit(1)

print(f"\n✓ Test Hotel: {hotel.name}")
print(f"✓ Test Room Type: {room_type.name}")

# ============================================================================
# ISSUE A: Booking without room selection crashes
# ============================================================================
print("\n" + "=" * 80)
print("ISSUE A: Booking without room selection crashes")
print("=" * 80)

try:
    client.login(email='test.user@example.com', password='test123456')
    print("✓ User logged in")
except Exception as e:
    print(f"✗ Login failed: {e}")

# Try to create booking without room selection
check_in = date.today() + timedelta(days=5)
check_out = check_in + timedelta(days=3)

booking_data = {
    'hotel_id': hotel.id,
    'check_in': check_in.isoformat(),
    'check_out': check_out.isoformat(),
    'number_of_rooms': 1,
    'customer_name': 'Test Guest',
    'customer_email': 'guest@example.com',
    'customer_phone': '+919876543210',
    # NOTE: room_type_id is MISSING
}

print("\nAttempting to book without room selection...")
print(f"Payload: {booking_data}")

try:
    response = client.post('/api/hotel-booking/', booking_data, content_type='application/json')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    if response.status_code == 400:
        print("✓ ISSUE A: Correctly rejected - room selection required")
    elif response.status_code == 500:
        print("✗ ISSUE A: Server crashed with 500 - Field 'id' expected a number but got ''")
except Exception as e:
    print(f"✗ Exception: {e}")

# ============================================================================
# ISSUE B: Wallet payment fails with 500 error
# ============================================================================
print("\n" + "=" * 80)
print("ISSUE B: Wallet payment fails with 500 error")
print("=" * 80)

# First, create a valid booking
print("\nCreating valid booking first...")
booking_data = {
    'hotel_id': hotel.id,
    'room_type_id': room_type.id,
    'check_in': check_in.isoformat(),
    'check_out': check_out.isoformat(),
    'number_of_rooms': 1,
    'customer_name': 'Test Guest',
    'customer_email': 'guest@example.com',
    'customer_phone': '+919876543210',
}

try:
    response = client.post('/api/hotel-booking/', booking_data, content_type='application/json')
    print(f"Booking creation status: {response.status_code}")
    if response.status_code in [200, 201]:
        booking_id = response.json().get('booking_id')
        print(f"✓ Booking created: {booking_id}")
        
        # Now try wallet payment
        print("\nAttempting wallet payment...")
        payment_data = {
            'booking_id': booking_id,
            'amount': '5000',
            'payment_method': 'wallet'
        }
        print(f"Payload: {payment_data}")
        
        response = client.post('/api/wallet-payment/', payment_data, content_type='application/json')
        print(f"Payment status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 500:
            print("✗ ISSUE B: Wallet payment fails with 500 error")
        elif response.status_code == 200:
            print("✓ ISSUE B: Wallet payment successful")
    else:
        print(f"✗ Booking creation failed: {response.json()}")
except Exception as e:
    print(f"✗ Exception: {e}")

# ============================================================================
# ISSUE C: Wallet balance not deducted after confirmation
# ============================================================================
print("\n" + "=" * 80)
print("ISSUE C: Wallet balance not deducted after confirmation")
print("=" * 80)

wallet.refresh_from_db()
initial_balance = wallet.balance
print(f"Wallet balance before booking: ₹{initial_balance}")

# Create new booking and pay
booking_data = {
    'hotel_id': hotel.id,
    'room_type_id': room_type.id,
    'check_in': (check_in + timedelta(days=10)).isoformat(),
    'check_out': (check_in + timedelta(days=13)).isoformat(),
    'number_of_rooms': 1,
    'customer_name': 'Test Guest',
    'customer_email': 'guest@example.com',
    'customer_phone': '+919876543210',
}

try:
    response = client.post('/api/hotel-booking/', booking_data, content_type='application/json')
    if response.status_code in [200, 201]:
        booking_id = response.json().get('booking_id')
        payment_data = {
            'booking_id': booking_id,
            'amount': '3000',
            'payment_method': 'wallet'
        }
        
        response = client.post('/api/wallet-payment/', payment_data, content_type='application/json')
        
        wallet.refresh_from_db()
        final_balance = wallet.balance
        
        print(f"Wallet balance after payment: ₹{final_balance}")
        print(f"Balance change: ₹{initial_balance - final_balance}")
        
        if final_balance == initial_balance:
            print("✗ ISSUE C: Wallet balance NOT deducted")
        else:
            print("✓ ISSUE C: Wallet balance correctly deducted")
except Exception as e:
    print(f"✗ Exception: {e}")

# ============================================================================
# ISSUE D: Login success message appearing on booking/payment pages
# ============================================================================
print("\n" + "=" * 80)
print("ISSUE D: Login success message appearing on booking/payment pages")
print("=" * 80)

client.logout()
try:
    response = client.post('/accounts/login/', {
        'email': 'test.user@example.com',
        'password': 'test123456'
    })
    print(f"Login response status: {response.status_code}")
    
    # Check for success message in session/cookies
    if 'messages' in client.session:
        messages = client.session['messages']
        print(f"Messages in session: {messages}")
        for msg in messages:
            if 'success' in str(msg).lower() or 'logged' in str(msg).lower():
                print(f"✗ ISSUE D: Auth success message detected: {msg}")
            
except Exception as e:
    print(f"Exception: {e}")

# Now navigate to booking page and check for messages
try:
    client.login(email='test.user@example.com', password='test123456')
    booking = Booking.objects.filter(user=test_user).first()
    if booking:
        response = client.get(f'/bookings/{booking.booking_id}/confirm/')
        print(f"Booking confirmation page status: {response.status_code}")
        
        if b'Login successful' in response.content or b'logged in' in response.content.lower():
            print("✗ ISSUE D: Auth message appearing on booking page")
        else:
            print("✓ ISSUE D: No auth messages on booking page")
except Exception as e:
    print(f"Exception: {e}")

# ============================================================================
# ISSUE E: Proceed to Payment enabled with missing mandatory fields
# ============================================================================
print("\n" + "=" * 80)
print("ISSUE E: Proceed to Payment enabled with missing mandatory fields")
print("=" * 80)

# This would require browser testing - checking if button is disabled in HTML
print("Manual verification needed: Check booking confirmation page")
print("Button should be disabled if ANY of these are missing:")
print("  - Room selected")
print("  - Guest name")
print("  - Email")
print("  - Phone")
print("  - Check-in/Check-out dates")

# ============================================================================
# ISSUE F: Back button loses booking state
# ============================================================================
print("\n" + "=" * 80)
print("ISSUE F: Back button loses booking state (hotel/bus/package)")
print("=" * 80)

print("Manual verification needed: Browser back button test")
print("Expected: Hotel/Bus/Package selection preserved")
print("Current: Likely lost due to no session state")

# ============================================================================
# ISSUE G: Hotel images showing placeholders
# ============================================================================
print("\n" + "=" * 80)
print("ISSUE G: Hotel images showing placeholders despite files existing")
print("=" * 80)

hotel_images = HotelImage.objects.filter(hotel=hotel)
print(f"Hotel images count: {hotel_images.count()}")

if hotel_images.exists():
    img = hotel_images.first()
    print(f"First image URL: {img.image.url}")
    print(f"First image path: {img.image.path if hasattr(img.image, 'path') else 'N/A'}")
    
    # Check if file exists
    if hasattr(img.image, 'path'):
        if os.path.exists(img.image.path):
            print(f"✓ Image file exists on disk")
        else:
            print(f"✗ Image file MISSING from disk: {img.image.path}")
else:
    print("✗ No hotel images found")

# ============================================================================
# ISSUE H: Inventory not reliably reserved/released
# ============================================================================
print("\n" + "=" * 80)
print("ISSUE H: Inventory not reliably reserved/released")
print("=" * 80)

print("Checking booking inventory state...")
booking = Booking.objects.filter(user=test_user, status='confirmed').first()

if booking:
    if booking.booking_type == 'hotel':
        try:
            hotel_details = booking.hotel_details
            if hotel_details:
                print(f"Booking ID: {booking.booking_id}")
                print(f"Status: {booking.status}")
                print(f"Rooms: {hotel_details.number_of_rooms}")
                # Check CM booking ID (indicates inventory was reserved)
                if booking.cm_booking_id:
                    print(f"✓ CM Booking ID set: {booking.cm_booking_id} (inventory reserved)")
                else:
                    print(f"✗ CM Booking ID NOT set (inventory may not be reserved)")
        except Exception as e:
            print(f"Exception: {e}")
else:
    print("No confirmed bookings to check inventory")

print("\n" + "=" * 80)
print("REPRODUCTION TEST SUITE COMPLETE")
print("=" * 80)
