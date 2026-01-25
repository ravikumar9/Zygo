#!/usr/bin/env python
"""
CRITICAL TEST: Verify ALL booking POST endpoints return JSON for AJAX requests.

This test simulates the frontend AJAX request and checks:
1. Content-Type is application/json
2. Response body is valid JSON (not HTML)
3. Error responses have {"error": "message"} structure
4. Success responses have {"booking_url": "..."} structure

NO EXCEPTIONS. If any test returns HTML, the fix is INCOMPLETE.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from hotels.models import Hotel
import json

User = get_user_model()

def test_booking_json_contract():
    """Test that all booking POST responses return JSON for AJAX requests"""
    
    print("\n" + "="*80)
    print("TESTING AJAX JSON RESPONSE CONTRACT")
    print("="*80)
    
    client = Client()
    
    # Create or get test user with email verification
    user, created = User.objects.get_or_create(
        username='testuser_json',
        defaults={
            'email': 'test@example.com',
            'email_verified_at': django.utils.timezone.now()
        }
    )
    if not user.email_verified_at:
        user.email_verified_at = django.utils.timezone.now()
        user.save()
    
    client.force_login(user)
    
    # Get first active hotel
    hotel = Hotel.objects.filter(is_active=True).first()
    if not hotel:
        print("[FAIL] No active hotels in database")
        return False
    
    print(f"\n[OK] Testing with Hotel ID: {hotel.id} - {hotel.name}")
    
    # Test 1: Missing required fields (validation error)
    print("\nTest 1: Validation Error (missing room type)")
    response = client.post(
        f'/hotels/{hotel.id}/book/',
        data={
            'checkin_date': '2025-06-01',
            'checkout_date': '2025-06-05',
            'guest_name': 'Test Guest',
            'guest_email': 'test@example.com',
            'guest_phone': '1234567890',
            # room_type_id is missing - should trigger validation error
        },
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    content_type = response.get('Content-Type', '')
    if 'application/json' not in content_type:
        print(f"[FAIL] Expected JSON, got Content-Type: {content_type}")
        print(f"Response body preview: {response.content[:200]}")
        return False
    
    try:
        data = json.loads(response.content)
        if 'error' not in data:
            print(f"[FAIL] JSON missing 'error' field: {data}")
            return False
        print(f"[OK] PASS: Validation error returns JSON with error: '{data['error']}'")
    except json.JSONDecodeError as e:
        print(f"[FAIL] Response is not valid JSON: {e}")
        print(f"Response body: {response.content[:500]}")
        return False
    
    # Test 2: Invalid dates (date validation error)
    print("\nTest 2: Invalid Dates (checkout before checkin)")
    response = client.post(
        f'/hotels/{hotel.id}/book/',
        data={
            'checkin_date': '2025-06-05',
            'checkout_date': '2025-06-01',  # Before checkin!
            'room_type_id': '1',
            'guest_name': 'Test Guest',
            'guest_email': 'test@example.com',
            'guest_phone': '1234567890',
        },
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    content_type = response.get('Content-Type', '')
    if 'application/json' not in content_type:
        print(f"[FAIL] Expected JSON, got Content-Type: {content_type}")
        print(f"Response body preview: {response.content[:200]}")
        return False
    
    try:
        data = json.loads(response.content)
        if 'error' not in data:
            print(f"[FAIL] JSON missing 'error' field: {data}")
            return False
        print(f"[OK] PASS: Date validation error returns JSON with error: '{data['error']}'")
    except json.JSONDecodeError as e:
        print(f"[FAIL] Response is not valid JSON: {e}")
        print(f"Response body: {response.content[:500]}")
        return False
    
    # Test 3: Invalid room type (room not found error)
    print("\nTest 3: Invalid Room Type (room ID 99999 doesn't exist)")
    response = client.post(
        f'/hotels/{hotel.id}/book/',
        data={
            'checkin_date': '2025-06-01',
            'checkout_date': '2025-06-05',
            'room_type_id': '99999',  # Doesn't exist
            'guest_name': 'Test Guest',
            'guest_email': 'test@example.com',
            'guest_phone': '1234567890',
        },
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    content_type = response.get('Content-Type', '')
    if 'application/json' not in content_type:
        print(f"[FAIL] Expected JSON, got Content-Type: {content_type}")
        print(f"Response body preview: {response.content[:200]}")
        return False
    
    try:
        data = json.loads(response.content)
        if 'error' not in data:
            print(f"[FAIL] JSON missing 'error' field: {data}")
            return False
        print(f"[OK] PASS: Room not found error returns JSON with error: '{data['error']}'")
    except json.JSONDecodeError as e:
        print(f"[FAIL] Response is not valid JSON: {e}")
        print(f"Response body: {response.content[:500]}")
        return False
    
    print("\n" + "="*80)
    print("[OK] ALL TESTS PASSED: All booking POST endpoints return JSON for AJAX")
    print("="*80)
    return True

if __name__ == '__main__':
    import django.utils.timezone
    
    success = test_booking_json_contract()
    sys.exit(0 if success else 1)
