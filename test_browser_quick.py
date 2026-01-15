#!/usr/bin/env python
"""
Quick browser test - wallet and other critical issues
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from users.models import User
from datetime import datetime

client = Client()

print("\n" + "=" * 80)
print("QUICK BROWSER FUNCTIONALITY TEST")
print("=" * 80)

# Create or get test user
user, created = User.objects.get_or_create(
    username='browser_test@test.com',
    defaults={
        'email': 'browser_test@test.com',
        'first_name': 'Browser',
        'last_name': 'Test',
        'phone': '9876543210'
    }
)

if created or not user.has_usable_password():
    user.set_password('TestPass123')
    user.save()

if not user.email_verified_at:
    from django.utils import timezone
    user.email_verified_at = timezone.now()
    user.save()

# Re-get user to ensure fresh state
user = User.objects.get(pk=user.pk)

# Test 1: Wallet page accessibility
print("\n[TEST 1] Wallet Page")
login_result = client.login(username='browser_test@test.com', password='TestPass123')
print(f"  Login result: {login_result}")
response = client.get('/payments/wallet/')
print(f"  URL: /payments/wallet/")
print(f"  Status: HTTP {response.status_code}")

if response.status_code == 200:
    has_balance = b'Available Balance' in response.content or b'balance' in response.content.lower()
    has_transactions = b'Transaction History' in response.content or b'transactions' in response.content.lower()
    print(f"  Shows Balance Section: {'YES' if has_balance else 'NO'}")
    print(f"  Shows Transactions Section: {'YES' if has_transactions else 'NO'}")
    print(f"  Result: PASS" if has_balance and has_transactions else f"  Result: PARTIAL")
elif response.status_code == 302:
    print(f"  Redirecting to: {response.url}")
    print(f"  Result: NEEDS LOGIN REDIRECT")
else:
    print(f"  Result: FAIL - {response.status_code}")

# Test 2: Hotel placeholder image
print("\n[TEST 2] Hotel Placeholder SVG")
response = client.get('/static/images/hotel_placeholder.svg')
print(f"  URL: /static/images/hotel_placeholder.svg")
print(f"  Status: HTTP {response.status_code}")
if response.status_code == 200:
    # Use streaming_content for WhiteNoise served files
    try:
        content = b''.join(response.streaming_content) if hasattr(response, 'streaming_content') else response.content
    except:
        content = response.content
    
    has_unavailable_text = b'unavailable' in content.lower()
    has_svg_content = b'<svg' in content or b'svg' in content.lower()
    print(f"  Contains 'unavailable' text: {'YES (BUG!)' if has_unavailable_text else 'NO (GOOD)'}")
    print(f"  Is valid SVG: {'YES' if has_svg_content else 'NO'}")
    print(f"  Result: PASS" if not has_unavailable_text and has_svg_content else f"  Result: ISSUE")
else:
    print(f"  Result: FILE NOT FOUND - {response.status_code}")

# Test 3: Hotel list page date picker
print("\n[TEST 3] Hotel List Date Picker (Min Date Validation)")
response = client.get('/hotels/')
if response.status_code == 200:
    has_checkin_input = b'name="checkin"' in response.content or b'id="checkin"' in response.content.lower()
    has_date_validation = b'minDate' in response.content or b'new Date()' in response.content.lower() or b'setHours' in response.content
    print(f"  Has check-in input: {'YES' if has_checkin_input else 'NO'}")
    print(f"  Has date validation logic: {'YES' if has_date_validation else 'NO'}")
    print(f"  Result: PASS" if has_date_validation else "  Result: NEEDS CHECKING")
else:
    print(f"  Result: PAGE ERROR - {response.status_code}")

# Test 4: Bus seat layout
print("\n[TEST 4] Bus Seat Layout (No 'AISLE' Text)")
from buses.models import Bus
try:
    bus = Bus.objects.first()
    if bus:
        response = client.get(f'/buses/{bus.id}/')
        if response.status_code == 200:
            has_aisle_text = b'<div class="aisle">AISLE</div>' in response.content
            has_empty_aisle = b'<div class="aisle"></div>' in response.content
            print(f"  Has 'AISLE' text: {'YES (BUG!)' if has_aisle_text else 'NO (GOOD)'}")
            print(f"  Has empty aisle div: {'YES' if has_empty_aisle else 'NO'}")
            print(f"  Result: PASS" if not has_aisle_text else "  Result: FAIL")
        else:
            print(f"  Result: PAGE ERROR - {response.status_code}")
    else:
        print("  No buses in database")
except Exception as e:
    print(f"  Error: {str(e)}")

print("\n" + "=" * 80)
print("TESTS COMPLETE")
print("=" * 80)
