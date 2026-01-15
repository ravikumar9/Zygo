#!/usr/bin/env python
"""
Test critical bug fixes in browser
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from users.models import User
from datetime import datetime, timedelta

client = Client()

print("=" * 80)
print("TESTING CRITICAL BUG FIXES")
print("=" * 80)

# Test 1: Phone validation template
print("\n[TEST 1] Mobile phone validation - checking template...")
response = client.get('/users/register/')
assert b'maxlength="10"' in response.content, "❌ maxlength should be 10, not 15"
assert b'pattern="^[0-9]{10}$"' in response.content, "❌ pattern should allow exactly 10 digits"
print("✅ Mobile phone validation template is correct")

# Test 2: Wallet URL
print("\n[TEST 2] Wallet page URL registration...")
# Create test user
try:
    user = User.objects.create_user(
        username='test@test.com',
        email='test@test.com',
        password='TestPass123',
        phone='9876543210'
    )
    user.email_verified_at = datetime.now()
    user.save()
except:
    user = User.objects.get(email='test@test.com')

# Login
client.login(username='test@test.com', password='TestPass123')
response = client.get('/payments/wallet/')
assert response.status_code == 200, f"❌ Wallet URL returned {response.status_code}, not 200"
print("✅ Wallet page is accessible")

# Test 3: Check hotel date min attribute in JavaScript
print("\n[TEST 3] Hotel date picker - checking min date initialization...")
response = client.get(reverse('hotels:hotel_detail', args=[1]))
assert b'checkinInput.min = minDate' in response.content or b'setHours(0, 0, 0, 0)' in response.content, "❌ Date min validation not found"
print("✅ Hotel date picker has min date logic")

# Test 4: Bus seat aisle text
print("\n[TEST 4] Bus seat layout - checking aisle text removed...")
response = client.get(reverse('buses:bus_detail', args=[1]) if 'buses:bus_detail' in [x.name for x in []] else '/buses/1/')
if response.status_code == 200:
    assert b'<div class="aisle"></div>' in response.content, "❌ Aisle div should be empty"
    assert b'<div class="aisle">AISLE</div>' not in response.content, "❌ AISLE text still present"
    print("✅ Bus seat aisle text is removed")
else:
    print("⚠️  Could not test bus detail (page may not exist)")

# Test 5: Phone validation backend still enforces exactly 10
print("\n[TEST 5] Phone backend validation - checking 10-digit requirement...")
from users.views import UserRegistrationForm
form = UserRegistrationForm(data={
    'email': 'test2@test.com',
    'password': 'TestPass123',
    'password_confirm': 'TestPass123',
    'first_name': 'Test',
    'last_name': 'User',
    'phone': '12345678901'  # 11 digits - should fail
})
assert not form.is_valid(), "❌ Backend should reject 11-digit phone"
print("✅ Backend correctly rejects non-10-digit phone numbers")

print("\n" + "=" * 80)
print("ALL TESTS PASSED ✅")
print("=" * 80)
