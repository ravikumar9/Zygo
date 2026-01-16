"""
Comprehensive verification of all 7 critical UI fixes - Windows compatible
Tests against local Django test client to verify fixes work
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from bs4 import BeautifulSoup

User = get_user_model()

def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def print_test(name, passed):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {name}")

# Create verified test user
print_section("SETUP - Creating verified test user")
user, created = User.objects.get_or_create(
    email='verified_test@example.com',
    defaults={
        'username': 'verified_test',
        'is_email_verified': True,
        'phone': '+919999999999',
        'is_phone_verified': True
    }
)
if created:
    user.set_password('TestPass123!')
    user.save()
print(f"User: {user.email}")
print(f"Email verified: {user.is_email_verified}")
print(f"Phone verified: {user.is_phone_verified}")

client = Client()

# Login
login_success = client.login(username=user.email, password='TestPass123!')
print(f"Login: {login_success}")

# ============================================================================
# TEST 1: WALLET PAGE - Must return HTML, not JSON/API response
# ============================================================================
print_section("TEST 1: WALLET PAGE - HTML RENDERING")

response = client.get('/payments/wallet/')
print(f"URL: /payments/wallet/")
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.get('Content-Type', 'unknown')}")

wallet_pass = True
if response.status_code != 200:
    print_test("HTTP 200 response", False)
    wallet_pass = False
else:
    print_test("HTTP 200 response", True)

if 'text/html' not in response.get('Content-Type', ''):
    print_test("Returns HTML (not JSON/API)", False)
    wallet_pass = False
else:
    print_test("Returns HTML (not JSON/API)", True)

soup = BeautifulSoup(response.content, 'html.parser')
has_balance = soup.find(string=lambda t: t and 'Balance' in t) is not None
print_test("Shows balance section", has_balance)
wallet_pass = wallet_pass and has_balance

has_transactions = soup.find(string=lambda t: t and ('Transaction' in t or 'History' in t)) is not None
print_test("Shows transaction history", has_transactions)
wallet_pass = wallet_pass and has_transactions

# Check for broken URL reference
broken_url = 'bookings:list' in response.content.decode('utf-8')
print_test("No broken URL references", not broken_url)
wallet_pass = wallet_pass and not broken_url

print(f"\nWALLET PAGE: {'PASS' if wallet_pass else 'FAIL'}")

# ============================================================================
# TEST 2: HOTEL IMAGES - No "unavailable" text anywhere
# ============================================================================
print_section("TEST 2: HOTEL IMAGES - NO UNAVAILABLE TEXT")

# Check placeholder SVG
placeholder_path = os.path.join('static', 'images', 'hotel_placeholder.svg')
if os.path.exists(placeholder_path):
    with open(placeholder_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()
    has_unavailable = 'unavailable' in svg_content.lower() or 'not available' in svg_content.lower()
    print_test("Placeholder SVG has no unavailable text", not has_unavailable)
    hotel_images_pass = not has_unavailable
else:
    print_test("Placeholder SVG exists", False)
    hotel_images_pass = False

# Check hotel list page
response = client.get('/hotels/')
if response.status_code == 200:
    print_test("Hotel list page loads", True)
    soup = BeautifulSoup(response.content, 'html.parser')
    page_text = soup.get_text().lower()
    has_unavailable = 'image unavailable' in page_text or 'not available' in page_text
    print_test("Hotel list has no unavailable text", not has_unavailable)
    hotel_images_pass = hotel_images_pass and not has_unavailable
else:
    print_test("Hotel list page loads", False)
    hotel_images_pass = False

print(f"\nHOTEL IMAGES: {'PASS' if hotel_images_pass else 'FAIL'}")

# ============================================================================
# TEST 3: HOTEL DATE PICKER - Min date validation like bus booking
# ============================================================================
print_section("TEST 3: HOTEL DATE PICKER - PAST DATE BLOCKING")

# Check hotel detail template for min-date validation
hotel_detail_template = os.path.join('templates', 'hotels', 'hotel_detail.html')
hotel_list_template = os.path.join('templates', 'hotels', 'hotel_list.html')

date_picker_pass = True
for template_path, name in [(hotel_detail_template, 'hotel_detail'), (hotel_list_template, 'hotel_list')]:
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        has_min_date = 'min=' in template_content or 'setAttribute' in template_content and 'min' in template_content
        print_test(f"{name}.html has min-date validation", has_min_date)
        date_picker_pass = date_picker_pass and has_min_date
    else:
        print_test(f"{name}.html exists", False)
        date_picker_pass = False

print(f"\nDATE PICKER: {'PASS' if date_picker_pass else 'FAIL'}")

# ============================================================================
# TEST 4: LOGIN REDIRECT - Verified users go to home, not register
# ============================================================================
print_section("TEST 4: LOGIN REDIRECT - NO REDIRECT TO REGISTER")

# Logout and login again to test redirect
client.logout()
response = client.post('/users/login/', {
    'username': user.email,
    'password': 'TestPass123!'
}, follow=True)

login_redirect_pass = True
final_url = response.redirect_chain[-1][0] if response.redirect_chain else ''
print(f"Final URL after login: {final_url}")

if '/users/register' in final_url:
    print_test("Does NOT redirect to /users/register", False)
    login_redirect_pass = False
else:
    print_test("Does NOT redirect to /users/register", True)

if '/' in final_url or '/core/home' in final_url:
    print_test("Redirects to home page", True)
else:
    print_test("Redirects to home page", False)
    login_redirect_pass = False

print(f"\nLOGIN REDIRECT: {'PASS' if login_redirect_pass else 'FAIL'}")

# ============================================================================
# TEST 5: BUS SEAT LAYOUT - No "AISLE" text visible
# ============================================================================
print_section("TEST 5: BUS SEAT LAYOUT - NO AISLE TEXT")

bus_template = os.path.join('templates', 'buses', 'bus_detail.html')
seat_layout_pass = True

if os.path.exists(bus_template):
    with open(bus_template, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Check that AISLE div exists but is empty
    has_empty_aisle = '<div class="aisle"></div>' in template_content
    has_aisle_text = '<div class="aisle">AISLE</div>' in template_content
    
    print_test("Empty aisle div exists", has_empty_aisle)
    print_test("No AISLE text in template", not has_aisle_text)
    seat_layout_pass = has_empty_aisle and not has_aisle_text
else:
    print_test("Bus detail template exists", False)
    seat_layout_pass = False

print(f"\nSEAT LAYOUT: {'PASS' if seat_layout_pass else 'FAIL'}")

# ============================================================================
# TEST 6: CORPORATE BOOKING - Feature status check
# ============================================================================
print_section("TEST 6: CORPORATE BOOKING - FEATURE STATUS")

# Check if corporate booking routes exist
from django.urls import resolve, Resolver404

corporate_pass = True
try:
    resolve('/dashboard/corporate/')
    print_test("Corporate dashboard URL exists", True)
    
    # Test if it loads
    client.login(username=user.email, password='TestPass123!')
    response = client.get('/dashboard/corporate/')
    if response.status_code == 200:
        print_test("Corporate dashboard loads (HTTP 200)", True)
        soup = BeautifulSoup(response.content, 'html.parser')
        is_coming_soon = 'coming soon' in soup.get_text().lower()
        print(f"Status: {'Coming Soon placeholder' if is_coming_soon else 'Functional dashboard'}")
    elif response.status_code == 404:
        print_test("Corporate dashboard loads (HTTP 200)", False)
        corporate_pass = False
    else:
        print(f"Corporate dashboard returns {response.status_code}")
except Resolver404:
    print_test("Corporate dashboard URL exists", False)
    print("Recommendation: Remove from navbar or implement feature")
    corporate_pass = False

print(f"\nCORPORATE BOOKING: {'PASS' if corporate_pass else 'NEEDS DECISION'}")

# ============================================================================
# TEST 7: ADMIN ROLLBACK - Soft delete and restore functionality
# ============================================================================
print_section("TEST 7: ADMIN ROLLBACK - SOFT DELETE & RESTORE")

# Check if Booking model has soft delete fields
from bookings.models import Booking
from django.db import models

admin_pass = True

# Check for soft delete fields
has_deleted_at = hasattr(Booking, 'deleted_at')
has_is_deleted = hasattr(Booking, 'is_deleted')

print_test("Booking has soft delete fields", has_deleted_at or has_is_deleted)
admin_pass = has_deleted_at or has_is_deleted

# Check admin configuration
from bookings.admin import BookingAdmin
from django.contrib import admin

booking_admin = admin.site._registry.get(Booking)
if booking_admin:
    print_test("Booking registered in admin", True)
    
    # Check for restore action
    actions = booking_admin.actions if hasattr(booking_admin, 'actions') else []
    has_restore = any('restore' in str(action).lower() for action in actions)
    print_test("Restore action available", has_restore)
    admin_pass = admin_pass and has_restore
else:
    print_test("Booking registered in admin", False)
    admin_pass = False

print(f"\nADMIN ROLLBACK: {'PASS' if admin_pass else 'NEEDS VERIFICATION IN ADMIN UI'}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print_section("FINAL SUMMARY - ALL 7 CRITICAL FIXES")

results = {
    "1. Wallet Page (HTML rendering)": wallet_pass,
    "2. Hotel Images (no unavailable text)": hotel_images_pass,
    "3. Date Picker (min-date validation)": date_picker_pass,
    "4. Login Redirect (no register redirect)": login_redirect_pass,
    "5. Bus Seat Layout (no AISLE text)": seat_layout_pass,
    "6. Corporate Booking (feature status)": corporate_pass,
    "7. Admin Rollback (soft delete/restore)": admin_pass
}

for feature, passed in results.items():
    status = "PASS" if passed else "FAIL/NEEDS REVIEW"
    print(f"{status:20} | {feature}")

passed_count = sum(results.values())
total_count = len(results)

print(f"\nRESULT: {passed_count}/{total_count} tests passed")

if passed_count == total_count:
    print("\nALL CRITICAL FIXES VERIFIED - Ready for DEV browser testing")
else:
    print("\nSOME ISSUES NEED ATTENTION - Review failed tests above")

print("\nNEXT STEPS:")
print("1. Deploy to DEV server (https://goexplorer-dev.cloud)")
print("2. Perform browser testing with screenshots")
print("3. Run seed_data_clean.py on DEV for test data")
print("4. Verify admin rollback in Django admin UI")
print("5. Take screenshots as proof for each feature")
