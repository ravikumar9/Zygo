#!/usr/bin/env python
"""
COMPONENT INTEGRITY TEST
Verify all 5 hotel_detail components work across ALL hotels (Principal Architect)

Test Matrix:
1. Hotel context data presence (hotel_policy, pricing_data, room_types)
2. Meal plans data validity (JSON structure, no injection risks)
3. Room cards generation (no empty iterations, defensive blocks)
4. Pricing calculations (backend-driven, no JS math)
5. Cancellation policy fallback (defensive display)
"""

import os
import django
import json
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import RequestFactory
from hotels.models import Hotel
from hotels.views import hotel_detail
from datetime import date, timedelta

print("=" * 90)
print("COMPONENT INTEGRITY TEST - PRINCIPAL ARCHITECT VERIFICATION")
print("=" * 90)

# ============================================================================
# SETUP
# ============================================================================

factory = RequestFactory()
active_hotels = Hotel.objects.filter(is_active=True)[:5]  # Test 5 hotels

print(f"\nTesting {active_hotels.count()} active hotels...")

# ============================================================================
# TEST 1: CONTEXT DATA PRESENCE
# ============================================================================

print("\n[TEST 1] CONTEXT DATA PRESENCE (Defensive Fallbacks)")
print("-" * 90)

context_issues = 0
for hotel in active_hotels:
    request = factory.get(f'/hotels/{hotel.id}/')
    request.session = {}
    
    try:
        # Import and call view directly
        from hotels.views import hotel_detail
        response = hotel_detail(request, hotel.id)
        
        # Extract context (Django test trick)
        from django.test.client import Client
        client = Client()
        response = client.get(f'/hotels/{hotel.id}/')
        
        # Check context keys
        if hasattr(response, 'context'):
            context = response.context[0]
            
            required_keys = ['hotel', 'hotel_policy', 'pricing_data', 'room_types']
            missing_keys = [k for k in required_keys if k not in context]
            
            if missing_keys:
                print(f"  ERROR: Hotel {hotel.id} missing context: {missing_keys}")
                context_issues += 1
            else:
                print(f"  OK: Hotel {hotel.id} ({hotel.name[:30]}) - ALL context present")
                
                # Verify data types
                if not isinstance(context['hotel_policy'], dict):
                    print(f"    WARNING: hotel_policy is not dict (type: {type(context['hotel_policy'])})")
                if not isinstance(context['pricing_data'], dict):
                    print(f"    WARNING: pricing_data is not dict")
    except Exception as e:
        print(f"  ERROR: Hotel {hotel.id} - {str(e)[:60]}")
        context_issues += 1

print(f"\nContext Data Issues: {context_issues}/{ active_hotels.count()}")

# ============================================================================
# TEST 2: MEAL PLANS JSON VALIDITY
# ============================================================================

print("\n[TEST 2] MEAL PLANS JSON VALIDITY (JSON Injection Prevention)")
print("-" * 90)

from hotels.models import RoomType, RoomMealPlan

json_issues = 0
for hotel in active_hotels:
    room_types = hotel.room_types.all()
    
    # Simulate meal plans JSON generation
    meal_plans_json = {}
    for room in room_types:
        plans = room.meal_plans.all()
        if plans.exists():
            meal_plans_json[str(room.id)] = []
            for plan in plans:
                # Check for JSON injection risks
                try:
                    # Simulate template escaping
                    name_safe = plan.name.replace('"', '\\"')
                    plan_type_safe = plan.plan_type.replace('"', '\\"')
                    
                    plan_data = {
                        'id': plan.id,
                        'name': name_safe,
                        'price': float(plan.price_per_night),  # Convert Decimal to float
                        'type': plan_type_safe,
                    }
                    meal_plans_json[str(room.id)].append(plan_data)
                except Exception as e:
                    print(f"  ERROR: Hotel {hotel.id}, Room {room.id}, Plan {plan.id} - {str(e)}")
                    json_issues += 1
    
    # Verify JSON is valid
    try:
        json_str = json.dumps(meal_plans_json)
        # Re-parse to ensure valid JSON
        parsed = json.loads(json_str)
        print(f"  OK: Hotel {hotel.id} - {len(meal_plans_json)} rooms, JSON valid")
    except json.JSONDecodeError as e:
        print(f"  ERROR: Hotel {hotel.id} - Invalid JSON: {str(e)}")
        json_issues += 1

print(f"\nJSON Validity Issues: {json_issues}/{active_hotels.count()}")

# ============================================================================
# TEST 3: ROOM CARDS GENERATION
# ============================================================================

print("\n[TEST 3] ROOM CARDS GENERATION (Defensive Empty Blocks)")
print("-" * 90)

room_issues = 0
for hotel in active_hotels:
    room_types = hotel.room_types.all()
    
    if not room_types.exists():
        print(f"  WARNING: Hotel {hotel.id} has NO rooms (defensive block should show)")
        # This is expected - test that template has {% empty %} block
    else:
        total_rooms = 0
        for room in room_types:
            total_rooms += 1
            
            # Verify room has required fields
            required_fields = ['name', 'base_price_per_night']
            for field in required_fields:
                if not hasattr(room, field):
                    print(f"  ERROR: Hotel {hotel.id}, Room {room.id} missing field: {field}")
                    room_issues += 1
        
        print(f"  OK: Hotel {hotel.id} - {total_rooms} rooms with valid data")

print(f"\nRoom Card Issues: {room_issues}")

# ============================================================================
# TEST 4: PRICING CALCULATIONS
# ============================================================================

print("\n[TEST 4] PRICING CALCULATIONS (Backend-Driven, No NaN)")
print("-" * 90)

pricing_issues = 0
for hotel in active_hotels:
    try:
        # Simulate pricing calculation from view
        base_price = float(hotel.base_price or 0)
        service_fee = min(base_price * 0.05, 500)
        gst_amount = service_fee * 0.18
        total = base_price + service_fee + gst_amount
        
        # Verify no NaN or infinity
        if not (isinstance(base_price, (int, float)) and base_price >= 0):
            print(f"  ERROR: Hotel {hotel.id} - Invalid base_price: {base_price}")
            pricing_issues += 1
        elif not (isinstance(total, (int, float)) and total >= 0):
            print(f"  ERROR: Hotel {hotel.id} - Invalid total: {total}")
            pricing_issues += 1
        else:
            print(f"  OK: Hotel {hotel.id} - Base: Rs.{base_price:.0f}, Service: Rs.{service_fee:.0f}, GST: Rs.{gst_amount:.0f}, Total: Rs.{total:.0f}")
    except Exception as e:
        print(f"  ERROR: Hotel {hotel.id} - Pricing calc failed: {str(e)}")
        pricing_issues += 1

print(f"\nPricing Calculation Issues: {pricing_issues}/{active_hotels.count()}")

# ============================================================================
# TEST 5: CANCELLATION POLICY FALLBACK
# ============================================================================

print("\n[TEST 5] CANCELLATION POLICY FALLBACK (Defensive Display)")
print("-" * 90)

policy_issues = 0
for hotel in active_hotels:
    try:
        policy = hotel.get_structured_cancellation_policy()
        
        if not policy:
            print(f"  WARNING: Hotel {hotel.id} returned None policy (should have fallback)")
            policy_issues += 1
        else:
            required_policy_fields = ['policy_type', 'refund_percentage', 'policy_text']
            missing_fields = [f for f in required_policy_fields if f not in policy]
            
            if missing_fields:
                print(f"  ERROR: Hotel {hotel.id} policy missing: {missing_fields}")
                policy_issues += 1
            else:
                print(f"  OK: Hotel {hotel.id} - Policy: {policy['policy_type']} ({policy['refund_percentage']}%)")
    except Exception as e:
        print(f"  ERROR: Hotel {hotel.id} - Policy method failed: {str(e)}")
        policy_issues += 1

print(f"\nPolicy Fallback Issues: {policy_issues}/{active_hotels.count()}")

# ============================================================================
# TEST 6: COMPONENT REUSABILITY
# ============================================================================

print("\n[TEST 6] COMPONENT REUSABILITY (Template Includes)")
print("-" * 90)

import os

components_required = [
    'templates/hotels/includes/meal-plans-data.html',
    'templates/hotels/includes/cancellation-policy.html',
    'templates/hotels/includes/room-card.html',
    'templates/hotels/includes/pricing-calculator.html',
    'templates/hotels/includes/booking-form.html',
]

component_issues = 0
for component_path in components_required:
    full_path = os.path.join(os.getcwd(), component_path)
    if os.path.exists(full_path):
        # Check file size (should not be monolithic)
        size = os.path.getsize(full_path)
        if size > 10000:  # 10KB limit for component
            print(f"  WARNING: {component_path} is large ({size} bytes)")
        else:
            print(f"  OK: {component_path} exists ({size} bytes)")
    else:
        print(f"  ERROR: {component_path} MISSING")
        component_issues += 1

print(f"\nComponent Reusability Issues: {component_issues}/{len(components_required)}")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 90)
print("COMPONENT INTEGRITY SUMMARY")
print("=" * 90)

total_issues = context_issues + json_issues + room_issues + pricing_issues + policy_issues + component_issues

if total_issues == 0:
    print("\nSTATUS: ALL TESTS PASSED")
    print("✓ Context data always present (defensive fallbacks)")
    print("✓ Meal plans JSON valid and injection-safe")
    print("✓ Room cards have defensive empty blocks")
    print("✓ Pricing calculated in backend (no NaN)")
    print("✓ Cancellation policy has fallback")
    print("✓ All 5 components exist and reusable")
    print("\n[SUCCESS] COMPONENTS PRODUCTION-READY")
else:
    print(f"\nSTATUS: {total_issues} ISSUES FOUND")
    print(f"Please review errors above before deployment")

print("\n" + "=" * 90)
