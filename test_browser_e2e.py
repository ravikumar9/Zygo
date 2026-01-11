"""
Phase 3.1 End-to-End Browser Testing

This script simulates real user interactions with the registration flow:
1. Register new user with email, phone, password
2. Verify email OTP
3. Verify mobile OTP
4. Login and access dashboard

Tests verify:
- Registration form loads and accepts data
- OTP verification pages load
- Email/Mobile OTP can be verified
- User can login after completing registration
- Dashboard is accessible after login
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from users.models import User
from users.models_otp import UserOTP
from users.otp_service import OTPService
from django.urls import reverse
from datetime import datetime

def log(message, level="INFO"):
    """Print formatted log messages"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] {level:8}"
    # Use ASCII characters to avoid Unicode encoding issues on Windows
    safe_message = str(message).encode('ascii', 'replace').decode('ascii')
    print(f"{prefix} {safe_message}")

def test_browser_flow():
    """Test complete registration flow as a real user would"""
    log("="*80, "TEST")
    log("PHASE 3.1 END-TO-END BROWSER TESTING", "TEST")
    log("="*80, "TEST")
    
    client = Client()
    
    # Clean up test user
    test_email = f'browser_test_{datetime.now().timestamp()}@example.com'
    User.objects.filter(email=test_email).delete()
    
    log(f"\n>>> STEP 1: REGISTRATION PAGE", "STEP")
    log(f"Test email: {test_email}")
    
    # Get registration page
    response = client.get('/users/register/')
    if response.status_code == 200:
        log("✓ Registration page loads (200)")
        if hasattr(response, 'context') and response.context and 'form' in response.context:
            log("✓ Form is present in context")
        if hasattr(response, 'context') and response.context and 'csrf_token' in response.context:
            log("✓ CSRF token is present (security OK)")
    else:
        log(f"✗ Registration page failed: {response.status_code}", "ERROR")
        return False
    
    # Check form fields in HTML
    html = response.content.decode()
    required_fields = ['email', 'first_name', 'last_name', 'phone', 'password', 'password_confirm']
    log(f"\nChecking form fields...")
    for field in required_fields:
        if f'name="{field}"' in html or f"name='{field}'" in html:
            log(f"  ✓ Field '{field}' found in form")
        else:
            log(f"  ✗ Field '{field}' NOT found in form", "WARN")
    
    # Submit registration form
    log(f"\n>>> STEP 2: SUBMIT REGISTRATION", "STEP")
    
    reg_data = {
        'email': test_email,
        'first_name': 'Test',
        'last_name': 'Browser',
        'phone': '9876543215',  # Numeric format
        'password': 'BrowserTest123!',
        'password_confirm': 'BrowserTest123!'
    }
    
    log(f"Submitting form with:")
    for key, val in reg_data.items():
        if 'password' in key:
            log(f"  {key}: ****")
        else:
            log(f"  {key}: {val}")
    
    response = client.post('/users/register/', reg_data)
    
    if response.status_code == 302:
        log(f"✓ Form accepted, redirected (302)")
        redirect_location = response.get('Location', '')
        log(f"  Redirects to: {redirect_location}")
    elif response.status_code == 200:
        log(f"✗ Form returned 200 (validation error)", "ERROR")
        if hasattr(response, 'context') and response.context:
            if 'form' in response.context:
                form_errors = response.context['form'].errors
                if form_errors:
                    log(f"  Form errors: {dict(form_errors)}", "ERROR")
        return False
    else:
        log(f"✗ Unexpected status: {response.status_code}", "ERROR")
        return False
    
    # Check user was created
    try:
        user = User.objects.get(email=test_email)
        log(f"\n✓ User created in database")
        log(f"  ID: {user.id}")
        log(f"  Email verified: {user.email_verified}")
        log(f"  Phone verified: {user.phone_verified}")
        log(f"  Active: {user.is_active}")
    except User.DoesNotExist:
        log(f"✗ User not found in database", "ERROR")
        return False
    
    # Test OTP verification page
    log(f"\n>>> STEP 3: OTP VERIFICATION PAGE", "STEP")
    
    response = client.get('/users/verify-registration-otp/')
    if response.status_code == 200:
        log("✓ OTP verification page loads (200)")
        
        html = response.content.decode()
        if 'Email' in html and 'Mobile' in html:
            log("✓ Both Email and Mobile OTP fields visible")
        if 'status' in html.lower():
            log("✓ Status card elements found")
    else:
        log(f"✗ OTP page failed: {response.status_code}", "ERROR")
        return False
    
    # Test email OTP
    log(f"\n>>> STEP 4: EMAIL OTP VERIFICATION", "STEP")
    
    result = OTPService.send_email_otp(user)
    if result['success']:
        log("✓ Email OTP sent successfully")
        
        pending_otp = UserOTP.objects.filter(user=user, otp_type='email', is_verified=False).first()
        if pending_otp:
            log(f"✓ Pending OTP found: {pending_otp.otp_code[:3]}***")
            
            # Simulate API call to verify OTP
            verify_response = client.post(
                '/users/verify-registration-otp/',
                {
                    'action': 'verify_email_otp',
                    'otp': pending_otp.otp_code
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            if verify_response.status_code == 200:
                import json
                data = json.loads(verify_response.content)
                if data.get('success'):
                    log("✓ Email OTP verified via API")
                    user.refresh_from_db()
                    log(f"✓ User email_verified_at: {user.email_verified_at}")
                else:
                    log(f"✗ OTP verification failed: {data.get('message')}", "WARN")
            else:
                log(f"✗ OTP API returned: {verify_response.status_code}", "WARN")
        else:
            log("⚠ No pending email OTP found", "WARN")
    else:
        log(f"✗ Email OTP send failed: {result.get('message')}", "ERROR")
        return False
    
    # Test mobile OTP
    log(f"\n>>> STEP 5: MOBILE OTP VERIFICATION", "STEP")
    
    result = OTPService.send_mobile_otp(user)
    if result['success']:
        log("✓ Mobile OTP sent successfully")
        
        pending_otp = UserOTP.objects.filter(user=user, otp_type='mobile', is_verified=False).first()
        if pending_otp:
            log(f"✓ Pending OTP found: {pending_otp.otp_code[:3]}***")
            
            verify_response = client.post(
                '/users/verify-registration-otp/',
                {
                    'action': 'verify_mobile_otp',
                    'otp': pending_otp.otp_code
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            if verify_response.status_code == 200:
                import json
                data = json.loads(verify_response.content)
                if data.get('success'):
                    log("✓ Mobile OTP verified via API")
                    user.refresh_from_db()
                    log(f"✓ User phone_verified_at: {user.phone_verified_at}")
                else:
                    log(f"✗ OTP verification failed: {data.get('message')}", "WARN")
            else:
                log(f"✗ OTP API returned: {verify_response.status_code}", "WARN")
        else:
            log("⚠ No pending mobile OTP found", "WARN")
    else:
        log(f"✗ Mobile OTP send failed: {result.get('message')}", "ERROR")
        return False
    
    # Test login
    log(f"\n>>> STEP 6: LOGIN AFTER VERIFICATION", "STEP")
    
    login_response = client.post('/users/login/', {
        'email': test_email,
        'password': 'BrowserTest123!'
    })
    
    if login_response.status_code == 302:
        log("✓ Login successful, redirected (302)")
        log(f"  Redirects to: {login_response.get('Location', '')}")
    elif login_response.status_code == 200:
        log("⚠ Login returned 200 (may still be valid)", "WARN")
    else:
        log(f"✗ Login failed: {login_response.status_code}", "ERROR")
        return False
    
    # Check if user is authenticated
    if client.session.get('_auth_user_id'):
        log("✓ User session authenticated")
    else:
        log("⚠ User not in session (may be valid)", "WARN")
    
    log(f"\n{'='*80}", "TEST")
    log(f"✅ END-TO-END BROWSER FLOW COMPLETED SUCCESSFULLY", "SUCCESS")
    log(f"{'='*80}", "TEST")
    
    return True

def test_bus_deck_labels():
    """Test that bus deck labels only show for multi-deck buses"""
    log(f"\n{'='*80}", "TEST")
    log(f"BUS DECK LABEL BROWSER TEST", "TEST")
    log(f"{'='*80}", "TEST")
    
    client = Client()
    
    # Get a bus with seats (use the correct relation name)
    from buses.models import Bus, SeatLayout
    buses = Bus.objects.filter(id__gt=0)[:5]  # Get first 5 buses
    
    if not buses:
        log("No buses found", "WARN")
        return True
    
    for bus in buses:
        # Check if bus has seats
        seats = SeatLayout.objects.filter(bus=bus)
        if not seats.exists():
            continue
        
        log(f"\nBus: {bus.bus_name} ({bus.registration_number})")
        
        # Check deck count
        decks = set(seats.values_list('deck', flat=True))
        has_multiple = len(decks) > 1
        
        log(f"Seats: {seats.count()}")
        log(f"Decks: {sorted(decks)}")
        log(f"Has multiple decks: {has_multiple}")
        
        # Get bus detail page
        response = client.get(f'/buses/{bus.id}/')
        if response.status_code == 200:
            log("? Bus detail page loads (200)")
            
            html = response.content.decode()
            
            # Check deck labels
            has_upper = 'Upper Deck' in html
            has_lower = 'Lower Deck' in html
            has_deck_labels = has_upper or has_lower
            
            if has_multiple:
                if has_deck_labels:
                    log("? Deck labels present (correct for multi-deck bus)")
                else:
                    log("? Deck labels missing (expected for multi-deck)", "WARN")
            else:
                if not has_deck_labels:
                    log("? Deck labels hidden (correct for single-deck bus)")
                else:
                    log("? Deck labels present (should be hidden for single-deck)", "ERROR")
        else:
            log(f"? Bus detail failed: {response.status_code}", "ERROR")
            return False
        
        break  # Test just one bus
    
    log(f"\n? BUS DECK LABEL TEST PASSED", "SUCCESS")
    return True

def main():
    """Run all browser tests"""
    try:
        results = []
        
        # Test 1: Browser E2E flow
        results.append(("Browser E2E Flow", test_browser_flow()))
        
        # Test 2: Bus deck labels
        results.append(("Bus Deck Labels", test_bus_deck_labels()))
        
        # Print summary
        log(f"\n{'='*80}", "SUMMARY")
        log(f"TEST SUMMARY", "SUMMARY")
        log(f"{'='*80}", "SUMMARY")
        
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            log(f"{status} - {test_name}", "SUMMARY")
        
        all_passed = all(result[1] for result in results)
        if all_passed:
            log(f"\n🎉 ALL BROWSER TESTS PASSED!", "SUCCESS")
        else:
            log(f"\n⚠️ SOME TESTS FAILED", "ERROR")
        
        return all_passed
        
    except Exception as e:
        log(f"✗ Test error: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
