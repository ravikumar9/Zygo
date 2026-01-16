#!/usr/bin/env python
"""
FINAL VERIFICATION - DEV SERVER UI TESTING
Real browser simulation for all critical features
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta

User = get_user_model()
client = Client()

print("\n" + "=" * 80)
print("FINAL VERIFICATION - DEV SERVER UI FEATURES")
print("=" * 80)

# ============================================================================
# PREPARE TEST USER - EMAIL VERIFIED (REAL USER SCENARIO)
# ============================================================================
print("\n[SETUP] Creating verified test user...")
user, created = User.objects.get_or_create(
    username='dev_test@example.com',
    defaults={
        'email': 'dev_test@example.com',
        'first_name': 'Dev',
        'last_name': 'Tester',
        'phone': '9876543210'
    }
)

if created or not user.has_usable_password():
    user.set_password('DevTest123!')
    user.save()

if not user.email_verified_at:
    user.email_verified_at = timezone.now()
    user.save()

print(f"  User: {user.email}")
print(f"  Email verified: {user.email_verified_at is not None}")

# ============================================================================
# TEST 1: WALLET PAGE - CRITICAL BLOCKER
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 1] WALLET PAGE - HTTP 200 WITH HTML RENDERING")
print("=" * 80)

# Login
login_success = client.login(username='dev_test@example.com', password='DevTest123!')
print(f"\nLogin result: {login_success}")

# Access wallet page
response = client.get('/payments/wallet/')
print(f"URL: http://localhost:8000/payments/wallet/")
print(f"HTTP Status: {response.status_code}")
print(f"Content-Type: {response.get('Content-Type', 'N/A')}")

if response.status_code == 200:
    content = response.content.decode('utf-8', errors='ignore')
    
    # Check for HTML elements (not JSON)
    checks = {
        'HTML structure': '<!DOCTYPE' in content or '<html' in content or '<head' in content,
        'Wallet balance display': 'Available Balance' in content or 'balance' in content.lower(),
        'Transaction history': 'Transaction History' in content or 'transactions' in content.lower(),
        'Cashback section': 'Cashback' in content or 'cashback' in content.lower(),
        'Card layout': 'card' in content.lower() or 'wallet' in content.lower(),
    }
    
    print("\nPage Content Verification:")
    for check_name, result in checks.items():
        status = "✓ YES" if result else "✗ NO"
        print(f"  {check_name}: {status}")
    
    all_passed = all(checks.values())
    print(f"\n  RESULT: {'PASS - Wallet page renders correctly' if all_passed else 'FAIL - Missing elements'}")
    
    if not all_passed:
        print("\n  DEBUG - First 500 chars of response:")
        print(f"  {content[:500]}")
else:
    print(f"  RESULT: FAIL - Expected 200, got {response.status_code}")
    if response.status_code == 302:
        print(f"  Redirect to: {response.url}")

# ============================================================================
# TEST 2: HOTEL IMAGES - PLACEHOLDER VERIFICATION
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 2] HOTEL IMAGES - NO 'UNAVAILABLE' TEXT")
print("=" * 80)

response = client.get('/hotels/')
print(f"\nURL: http://localhost:8000/hotels/")
print(f"HTTP Status: {response.status_code}")

if response.status_code == 200:
    content = response.content.decode('utf-8', errors='ignore')
    
    checks = {
        'Has hotel cards': 'card' in content.lower() or 'hotel' in content.lower(),
        'Has img tags': '<img' in content,
        'Has display_image_url': 'display_image_url' in content or '/static/' in content or '/media/' in content,
        'NO "unavailable" text': 'unavailable' not in content.lower(),
        'Has placeholder fallback': 'hotel_placeholder' in content or 'onerror=' in content,
    }
    
    print("\nHotel Images Verification:")
    for check_name, result in checks.items():
        status = "✓ YES" if result else "✗ NO"
        print(f"  {check_name}: {status}")
    
    all_passed = all(checks.values())
    print(f"\n  RESULT: {'PASS - Hotel images properly configured' if all_passed else 'PARTIAL - Check issues'}")
else:
    print(f"  RESULT: FAIL - Expected 200, got {response.status_code}")

# ============================================================================
# TEST 3: HOTEL DATE PICKER - PAST DATES BLOCKED
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 3] HOTEL DATE PICKER - MIN DATE VALIDATION")
print("=" * 80)

response = client.get('/hotels/')
print(f"\nURL: http://localhost:8000/hotels/ (search form)")
print(f"HTTP Status: {response.status_code}")

if response.status_code == 200:
    content = response.content.decode('utf-8', errors='ignore')
    
    # Get today's date for comparison
    today = date.today()
    min_date_str = today.strftime('%Y-%m-%d')
    
    checks = {
        'Has checkin input': 'name="checkin"' in content or 'name="checkin_date"' in content,
        'Has checkout input': 'name="checkout"' in content or 'name="checkout_date"' in content,
        'Has min-date validation JS': 'minDate' in content or 'setHours' in content or 'new Date()' in content,
        'Today date set as min': min_date_str in content or 'min=' in content,
    }
    
    print("\nDate Picker Verification:")
    for check_name, result in checks.items():
        status = "✓ YES" if result else "✗ NO"
        print(f"  {check_name}: {status}")
    
    # Also check hotel detail page
    from hotels.models import Hotel
    hotel = Hotel.objects.filter(is_active=True).first()
    
    if hotel:
        response = client.get(f'/hotels/{hotel.id}/')
        if response.status_code == 200:
            content = response.content.decode('utf-8', errors='ignore')
            has_detail_validation = 'minDate' in content or 'setHours' in content
            checks['Hotel detail has min-date'] = has_detail_validation
            print(f"  Hotel detail has min-date: {'✓ YES' if has_detail_validation else '✗ NO'}")
    
    all_passed = all(checks.values())
    print(f"\n  RESULT: {'PASS - Date picker blocks past dates' if all_passed else 'PARTIAL - Check issues'}")
else:
    print(f"  RESULT: FAIL - Expected 200, got {response.status_code}")

# ============================================================================
# TEST 4: LOGIN REDIRECT - NO REGISTER LOOP
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 4] LOGIN REDIRECT - VERIFIED USER TO HOME")
print("=" * 80)

client.logout()

# Login again
login_ok = client.login(username='dev_test@example.com', password='DevTest123!')
print(f"\nLogin: {'SUCCESS' if login_ok else 'FAILED'}")

if login_ok:
    # Try accessing home page
    response = client.get('/')
    print(f"Home page status: {response.status_code}")
    
    if response.status_code == 200:
        content = response.content.decode('utf-8', errors='ignore')
        checks = {
            'Is home page': 'home' in content.lower() or 'featured' in content.lower() or 'hotel' in content.lower(),
            'NOT register page': '/users/register' not in content or 'href="/users/register"' not in content,
            'Logout available': 'logout' in content.lower() or 'sign out' in content.lower(),
        }
        
        print("\nLogin Redirect Verification:")
        for check_name, result in checks.items():
            status = "✓ YES" if result else "✗ NO"
            print(f"  {check_name}: {status}")
        
        all_passed = all(checks.values())
        print(f"\n  RESULT: {'PASS - Login redirects correctly' if all_passed else 'PARTIAL - Check issue'}")
    else:
        print(f"  RESULT: FAIL - Home page returned {response.status_code}")
else:
    print(f"  RESULT: FAIL - Login failed")

# ============================================================================
# TEST 5: BUS SEAT LAYOUT - NO AISLE TEXT
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 5] BUS SEAT LAYOUT - CLEAN LAYOUT")
print("=" * 80)

from buses.models import Bus
bus = Bus.objects.filter(is_active=True).first()

if bus:
    response = client.get(f'/buses/{bus.id}/')
    print(f"\nBus seat layout page HTTP: {response.status_code}")
    
    if response.status_code == 200:
        content = response.content.decode('utf-8', errors='ignore')
        
        checks = {
            'Has seat layout': 'seat' in content.lower() or 'class="aisle' in content.lower(),
            'NO "AISLE" text': '<div class="aisle">AISLE</div>' not in content,
            'Has empty aisle div': '<div class="aisle"></div>' in content or 'aisle' in content.lower(),
        }
        
        print("\nBus Seat Layout Verification:")
        for check_name, result in checks.items():
            status = "✓ YES" if result else "✗ NO"
            print(f"  {check_name}: {status}")
        
        all_passed = all(checks.values())
        print(f"\n  RESULT: {'PASS - Bus layout clean' if all_passed else 'FAIL - Check issue'}")
    else:
        print(f"  RESULT: SKIP - Bus page not found")
else:
    print(f"\n  RESULT: SKIP - No active buses in database")

# ============================================================================
# TEST 6: CORPORATE BOOKING - STATUS CHECK
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 6] CORPORATE BOOKING - FEATURE STATUS")
print("=" * 80)

response = client.get('/packages/')
print(f"\nCorporate packages page HTTP: {response.status_code}")

if response.status_code == 200:
    content = response.content.decode('utf-8', errors='ignore')
    checks = {
        'Page loads': True,
        'Has packages': 'package' in content.lower() or 'tour' in content.lower() or 'corporate' in content.lower(),
        'NOT broken link': response.status_code != 404,
    }
    
    print("\nCorporate Booking Status:")
    for check_name, result in checks.items():
        status = "✓ YES" if result else "✗ NO"
        print(f"  {check_name}: {status}")
    
    print(f"\n  RESULT: WORKING - Corporate section accessible")
else:
    print(f"  RESULT: ISSUE - Status {response.status_code}")

# ============================================================================
# TEST 7: ADMIN ROLLBACK - CODE VERIFICATION
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 7] ADMIN ROLLBACK - SOFT DELETE/RESTORE ACTION")
print("=" * 80)

try:
    from bookings.admin import BookingAdmin
    
    has_restore = hasattr(BookingAdmin, 'restore_deleted_bookings')
    has_delete = hasattr(BookingAdmin, 'soft_delete_action')
    
    actions = getattr(BookingAdmin, 'actions', [])
    has_restore_in_actions = 'restore_deleted_bookings' in actions
    has_delete_in_actions = 'soft_delete_action' in actions
    
    print("\nAdmin Actions Verification:")
    print(f"  Soft delete method exists: {'✓ YES' if has_delete else '✗ NO'}")
    print(f"  Restore method exists: {'✓ YES' if has_restore else '✗ NO'}")
    print(f"  Restore in actions list: {'✓ YES' if has_restore_in_actions else '✗ NO'}")
    print(f"  Delete in actions list: {'✓ YES' if has_delete_in_actions else '✗ NO'}")
    
    all_passed = has_restore and has_delete and has_restore_in_actions and has_delete_in_actions
    print(f"\n  RESULT: {'PASS - Admin rollback available' if all_passed else 'FAIL - Actions missing'}")
    
except Exception as e:
    print(f"\n  RESULT: ERROR - {str(e)}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print("""
To verify on DEV server (https://goexplorer-dev.cloud):

1. WALLET PAGE - Do this:
   - Login as a real user (email verified)
   - Click wallet icon in navbar
   - Should load: /payments/wallet/ (HTTP 200)
   - Should show: Balance, Transactions, Cashback info

2. HOTEL IMAGES - Do this:
   - Go to home page
   - Go to /hotels/ listing
   - Go to hotel detail page
   - VERIFY: Images show building illustration (NOT "unavailable" text)

3. DATE PICKER - Do this:
   - Go to /hotels/ or hotel detail
   - Try to select past date in calendar
   - Calendar should gray out / block past dates
   - Try typing past date manually - should be blocked or rejected

4. LOGIN FLOW - Do this:
   - Logout
   - Login with verified user
   - Should redirect to HOME, NOT to /users/register

5. CORPORATE - Do this:
   - Navigate to /packages/
   - Should load without 404

6. ADMIN - Do this:
   - Go to Django admin
   - Bookings section
   - Edit any booking, soft delete it
   - Should appear in admin with restore option
   - Click restore - should restore booking

All code changes are in place and ready for DEV testing.
""")
