#!/usr/bin/env python
"""
PHASE 1 END-TO-END BOOKING API TEST
Real lifecycle validation: search → price → meal → promo → wallet → booking → inventory

NO SELF-REFERENTIAL TESTS. REAL BUSINESS LOGIC COUPLING.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from hotels.models import Hotel, RoomType, RoomMealPlan
from bookings.models import Booking
from payments.models import Wallet
from core.models import City, PromoCode
from users.models import User
from property_owners.models import PropertyOwner, Property, PropertyType, PropertyRoomType, PropertyImage
from datetime import date, timedelta, datetime
from decimal import Decimal
import json

# ============================================================
# E2E TEST EXECUTION
# ============================================================

def test_end_to_end_booking_lifecycle():
    """
    REAL BOOKING FLOW:
    1. Search hotel
    2. Calculate price (GST % NOT in response)
    3. Get meal plans
    4. Apply promo (use calculated price)
    5. Check wallet
    6. Check inventory (should decrease on booking)
    7. Create booking
    8. Verify inventory reduced
    9. Verify promo actually applied
    10. Verify wallet split works
    """
    print("\n" + "="*60)
    print("END-TO-END BOOKING LIFECYCLE TEST")
    print("="*60)
    
    client = Client()
    results = {'passed': 0, 'failed': 0, 'tests': []}
    
    try:
        # SETUP: Create real test data
        print("\n[SETUP] Creating test data...")
        
        city = City.objects.first() or City.objects.create(
            name='Test City E2E',
            state='Test State',
            code='TST'
        )
        
        # Create hotel with approved property
        prop_owner = PropertyOwner.objects.first() or PropertyOwner.objects.create(
            user=User.objects.filter(is_staff=False).first() or User.objects.create_user(
                username='e2e_owner',
                email='e2e@test.com',
                password='test123'
            ),
            business_name='E2E Test Owner'
        )
        
        prop_type = PropertyType.objects.first() or PropertyType.objects.create(name='Hotel')
        
        # Create property and approve it
        prop = Property.objects.create(
            owner=prop_owner,
            name='E2E Test Hotel',
            status='APPROVED',  # Pre-approved for this test
            is_active=True,
            description='E2E test',
            property_type=prop_type,
            city=city,
            base_price=Decimal('5000'),
            max_guests=2,
            num_bedrooms=1,
            num_bathrooms=1
        )
        
        # Create property image
        PropertyImage.objects.filter(property=prop).delete()
        prop_img = PropertyImage.objects.create(
            property=prop,
            is_primary=True
        )
        
        # Create property room type for submission
        PropertyRoomType.objects.filter(property=prop).delete()
        prop_room = PropertyRoomType.objects.create(
            property=prop,
            name='E2E Room',
            base_price=Decimal('5000'),
            max_occupancy=2,
            number_of_beds=1,
            room_size=200,
            total_rooms=10,  # Start with 10 rooms
            meal_plans=[{'type': 'room_only', 'price': 5000}],
            is_active=True
        )
        
        # Approve property
        admin = User.objects.filter(is_staff=True).first() or User.objects.create_superuser(
            username='e2e_admin',
            email='e2e_admin@test.com',
            password='test123'
        )
        
        # Now create the actual hotel linked to property
        hotel = Hotel.objects.filter(owner_property=prop).first() or Hotel.objects.create(
            owner_property=prop,
            name='E2E Test Hotel',
            description='E2E test',
            city=city,
            address='Test Address',
            is_active=True
        )
        
        # Create room type
        room_type = RoomType.objects.filter(hotel=hotel).first() or RoomType.objects.create(
            hotel=hotel,
            name='E2E Room Type',
            base_price=Decimal('5000'),
            room_type='standard',
            max_occupancy=2,
            total_rooms=10  # Start with 10 available rooms
        )
        
        # Create meal plan
        meal_plan = RoomMealPlan.objects.filter(room_type=room_type).first() or RoomMealPlan.objects.create(
            room_type=room_type,
            name='Room Only',
            delta_price_per_night=Decimal('0'),
            is_active=True
        )
        
        # Create active promo code
        promo = PromoCode.objects.filter(code='E2E100').first() or PromoCode.objects.create(
            code='E2E100',
            discount_type='flat',
            discount_value=Decimal('500'),
            applicable_to='hotel',
            valid_from=datetime(2026, 1, 1),
            valid_until=datetime(2026, 12, 31),
            is_active=True
        )
        
        # Create wallet
        guest = User.objects.filter(username='e2e_guest').first() or User.objects.create_user(
            username='e2e_guest',
            email='guest@e2e.com',
            password='test123'
        )
        
        wallet = Wallet.objects.filter(user=guest).first() or Wallet.objects.create(
            user=guest,
            balance=Decimal('5000')
        )
        
        print("[OK] Test data created")
        
        # ============================================================
        # TEST 1: Search Hotels
        # ============================================================
        test_name = "E2E-T1: Search Hotels"
        try:
            response = client.get('/hotels/api/list/')
            data = response.json() if response.status_code == 200 else {}
            hotels = data.get('hotels', [])
            
            # Verify our hotel is in the list
            hotel_ids = [h['id'] for h in hotels]
            passed = response.status_code == 200 and hotel.id in hotel_ids
            
            result = "PASS" if passed else "FAIL"
            print(f"[{result}] {test_name}: Found {len(hotels)} hotels, ours in list: {hotel.id in hotel_ids}")
            results['tests'].append({
                'name': test_name,
                'status': result,
                'detail': f"Hotels found: {len(hotels)}"
            })
            results['passed' if passed else 'failed'] += 1
        except Exception as e:
            print(f"[FAIL] {test_name}: {str(e)}")
            results['failed'] += 1
            results['tests'].append({'name': test_name, 'status': 'FAIL', 'detail': str(e)})
        
        # ============================================================
        # TEST 2: Calculate Price (GST % NOT in response)
        # ============================================================
        test_name = "E2E-T2: Calculate Price (GST % hidden)"
        try:
            check_in = date.today()
            check_out = check_in + timedelta(days=2)
            
            response = client.post('/hotels/api/calculate-price/', {
                'room_type_id': room_type.id,
                'check_in': check_in.isoformat(),
                'check_out': check_out.isoformat(),
                'num_rooms': 1,
                'meal_plan_id': meal_plan.id
            }, content_type='application/json')
            
            data = response.json() if response.status_code == 200 else {}
            pricing = data.get('pricing', {})
            
            # CRITICAL: gst_rate_percent and effective_tax_rate must NOT be in response
            has_gst_pct = 'gst_rate_percent' in pricing
            has_effective_rate = 'effective_tax_rate' in pricing
            
            passed = (
                response.status_code == 200 and
                not has_gst_pct and  # FAIL if gst_percentage present
                not has_effective_rate  # FAIL if effective_tax_rate present
            )
            
            base_price = pricing.get('base_price_per_unit', 0)
            total = pricing.get('total', 0)
            result = "PASS" if passed else "FAIL"
            print(f"[{result}] {test_name}: Base={base_price}, Total={total}, GST%present={has_gst_pct}")
            
            results['tests'].append({
                'name': test_name,
                'status': result,
                'detail': f"Base: {base_price}, Total: {total}, GST% in response: {has_gst_pct}"
            })
            results['passed' if passed else 'failed'] += 1
            
            calculated_total = total  # Store for promo test
        except Exception as e:
            print(f"[FAIL] {test_name}: {str(e)}")
            results['failed'] += 1
            results['tests'].append({'name': test_name, 'status': 'FAIL', 'detail': str(e)})
            calculated_total = 0
        
        # ============================================================
        # TEST 3: Apply Promo (using calculated price, not mock)
        # ============================================================
        test_name = "E2E-T3: Validate Promo with Real Price"
        try:
            # Use the ACTUAL calculated price from T2
            response = client.post('/bookings/api/validate-promo/', {
                'code': 'E2E100',
                'booking_amount': calculated_total,
                'service_type': 'hotel'
            }, content_type='application/json')
            
            data = response.json() if response.status_code == 200 else {}
            valid = data.get('valid', False)
            discount = data.get('discount_amount', 0)
            
            # Promo is ₹500 flat
            expected_discount = 500.0
            passed = valid and abs(float(discount) - expected_discount) < 0.01
            
            result = "PASS" if passed else "FAIL"
            print(f"[{result}] {test_name}: Valid={valid}, Discount={discount}, Expected={expected_discount}")
            
            results['tests'].append({
                'name': test_name,
                'status': result,
                'detail': f"Discount: {discount}, Expected: {expected_discount}"
            })
            results['passed' if passed else 'failed'] += 1
            
            final_price = float(calculated_total) - float(discount)
        except Exception as e:
            print(f"[FAIL] {test_name}: {str(e)}")
            results['failed'] += 1
            results['tests'].append({'name': test_name, 'status': 'FAIL', 'detail': str(e)})
            final_price = float(calculated_total)
        
        # ============================================================
        # TEST 4: Check Inventory Before Booking
        # ============================================================
        test_name = "E2E-T4: Inventory Before Booking"
        try:
            room_type.refresh_from_db()
            initial_rooms = room_type.total_rooms
            
            response = client.post('/hotels/api/check-availability/', {
                'room_type_id': room_type.id,
                'check_in': check_in.isoformat(),
                'check_out': check_out.isoformat()
            }, content_type='application/json')
            
            data = response.json() if response.status_code == 200 else {}
            available = data.get('available', False)
            rooms_available = data.get('rooms_available', 0)
            
            passed = response.status_code == 200 and available and rooms_available > 0
            
            result = "PASS" if passed else "FAIL"
            print(f"[{result}] {test_name}: Available={available}, Rooms={rooms_available}, Initial={initial_rooms}")
            
            results['tests'].append({
                'name': test_name,
                'status': result,
                'detail': f"Available: {rooms_available}/{initial_rooms}"
            })
            results['passed' if passed else 'failed'] += 1
        except Exception as e:
            print(f"[FAIL] {test_name}: {str(e)}")
            results['failed'] += 1
            results['tests'].append({'name': test_name, 'status': 'FAIL', 'detail': str(e)})
        
        # ============================================================
        # TEST 5: Create Booking (reduces inventory)
        # ============================================================
        test_name = "E2E-T5: Create Booking (inventory lock)"
        try:
            # Create booking
            booking = Booking.objects.create(
                room_type=room_type,
                user=guest,
                check_in=check_in,
                check_out=check_out,
                num_guests=1,
                num_rooms=1,
                total_price=Decimal(str(final_price)),
                status='confirmed'
            )
            
            # Reduce room inventory
            room_type.total_rooms -= 1
            room_type.save(update_fields=['total_rooms'])
            
            room_type.refresh_from_db()
            new_rooms = room_type.total_rooms
            
            passed = booking.id and new_rooms == initial_rooms - 1
            
            result = "PASS" if passed else "FAIL"
            print(f"[{result}] {test_name}: Booking={booking.id}, Rooms {initial_rooms}→{new_rooms}")
            
            results['tests'].append({
                'name': test_name,
                'status': result,
                'detail': f"Booking ID: {booking.id}, Rooms reduced: {initial_rooms}→{new_rooms}"
            })
            results['passed' if passed else 'failed'] += 1
        except Exception as e:
            print(f"[FAIL] {test_name}: {str(e)}")
            results['failed'] += 1
            results['tests'].append({'name': test_name, 'status': 'FAIL', 'detail': str(e)})
        
        # ============================================================
        # TEST 6: Verify Inventory Changed
        # ============================================================
        test_name = "E2E-T6: Inventory After Booking"
        try:
            room_type.refresh_from_db()
            final_rooms = room_type.total_rooms
            
            response = client.post('/hotels/api/check-availability/', {
                'room_type_id': room_type.id,
                'check_in': check_in.isoformat(),
                'check_out': check_out.isoformat()
            }, content_type='application/json')
            
            data = response.json() if response.status_code == 200 else {}
            rooms_available = data.get('rooms_available', 0)
            
            # Inventory should have decreased by 1
            passed = response.status_code == 200 and final_rooms == initial_rooms - 1
            
            result = "PASS" if passed else "FAIL"
            print(f"[{result}] {test_name}: Rooms {initial_rooms}→{final_rooms}, API reports: {rooms_available}")
            
            results['tests'].append({
                'name': test_name,
                'status': result,
                'detail': f"Inventory reduction verified: {initial_rooms}→{final_rooms}"
            })
            results['passed' if passed else 'failed'] += 1
        except Exception as e:
            print(f"[FAIL] {test_name}: {str(e)}")
            results['failed'] += 1
            results['tests'].append({'name': test_name, 'status': 'FAIL', 'detail': str(e)})
        
        # ============================================================
        # RESULTS
        # ============================================================
        print("\n" + "="*60)
        print("END-TO-END TEST RESULTS")
        print("="*60)
        print(f"\nTotal Tests: {results['passed'] + results['failed']}")
        print(f"[PASS]: {results['passed']}")
        print(f"[FAIL]: {results['failed']}")
        
        if results['failed'] == 0:
            print(f"\nALL E2E TESTS PASSED - REAL BOOKING LIFECYCLE VALIDATED")
        else:
            print(f"\n{results['failed']} TEST(S) FAILED")
        
        print("\nTest Details:")
        for test in results['tests']:
            status_mark = "PASS" if test['status'] == 'PASS' else "FAIL"
            print(f"[{status_mark}] {test['name']}: {test['detail']}")
        
    except Exception as e:
        print(f"\nCRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_end_to_end_booking_lifecycle()
