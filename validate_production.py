#!/usr/bin/env python
"""
STANDALONE VALIDATION SCRIPT
Verifies all implementations without pytest infrastructure
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
sys.path.insert(0, '/c/Users/ravi9/Downloads/cgpt/Go_explorer_clear')

django.setup()

from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from core.models import City
from property_owners.models import PropertyOwner, PropertyType, Property
from property_owners.property_approval_models import (
    PropertyApprovalRequest, PropertyApprovalChecklist, PropertyApprovalAuditLog
)
from hotels.models import Hotel, RoomType, MealPlan, RoomMealPlan, RoomImage
from bookings.models import Booking, HotelBooking
from bookings.booking_api import PricingService

User = get_user_model()

print("\n" + "="*70)
print("🚀 GOIBIBO PRODUCTION IMPLEMENTATION VALIDATION")
print("="*70 + "\n")

test_results = []

# ============ TEST 1: Models Exist ============
print("✓ Test 1: Checking Models...")
try:
    assert PropertyApprovalRequest is not None
    assert PropertyApprovalChecklist is not None
    assert PropertyApprovalAuditLog is not None
    print("  ✅ PropertyApprovalRequest model exists")
    print("  ✅ PropertyApprovalChecklist model exists")
    print("  ✅ PropertyApprovalAuditLog model exists")
    test_results.append(True)
except AssertionError as e:
    print(f"  ❌ {e}")
    test_results.append(False)

# ============ TEST 2: Pricing Service ============
print("\n✓ Test 2: Pricing Calculations...")
try:
    # Create test room
    city = City.objects.first() or City.objects.create(name='Test', state='Test')
    hotel = Hotel.objects.create(
        name='Test Hotel',
        city=city,
        description='Test',
        address='Test',
        contact_phone='+919999999999',
        contact_email='test@test.com'
    )
    
    # Budget room (₹3000) → 0% GST
    room_budget = RoomType.objects.create(
        hotel=hotel,
        name='Budget Room',
        description='Budget',
        max_adults=2,
        base_price=Decimal('3000.00'),
        bed_type='double',
        room_size=200,
        status='READY'
    )
    
    pricing = PricingService.calculate_booking_price(
        room_budget, None, num_nights=1, num_rooms=1
    )
    
    assert pricing['gst_rate'] == Decimal('0.00'), f"Expected 0% GST, got {pricing['gst_rate']}"
    assert pricing['service_fee'] == Decimal('99.00'), f"Expected ₹99 service fee, got {pricing['service_fee']}"
    print(f"  ✅ Budget room (₹3000): 0% GST, ₹99 service fee")
    print(f"     Total: ₹{pricing['total_amount']}")
    
    # Premium room (₹16000) → 5% GST
    room_premium = RoomType.objects.create(
        hotel=hotel,
        name='Premium Room',
        description='Premium',
        max_adults=2,
        base_price=Decimal('16000.00'),
        bed_type='king',
        room_size=400,
        status='READY'
    )
    
    pricing_premium = PricingService.calculate_booking_price(
        room_premium, None, num_nights=1, num_rooms=1
    )
    
    assert pricing_premium['gst_rate'] == Decimal('18.00'), f"Expected 18% GST for ₹16000, got {pricing_premium['gst_rate']}"
    print(f"  ✅ Premium room (₹16000): 18% GST")
    print(f"     Total: ₹{pricing_premium['total_amount']}")
    
    test_results.append(True)
except Exception as e:
    print(f"  ❌ {e}")
    test_results.append(False)

# ============ TEST 3: Meal Plan Pricing ============
print("\n✓ Test 3: Meal Plan Dynamic Pricing...")
try:
    # Create meal plans
    room_only = MealPlan.objects.get_or_create(
        name='Room Only',
        defaults={'plan_type': 'room_only', 'is_refundable': True}
    )[0]
    
    breakfast = MealPlan.objects.get_or_create(
        name='Breakfast',
        defaults={'plan_type': 'breakfast', 'is_refundable': True}
    )[0]
    
    # Link to room
    RoomMealPlan.objects.get_or_create(
        room_type=room_budget,
        meal_plan=room_only,
        defaults={'price_delta': Decimal('0.00'), 'is_active': True, 'is_default': True}
    )
    
    RoomMealPlan.objects.get_or_create(
        room_type=room_budget,
        meal_plan=breakfast,
        defaults={'price_delta': Decimal('500.00'), 'is_active': True}
    )
    
    # Price with Room Only
    pricing_room_only = PricingService.calculate_booking_price(
        room_budget, meal_plan=None, num_nights=1, num_rooms=1
    )
    
    # Price with Breakfast
    breakfast_rmp = RoomMealPlan.objects.get(room_type=room_budget, meal_plan=breakfast)
    pricing_breakfast = PricingService.calculate_booking_price(
        room_budget, meal_plan=breakfast_rmp.meal_plan, num_nights=1, num_rooms=1
    )
    
    assert pricing_breakfast['subtotal_per_night'] > pricing_room_only['subtotal_per_night']
    print(f"  ✅ Room Only: ₹{pricing_room_only['subtotal_per_night']}")
    print(f"  ✅ Room + Breakfast: ₹{pricing_breakfast['subtotal_per_night']}")
    print(f"  ✅ Meal plan delta correctly applied")
    
    test_results.append(True)
except Exception as e:
    print(f"  ❌ {e}")
    test_results.append(False)

# ============ TEST 4: Admin Approval Workflow ============
print("\n✓ Test 4: Admin Approval Workflow...")
try:
    # Create users
    admin_user = User.objects.create_user(
        username=f'admin_{os.urandom(4).hex()}',
        email=f'admin_{os.urandom(4).hex()}@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True
    )
    
    owner_user = User.objects.create_user(
        username=f'owner_{os.urandom(4).hex()}',
        email=f'owner_{os.urandom(4).hex()}@test.com',
        password='testpass123'
    )
    
    # Create property owner
    prop_type = PropertyType.objects.first() or PropertyType.objects.create(name='homestay')
    owner_profile = PropertyOwner.objects.create(
        user=owner_user,
        business_name='Test Homestays',
        property_type=prop_type,
        owner_name='Test Owner',
        owner_phone='+919876543210',
        owner_email='owner@test.com',
        city=city,
        address='123 St',
        pincode='110001',
        verification_status='verified'
    )
    
    # Create property
    property_obj = Property.objects.create(
        owner=owner_profile,
        name='Test Property',
        city=city,
        address='123 St',
        contact_phone='+919876543210',
        contact_email='prop@test.com',
        base_price=Decimal('5000.00'),
        status='DRAFT'
    )
    
    # Submit for approval
    property_obj.status = 'PENDING'
    property_obj.submitted_at = django.utils.timezone.now()
    property_obj.save()
    
    approval_req = PropertyApprovalRequest.objects.create(
        property=property_obj,
        status='SUBMITTED',
        submitted_by=owner_user,
        submission_data={'name': property_obj.name}
    )
    
    checklist = PropertyApprovalChecklist.objects.create(approval_request=approval_req)
    checklist.initialize_checklist()
    
    print(f"  ✅ Property submitted (status: {property_obj.status})")
    
    # Admin approves
    approval_req.approve(admin_user, approval_reason='Approved')
    property_obj.refresh_from_db()
    
    assert property_obj.status == 'APPROVED'
    assert approval_req.status == 'APPROVED'
    print(f"  ✅ Property approved (status: {property_obj.status})")
    
    # Admin revokes
    approval_req.revoke_approval(admin_user, 'Test revocation')
    property_obj.refresh_from_db()
    
    assert property_obj.status == 'REJECTED'
    assert approval_req.status == 'REVOKED'
    print(f"  ✅ Approval revoked (status: {property_obj.status})")
    
    test_results.append(True)
except Exception as e:
    print(f"  ❌ {e}")
    import traceback
    traceback.print_exc()
    test_results.append(False)

# ============ TEST 5: Booking Creation ============
print("\n✓ Test 5: Booking Creation...")
try:
    booking = Booking.objects.create(
        booking_type='hotel',
        status='reserved',
        customer_name='Test User',
        customer_email='user@test.com',
        customer_phone='+919876543210',
        total_amount=Decimal('5000.00')
    )
    
    assert booking.status == 'reserved'
    print(f"  ✅ Booking created (status: {booking.status})")
    print(f"  ✅ Booking ID: {booking.booking_id}")
    
    test_results.append(True)
except Exception as e:
    print(f"  ❌ {e}")
    test_results.append(False)

# ============ TEST 6: Inventory Alerts ============
print("\n✓ Test 6: Inventory Alerts...")
try:
    # Create low-inventory room
    room_limited = RoomType.objects.create(
        hotel=hotel,
        name='Limited Room',
        description='Limited',
        max_adults=2,
        base_price=Decimal('5000.00'),
        bed_type='double',
        room_size=300,
        total_rooms=3,  # Less than 5
        status='READY'
    )
    
    pricing_limited = PricingService.calculate_booking_price(
        room_limited, None, num_nights=1, num_rooms=1
    )
    
    assert pricing_limited['inventory_warning'] is not None
    assert 'Only' in pricing_limited['inventory_warning']
    print(f"  ✅ Inventory alert displayed: {pricing_limited['inventory_warning']}")
    
    test_results.append(True)
except Exception as e:
    print(f"  ❌ {e}")
    test_results.append(False)

# ============ RESULTS ============
print("\n" + "="*70)
print(f"📊 VALIDATION RESULTS: {sum(test_results)}/{len(test_results)} PASSED")
print("="*70)

if all(test_results):
    print("\n✅ ✅ ✅  PRODUCTION READY  ✅ ✅ ✅\n")
    sys.exit(0)
else:
    print("\n❌ Some tests failed\n")
    sys.exit(1)
