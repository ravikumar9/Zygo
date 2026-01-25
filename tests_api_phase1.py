"""
PHASE 1 API TESTS — Comprehensive end-to-end validation
Tests all features before UI implementation
"""
import os
import django
import json
from decimal import Decimal
from datetime import date, timedelta, datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from hotels.models import Hotel, RoomType, MealPlan, RoomMealPlan, City
from payments.models import Wallet, WalletTransaction
from bookings.models import Booking, InventoryLock
from property_owners.models import Property, PropertyOwner, PropertyType
from core.models import PromoCode
from bookings.promo_models import PromoCode as BookingPromoCode

User = get_user_model()
client = Client()

# Color codes for test output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def safe_print(text):
    """Print safely without encoding issues"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace problematic chars
        safe_text = text.encode('ascii', errors='replace').decode('ascii')
        print(safe_text)

def log_test(name, passed, details=""):
    status_text = f"{GREEN}[PASS]{RESET}" if passed else f"{RED}[FAIL]{RESET}"
    try:
        safe_details = details.encode('ascii', errors='replace').decode('ascii') if details else ""
        safe_print(f"{status_text} {name}")
        if safe_details:
            safe_print(f"  {safe_details}")
    except:
        safe_print(f"{status_text} {name}")

def log_section(title):
    safe_print(f"\n{BOLD}{YELLOW}{'='*60}{RESET}")
    safe_print(f"{BOLD}{title}{RESET}")
    safe_print(f"{BOLD}{YELLOW}{'='*60}{RESET}")

results = {
    'passed': 0,
    'failed': 0,
    'tests': []
}

# ============================================
# SETUP: Create test data
# ============================================

log_section("SETUP: Creating Test Data")

try:
    # Create city
    city, _ = City.objects.get_or_create(name='Test City')
    
    # Create admin user
    admin_user, _ = User.objects.get_or_create(
        username='admin_test',
        defaults={
            'email': 'admin@test.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    # Create owner user
    owner_user, _ = User.objects.get_or_create(
        username='owner_test',
        defaults={'email': 'owner@test.com'}
    )
    
    # Create guest user
    guest_user, _ = User.objects.get_or_create(
        username='guest_test',
        defaults={'email': 'guest@test.com'}
    )
    
    # Create PropertyOwner profile
    prop_owner, _ = PropertyOwner.objects.get_or_create(
        user=owner_user,
        defaults={
            'business_name': 'Test Hotel Co',
            'owner_name': 'Owner Test',
            'owner_phone': '9876543210',
            'owner_email': 'owner@test.com',
            'city': city,
            'address': 'Test Address',
            'pincode': '12345'
        }
    )
    
    # Create PropertyType
    prop_type, _ = PropertyType.objects.get_or_create(name='hotel')
    
    # Create Property (onboarding)
    property_obj, _ = Property.objects.get_or_create(
        owner=prop_owner,
        name='Test Hotel Property',
        defaults={
            'status': 'DRAFT',
            'description': 'Test hotel for API testing',
            'property_type': prop_type,
            'city': city,
            'address': 'Test Address',
            'contact_phone': '9876543210',
            'contact_email': 'hotel@test.com',
            'base_price': Decimal('5000'),
            'max_guests': 2,
            'num_bedrooms': 1,
            'num_bathrooms': 1
        }
    )
    
    # Create Hotel (approved)
    hotel, _ = Hotel.objects.get_or_create(
        name='Test Hotel Approved',
        defaults={
            'city': city,
            'address': 'Test Address',
            'is_active': True,
            'owner_property': property_obj if property_obj.status == 'APPROVED' else None
        }
    )
    
    # Create approved property if needed
    if not hotel.owner_property or hotel.owner_property.status != 'APPROVED':
        approved_prop, _ = Property.objects.get_or_create(
            owner=prop_owner,
            name='Test Hotel Approved Property',
            defaults={
                'status': 'APPROVED',
                'approved_at': timezone.now(),
                'approved_by': admin_user,
                'description': 'Test hotel approved',
                'property_type': prop_type,
                'city': city,
                'address': 'Test Address',
                'contact_phone': '9876543210',
                'contact_email': 'hotel@test.com',
                'base_price': Decimal('5000'),
                'max_guests': 2,
                'num_bedrooms': 1,
                'num_bathrooms': 1
            }
        )
        hotel.owner_property = approved_prop
        hotel.save(update_fields=['owner_property'])
    
    # Create RoomType
    room_type, _ = RoomType.objects.get_or_create(
        hotel=hotel,
        name='Deluxe Room',
        defaults={
            'base_price': Decimal('5000'),
            'room_type': 'deluxe',
            'max_occupancy': 2,
            'total_rooms': 10
        }
    )
    
    # Create MealPlan
    meal_plan, _ = MealPlan.objects.get_or_create(
        plan_type='breakfast',
        defaults={
            'name': 'Breakfast Included',
            'description': 'Complimentary breakfast',
            'is_active': True
        }
    )
    
    # Create RoomMealPlan
    room_meal_plan, _ = RoomMealPlan.objects.get_or_create(
        room_type=room_type,
        meal_plan=meal_plan,
        defaults={
            'price_delta': Decimal('500'),
            'is_active': True
        }
    )
    
    # Create PromoCode
    promo, _ = BookingPromoCode.objects.get_or_create(
        code='TEST20',
        defaults={
            'discount_type': 'PERCENTAGE',
            'discount_value': Decimal('20'),
            'valid_from': timezone.now(),
            'valid_until': timezone.now() + timedelta(days=30),
            'is_active': True
        }
    )
    
    # Create Wallet for guest
    wallet, _ = Wallet.objects.get_or_create(
        user=guest_user,
        defaults={'balance': Decimal('10000')}
    )
    
    print(f"{GREEN}[OK] Test data created{RESET}")
    
except Exception as e:
    print(f"{RED}[ERROR] Setup failed: {str(e)}{RESET}")
    exit(1)

# ============================================
# TEST 1: PROPERTY ONBOARDING (Draft → Pending → Approved)
# ============================================

log_section("TEST 1: Property Onboarding Workflow")

test_name = "T1.1: Create property in DRAFT status"
try:
    prop = Property.objects.create(
        owner=prop_owner,
        name='Onboarding Test Hotel',
        status='DRAFT',
        description='Testing onboarding',
        property_type=prop_type,
        city=city,
        base_price=Decimal('3000'),
        max_guests=2,
        num_bedrooms=1,
        num_bathrooms=1
    )
    passed = prop.status == 'DRAFT'
    log_test(test_name, passed, f"Status: {prop.status}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

test_name = "T1.2: Submit property to PENDING"
try:
    # Create PropertyRoomType (not Hotel.RoomType) for submission
    from property_owners.models import PropertyRoomType
    prop_room_type, _ = PropertyRoomType.objects.get_or_create(
        property=prop,
        name='Test Room Type Onboarding',
        defaults={
            'base_price': Decimal('3000'),
            'room_type': 'standard',
            'max_occupancy': 2,
            'number_of_beds': 1,
            'room_size': 200,
            'total_rooms': 5,
            'meal_plans': [{'type': 'room_only', 'price': 3000}],
            'is_active': True
        }
    )
    
    prop.submit_for_approval()
    prop.refresh_from_db()
    passed = prop.status == 'PENDING' and prop.submitted_at is not None
    log_test(test_name, passed, f"Status: {prop.status}, Submitted: {prop.submitted_at is not None}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

test_name = "T1.3: Admin approves property"
try:
    # Create a primary image for the property (required for approval)
    from property_owners.models import PropertyImage
    from django.core.files.base import ContentFile
    from PIL import Image as PILImage
    from io import BytesIO
    
    # Create a simple test image
    img = PILImage.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    
    prop_image = PropertyImage.objects.create(
        property=prop,
        image=ContentFile(img_io.read(), 'test_property.jpg'),
        is_primary=True
    )
    
    prop.approve(admin_user)
    prop.refresh_from_db()
    passed = prop.status == 'APPROVED' and prop.approved_at is not None and prop.approved_by == admin_user
    log_test(test_name, passed, f"Status: {prop.status}, Approved by: {prop.approved_by}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

test_name = "T1.4: Approved property is_approved property works"
try:
    prop.refresh_from_db()
    is_approved = prop.is_approved
    passed = is_approved == True
    log_test(test_name, passed, f"is_approved: {is_approved}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

# ============================================
# TEST 2: PRICING & TAX ENGINE (Backend-driven)
# ============================================

log_section("TEST 2: Pricing & Tax Engine")

test_name = "T2.1: Calculate price without meal plan"
try:
    response = client.post('/hotels/api/calculate-price/', {
        'room_type_id': room_type.id,
        'check_in': date.today().isoformat(),
        'check_out': (date.today() + timedelta(days=2)).isoformat(),
        'num_rooms': 1
    }, content_type='application/json')
    
    data = response.json() if response.status_code == 200 else {}
    pricing = data.get('pricing', {})
    
    passed = (
        response.status_code == 200 and
        data.get('success') == True and
        data.get('gst_hidden') == True and
        'tax_modal_data' in data and
        'service_fee' in pricing
    )
    
    log_test(test_name, passed, 
        f"Status: {response.status_code}, GST hidden: {data.get('gst_hidden')}, " +
        f"Total: {pricing.get('total_amount', 'N/A')}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

test_name = "T2.2: Calculate price with meal plan"
try:
    response = client.post('/hotels/api/calculate-price/', {
        'room_type_id': room_type.id,
        'meal_plan_id': room_meal_plan.id,
        'check_in': date.today().isoformat(),
        'check_out': (date.today() + timedelta(days=1)).isoformat(),
        'num_rooms': 1
    }, content_type='application/json')
    
    data = response.json() if response.status_code == 200 else {}
    pricing = data.get('pricing', {})
    
    passed = (
        response.status_code == 200 and
        pricing.get('meal_plan_delta') == 500.0
    )
    
    log_test(test_name, passed,
        f"Meal plan delta: ₹{pricing.get('meal_plan_delta', 'N/A')}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

test_name = "T2.3: Tax modal data structure (GST % hidden)"
try:
    response = client.post('/hotels/api/calculate-price/', {
        'room_type_id': room_type.id,
        'check_in': date.today().isoformat(),
        'check_out': (date.today() + timedelta(days=1)).isoformat(),
        'num_rooms': 1
    }, content_type='application/json')
    
    data = response.json()
    tax_modal = data.get('tax_modal_data', {})
    
    # CRITICAL: GST % should NOT be in tax_modal
    has_gst_pct = 'gst_rate_percent' in tax_modal
    
    passed = (
        'gst_amount' in tax_modal and
        'service_fee' in tax_modal and
        'subtotal' in tax_modal and
        'taxes_total' in tax_modal and
        'total_payable' in tax_modal and
        not has_gst_pct  # PASS only if gst_rate_percent is NOT present
    )
    
    log_test(test_name, passed, f"Tax breakdown complete: {passed}, GST% present: {has_gst_pct}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

# ============================================
# TEST 3: MEAL PLANS (Backend-driven)
# ============================================

log_section("TEST 3: Meal Plans")

test_name = "T3.1: Get meal plans for room"
try:
    response = client.get(f'/hotels/api/room/{room_type.id}/meal-plans/')
    data = response.json() if response.status_code == 200 else {}
    meal_plans = data.get('meal_plans', [])
    
    passed = (
        response.status_code == 200 and
        len(meal_plans) > 0 and
        all('price_delta' in mp for mp in meal_plans)
    )
    
    log_test(test_name, passed, f"Meal plans count: {len(meal_plans)}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

test_name = "T3.2: Meal plan has data-testid"
try:
    response = client.get(f'/hotels/api/room/{room_type.id}/meal-plans/')
    data = response.json()
    meal_plans = data.get('meal_plans', [])
    
    passed = len(meal_plans) > 0 and all('data_testid' in mp for mp in meal_plans)
    
    log_test(test_name, passed, f"All meal plans have data-testid: {passed}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

# ============================================
# TEST 4: WALLET (Auth-gated, Partial Split)
# ============================================

log_section("TEST 4: Wallet System")

test_name = "T4.1: Wallet status for unauthenticated user"
try:
    response = client.get('/hotels/api/wallet/status/')
    data = response.json()
    
    passed = (
        response.status_code == 200 and
        data.get('is_authenticated') == False and
        data.get('balance') is None
    )
    
    log_test(test_name, passed, f"Authenticated: {data.get('is_authenticated')}, Balance visible: {data.get('balance') is not None}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

test_name = "T4.2: Wallet status for authenticated user"
try:
    client.force_login(guest_user)
    response = client.get('/hotels/api/wallet/status/')
    data = response.json()
    
    passed = (
        response.status_code == 200 and
        data.get('is_authenticated') == True and
        isinstance(data.get('balance'), (int, float)) and
        data.get('balance') > 0
    )
    
    log_test(test_name, passed, f"Authenticated: {data.get('is_authenticated')}, Balance: ₹{data.get('balance', 'N/A')}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

# ============================================
# TEST 5: PROMO ENGINE (API-driven validation)
# ============================================

log_section("TEST 5: Promo Engine")

test_name = "T5.1: Validate valid promo code"
try:
    response = client.post('/bookings/api/validate-promo/', {
        'code': 'TEST20',
        'base_amount': 5000
    }, content_type='application/json')
    
    data = response.json()
    
    passed = (
        response.status_code == 200 and
        data.get('valid') == True and
        data.get('discount_amount') > 0
    )
    
    log_test(test_name, passed, f"Valid: {data.get('valid')}, Discount: ₹{data.get('discount_amount', 'N/A')}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

test_name = "T5.2: Reject invalid promo code"
try:
    response = client.post('/bookings/api/validate-promo/', {
        'code': 'INVALID999',
        'base_amount': 5000
    }, content_type='application/json')
    
    data = response.json()
    
    passed = (
        data.get('valid') == False and
        'error' in data
    )
    
    log_test(test_name, passed, f"Valid: {data.get('valid')}, Error: {data.get('error', 'N/A')[:40]}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

# ============================================
# TEST 6: INVENTORY WARNINGS & HOLD TIMER
# ============================================

log_section("TEST 6: Inventory Warnings & Hold Timer")

test_name = "T6.1: Check availability returns warning for low inventory"
try:
    response = client.post('/hotels/api/check-availability/', {
        'room_type_id': room_type.id,
        'check_in': date.today().isoformat(),
        'check_out': (date.today() + timedelta(days=1)).isoformat(),
        'num_rooms': 1
    }, content_type='application/json')
    
    data = response.json()
    
    passed = (
        response.status_code == 200 and
        'inventory_warning' in data and
        'inventory_available' in data
    )
    
    log_test(test_name, passed, f"Warning: {data.get('inventory_warning')}, Available: {data.get('inventory_available')}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

test_name = "T6.2: Hold timer endpoint returns countdown"
try:
    response = client.get(f'/hotels/api/room/{room_type.id}/availability-with-hold/' +
        f'?check_in={date.today().isoformat()}' +
        f'&check_out={(date.today() + timedelta(days=1)).isoformat()}')
    
    data = response.json()
    
    passed = (
        response.status_code == 200 and
        'hold_expires_at' in data and
        'hold_countdown_seconds' in data and
        'is_available' in data
    )
    
    log_test(test_name, passed, f"Hold expires: {data.get('hold_expires_at')}, Countdown: {data.get('hold_countdown_seconds')}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

# ============================================
# TEST 7: ADMIN PRICE UPDATES (Immediate reflect)
# ============================================

log_section("TEST 7: Admin Price Updates")

test_name = "T7.1: Admin can update room price"
try:
    client.force_login(admin_user)
    response = client.post('/hotels/api/admin/price-update/', {
        'room_type_id': room_type.id,
        'base_price': 6000,
        'reason': 'Test price update'
    }, content_type='application/json')
    
    data = response.json()
    room_type.refresh_from_db()
    
    passed = (
        response.status_code == 200 and
        data.get('success') == True and
        float(room_type.base_price) == 6000.0
    )
    
    log_test(test_name, passed, f"Success: {data.get('success')}, New price: ₹{room_type.base_price}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
    
    # Reset price for other tests
    room_type.base_price = Decimal('5000')
    room_type.save()
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

test_name = "T7.2: Non-admin cannot update price"
try:
    client.force_login(guest_user)
    response = client.post('/hotels/api/admin/price-update/', {
        'room_type_id': room_type.id,
        'base_price': 7000
    }, content_type='application/json')
    
    passed = response.status_code == 403
    
    log_test(test_name, passed, f"Status: {response.status_code} (expected 403)")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

# ============================================
# TEST 8: APPROVED PROPERTY VISIBILITY
# ============================================

log_section("TEST 8: Property Approval Gating")

test_name = "T8.1: Unapproved property not in hotel list"
try:
    response = client.get('/hotels/api/list/')
    data = response.json()
    hotels = data.get('results', [])
    
    # Check that only approved hotels are shown
    passed = all(h.get('owner_property_status') != 'DRAFT' for h in hotels if 'owner_property_status' in h)
    
    log_test(test_name, passed, f"Hotels in list: {len(hotels)}")
    results['passed'] += 1 if passed else 0
    results['failed'] += 0 if passed else 1
except Exception as e:
    log_test(test_name, False, str(e))
    results['failed'] += 1

# ============================================
# FINAL RESULTS
# ============================================

log_section("TEST RESULTS SUMMARY")

total = results['passed'] + results['failed']
pass_rate = (results['passed'] / total * 100) if total > 0 else 0

print(f"\n{BOLD}Total Tests: {total}{RESET}")
print(f"{GREEN}[PASS]: {results['passed']}{RESET}")
print(f"{RED}[FAIL]: {results['failed']}{RESET}")
print(f"{BOLD}Pass Rate: {pass_rate:.1f}%{RESET}")

if results['failed'] == 0:
    print(f"\n{GREEN}{BOLD}ALL TESTS PASSED - READY FOR PHASE 2{RESET}")
else:
    print(f"\n{RED}{BOLD}TESTS FAILED - FIX REQUIRED{RESET}")

exit(0 if results['failed'] == 0 else 1)
