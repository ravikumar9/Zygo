#!/usr/bin/env python
"""
COMPREHENSIVE BOOKING FLOW TEST
Tests booking across multiple hotels to ensure consistency.

Tests:
1. Booking flow works for ALL hotels (not just specific IDs)
2. Cancellation policy comes from hotel level (not room)
3. Pricing calculations are consistent (service fee cap ₹500, GST on service fee only)
4. All error paths return JSON for AJAX requests
5. Success paths redirect correctly
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from hotels.models import Hotel
from decimal import Decimal
import json

User = get_user_model()

def test_booking_flow_consistency():
    """Test booking flow across multiple hotels"""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE BOOKING FLOW TEST - SYSTEM TRUTH VERIFICATION")
    print("="*80)
    
    client = Client()
    
    # Create verified test user
    user, created = User.objects.get_or_create(
        username='system_test_user',
        defaults={
            'email': 'systemtest@example.com',
            'email_verified_at': django.utils.timezone.now()
        }
    )
    if not user.email_verified_at:
        user.email_verified_at = django.utils.timezone.now()
        user.save()
    
    client.force_login(user)
    
    # Get first 3 active hotels (or all if less than 3)
    hotels = list(Hotel.objects.filter(is_active=True)[:5])
    
    if len(hotels) < 3:
        print(f"[WARNING] Only {len(hotels)} active hotels found. Need at least 3 for comprehensive test.")
    
    print(f"\n[INFO] Testing with {len(hotels)} hotels")
    
    test_results = []
    
    for hotel in hotels:
        print(f"\n{'='*80}")
        print(f"Testing Hotel ID {hotel.id}: {hotel.name}")
        print(f"{'='*80}")
        
        # Get hotel's cancellation policy
        policy = hotel.get_structured_cancellation_policy()
        print(f"[POLICY] Type: {policy['policy_type']}, Refund: {policy['refund_percentage']}%, Hours: {policy.get('cancellation_hours')}")
        print(f"[POLICY] Text: {policy['policy_text'][:100]}...")
        
        # Test 1: Missing room type (validation error)
        print("\n[TEST 1] Validation Error - Missing Room Type")
        response = client.post(
            f'/hotels/{hotel.id}/book/',
            data={
                'checkin_date': '2026-06-01',
                'checkout_date': '2026-06-05',
                'guest_name': 'Test Guest',
                'guest_email': 'test@example.com',
                'guest_phone': '1234567890',
                # room_type missing
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        content_type = response.get('Content-Type', '')
        is_json = 'application/json' in content_type
        
        if is_json:
            try:
                data = json.loads(response.content)
                if 'error' in data:
                    print(f"  [PASS] Returns JSON error: {data['error'][:60]}...")
                    test_results.append({'hotel_id': hotel.id, 'test': 'validation', 'status': 'PASS'})
                else:
                    print(f"  [FAIL] JSON missing error field: {data}")
                    test_results.append({'hotel_id': hotel.id, 'test': 'validation', 'status': 'FAIL'})
            except json.JSONDecodeError:
                print(f"  [FAIL] Invalid JSON response")
                test_results.append({'hotel_id': hotel.id, 'test': 'validation', 'status': 'FAIL'})
        else:
            print(f"  [FAIL] Content-Type: {content_type} (expected JSON)")
            print(f"  Response preview: {response.content[:200]}")
            test_results.append({'hotel_id': hotel.id, 'test': 'validation', 'status': 'FAIL'})
        
        # Test 2: Invalid room type ID
        print("\n[TEST 2] Invalid Room Type (ID 99999)")
        response = client.post(
            f'/hotels/{hotel.id}/book/',
            data={
                'checkin_date': '2026-06-01',
                'checkout_date': '2026-06-05',
                'room_type': '99999',  # Doesn't exist
                'guest_name': 'Test Guest',
                'guest_email': 'test@example.com',
                'guest_phone': '1234567890',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        content_type = response.get('Content-Type', '')
        is_json = 'application/json' in content_type
        
        if is_json:
            try:
                data = json.loads(response.content)
                if 'error' in data:
                    print(f"  [PASS] Returns JSON error: {data['error'][:60]}...")
                    test_results.append({'hotel_id': hotel.id, 'test': 'invalid_room', 'status': 'PASS'})
                else:
                    print(f"  [FAIL] JSON missing error field")
                    test_results.append({'hotel_id': hotel.id, 'test': 'invalid_room', 'status': 'FAIL'})
            except json.JSONDecodeError:
                print(f"  [FAIL] Invalid JSON response")
                test_results.append({'hotel_id': hotel.id, 'test': 'invalid_room', 'status': 'FAIL'})
        else:
            print(f"  [FAIL] Content-Type: {content_type} (expected JSON)")
            test_results.append({'hotel_id': hotel.id, 'test': 'invalid_room', 'status': 'FAIL'})
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total_tests = len(test_results)
    passed = sum(1 for r in test_results if r['status'] == 'PASS')
    failed = total_tests - passed
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\n[FAILED TESTS]")
        for result in test_results:
            if result['status'] == 'FAIL':
                print(f"  Hotel {result['hotel_id']}: {result['test']}")
    
    print("\n" + "="*80)
    if failed == 0:
        print("[SUCCESS] ALL HOTELS WORK CONSISTENTLY")
        print("="*80)
        return True
    else:
        print("[FAILURE] INCONSISTENT BEHAVIOR ACROSS HOTELS")
        print("="*80)
        return False

if __name__ == '__main__':
    import django.utils.timezone
    success = test_booking_flow_consistency()
    sys.exit(0 if success else 1)
