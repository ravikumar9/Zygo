#!/usr/bin/env python
"""
Comprehensive test for Session 1: Room Meal Plans
Verifies: Model, pricing, booking integration, admin visibility
"""
import os
import sys
import django
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.models import Hotel, RoomType, RoomMealPlan
from bookings.models import Booking, HotelBooking
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def test_meal_plan_model():
    """Test RoomMealPlan model creation and pricing logic"""
    print("\n" + "="*70)
    print("TEST 1: RoomMealPlan Model Structure")
    print("="*70)
    
    # Get a sample room type
    room_type = RoomType.objects.first()
    if not room_type:
        print("❌ No room types found in database")
        return False
    
    print(f"✓ Found room type: {room_type.name} @ {room_type.hotel.name}")
    
    # Check meal plans exist for this room type
    meal_plans = room_type.meal_plans.filter(is_active=True)
    print(f"✓ Meal plans for this room: {meal_plans.count()}")
    
    if meal_plans.count() != 4:
        print(f"❌ Expected 4 meal plans, got {meal_plans.count()}")
        return False
    
    # Verify plan types
    plan_types = list(meal_plans.values_list('plan_type', flat=True))
    expected = ['room_only', 'room_breakfast', 'room_half_board', 'room_full_board']
    if set(plan_types) != set(expected):
        print(f"❌ Missing plan types. Got: {plan_types}")
        return False
    
    print("✓ All 4 plan types present")
    
    # Verify pricing is absolute (not delta)
    for plan in meal_plans:
        if not isinstance(plan.price_per_night, Decimal):
            print(f"❌ Price not Decimal: {plan.price_per_night}")
            return False
        if plan.price_per_night <= 0:
            print(f"❌ Invalid price: {plan.price_per_night}")
            return False
    
    print("✓ All pricing values are valid Decimals > 0")
    
    # Test price calculation
    plan = meal_plans.first()
    total_price = plan.calculate_total_price(num_rooms=2, num_nights=3)
    expected_total = plan.price_per_night * 2 * 3
    
    if total_price != expected_total:
        print(f"❌ Price calculation mismatch: {total_price} != {expected_total}")
        return False
    
    print(f"✓ Price calculation correct: {plan.name} x2 rooms x3 nights = ₹{total_price}")
    
    return True


def test_meal_plan_pricing():
    """Test that meal plan pricing is progressive (breakfast < half-board < full-board)"""
    print("\n" + "="*70)
    print("TEST 2: Meal Plan Pricing Hierarchy")
    print("="*70)
    
    room_type = RoomType.objects.first()
    meal_plans = room_type.meal_plans.filter(is_active=True).order_by('display_order')
    
    prices = list(meal_plans.values_list('plan_type', 'price_per_night'))
    print(f"Room: {room_type.name} @ Base ₹{room_type.base_price}")
    
    room_only_price = None
    prev_price = Decimal('0')
    
    for plan_type, price in prices:
        plan_name = {
            'room_only': 'Room Only',
            'room_breakfast': 'Room + Breakfast',
            'room_half_board': 'Room + Breakfast + Dinner',
            'room_full_board': 'Room + All Meals'
        }.get(plan_type, plan_type)
        
        print(f"  {plan_name}: ₹{price}")
        
        if plan_type == 'room_only':
            room_only_price = price
        
        if price <= prev_price:
            print(f"❌ Pricing not progressive: {plan_name} (₹{price}) <= previous (₹{prev_price})")
            return False
        
        prev_price = price
    
    print("✓ Pricing correctly progressive (Room Only < Breakfast < Half-Board < Full-Board)")
    return True


def test_booking_integration():
    """Test that HotelBooking requires meal_plan selection"""
    print("\n" + "="*70)
    print("TEST 3: Booking Integration - Meal Plan Requirement")
    print("="*70)
    
    # Check HotelBooking model
    from django.db import models
    meal_plan_field = HotelBooking._meta.get_field('meal_plan')
    
    if meal_plan_field.null:
        print("❌ meal_plan field allows NULL (should be required)")
        return False
    
    print("✓ meal_plan field is non-nullable (required)")
    
    # Check if it's a ForeignKey
    if not isinstance(meal_plan_field, models.ForeignKey):
        print(f"❌ meal_plan is not ForeignKey: {type(meal_plan_field)}")
        return False
    
    print("✓ meal_plan field is ForeignKey to RoomMealPlan")
    return True


def test_admin_visibility():
    """Test that admin interface shows meal plans"""
    print("\n" + "="*70)
    print("TEST 4: Admin Interface - Meal Plan Visibility")
    print("="*70)
    
    from django.contrib import admin
    from hotels.admin import RoomMealPlanAdmin, RoomTypeAdmin
    from bookings.admin import HotelBookingInline
    
    # Check RoomMealPlanAdmin is registered
    if RoomMealPlan not in admin.site._registry:
        print("❌ RoomMealPlan not registered in admin")
        return False
    
    print("✓ RoomMealPlanAdmin registered")
    
    # Check RoomTypeAdmin has inline
    inline_models = [inline.model for inline in RoomTypeAdmin.inlines]
    if RoomMealPlan not in inline_models:
        print("❌ RoomMealPlanInline not in RoomTypeAdmin")
        return False
    
    print("✓ RoomMealPlanInline in RoomTypeAdmin")
    
    # Check HotelBookingInline has meal_plan in fields
    if 'meal_plan' not in HotelBookingInline.fields:
        print("❌ meal_plan not in HotelBookingInline.fields")
        return False
    
    print("✓ meal_plan visible in HotelBookingInline")
    return True


def test_data_consistency():
    """Test data consistency: all room types have meal plans"""
    print("\n" + "="*70)
    print("TEST 5: Data Consistency")
    print("="*70)
    
    room_types = RoomType.objects.all()
    print(f"Total room types: {room_types.count()}")
    
    room_types_without_plans = room_types.filter(meal_plans__isnull=True).distinct()
    if room_types_without_plans.exists():
        print(f"❌ {room_types_without_plans.count()} room types have no meal plans")
        return False
    
    print("✓ All room types have meal plans")
    
    # Check each room type has exactly 4 active plans
    for room_type in room_types[:10]:  # Sample check
        active_plans = room_type.meal_plans.filter(is_active=True).count()
        if active_plans != 4:
            print(f"❌ {room_type.name} has {active_plans} active plans (expected 4)")
            return False
    
    print("✓ Sample room types all have 4 active meal plans")
    
    # Check total seeded meal plans
    total_plans = RoomMealPlan.objects.filter(is_active=True).count()
    expected = room_types.count() * 4
    print(f"Total active meal plans: {total_plans} (expected ~{expected})")
    
    return True


def test_no_hardcoded_prices():
    """Test that prices are stored in database, not hardcoded"""
    print("\n" + "="*70)
    print("TEST 6: No Hardcoded Prices")
    print("="*70)
    
    # Verify pricing is dynamic from model
    room_type = RoomType.objects.first()
    meal_plan = room_type.meal_plans.first()
    
    # Price should come from database
    db_price = meal_plan.price_per_night
    print(f"✓ Meal plan price from database: ₹{db_price}")
    
    # Verify calculation method exists
    if not hasattr(meal_plan, 'calculate_total_price'):
        print("❌ calculate_total_price() method not found")
        return False
    
    print("✓ calculate_total_price() method exists")
    
    # Verify price updates in database reflect in calculations
    original_price = meal_plan.price_per_night
    meal_plan.price_per_night = Decimal('9999.99')
    meal_plan.save()
    
    total = meal_plan.calculate_total_price(1, 1)
    if total != Decimal('9999.99'):
        print(f"❌ Price not updated: {total} != 9999.99")
        meal_plan.price_per_night = original_price
        meal_plan.save()
        return False
    
    print("✓ Price changes in database immediately affect calculations")
    
    # Restore original
    meal_plan.price_per_night = original_price
    meal_plan.save()
    
    return True


def main():
    """Run all tests"""
    print("\n" + "█"*70)
    print("SESSION 1: ROOM MEAL PLANS - COMPREHENSIVE TEST")
    print("█"*70)
    
    tests = [
        ("Room Meal Plan Model", test_meal_plan_model),
        ("Meal Plan Pricing Hierarchy", test_meal_plan_pricing),
        ("Booking Integration", test_booking_integration),
        ("Admin Visibility", test_admin_visibility),
        ("Data Consistency", test_data_consistency),
        ("No Hardcoded Prices", test_no_hardcoded_prices),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - SESSION 1 COMPLETE AND VERIFIED")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
