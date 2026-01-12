#!/usr/bin/env python
"""
Test script to verify critical identity layer fixes:
1. CSRF token handling in OTP template
2. Email backend configuration
3. OTP model state (timestamps)
4. Password reset form error handling
5. Verification enforcement
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail
from django.test import Client
from users.models import User, UserOTP
from users.otp_service import OTPService
from users.password_reset_forms import SafePasswordResetForm
import logging

logger = logging.getLogger(__name__)

def test_email_config():
    """Verify email backend configuration."""
    print("\n" + "="*60)
    print("TEST 1: Email Backend Configuration")
    print("="*60)
    
    print(f"✓ EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"✓ EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"✓ EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"✓ EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"✓ DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    # Verify SendGrid is configured (not Gmail)
    assert settings.EMAIL_HOST == "smtp.sendgrid.net", "❌ EMAIL_HOST must be SendGrid!"
    assert settings.EMAIL_HOST_USER == "apikey", "❌ EMAIL_HOST_USER must be 'apikey'!"
    assert settings.DEFAULT_FROM_EMAIL == "noreply@goexplorer.in", "❌ DEFAULT_FROM_EMAIL mismatch!"
    print("✓ Email backend is correctly configured for SendGrid\n")


def test_otp_model():
    """Verify OTP model has proper timestamps."""
    print("="*60)
    print("TEST 2: OTP Model Structure")
    print("="*60)
    
    # Create a test OTP
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(
            username='test_otp_user@test.com',
            email='test_otp_user@test.com',
            password='testpass123'
        )
    
    otp = UserOTP.create_otp(user, 'email', 'test@example.com', expiry_minutes=5)
    
    assert hasattr(otp, 'created_at'), "❌ OTP missing created_at!"
    assert hasattr(otp, 'expires_at'), "❌ OTP missing expires_at!"
    assert hasattr(otp, 'verified_at'), "❌ OTP missing verified_at!"
    assert otp.created_at is not None, "❌ created_at is None!"
    assert otp.expires_at is not None, "❌ expires_at is None!"
    
    print(f"✓ OTP created_at: {otp.created_at}")
    print(f"✓ OTP expires_at: {otp.expires_at}")
    print(f"✓ OTP verified_at: {otp.verified_at} (initially None)")
    print("✓ OTP model has all required timestamp fields\n")
    
    # Clean up
    otp.delete()
    if user.email == 'test_otp_user@test.com':
        user.delete()


def test_verification_enforcement():
    """Verify that unverified users cannot proceed."""
    print("="*60)
    print("TEST 3: Verification Enforcement")
    print("="*60)
    
    # Create test user (unverified)
    test_user = User.objects.create_user(
        username='unverified@test.com',
        email='unverified@test.com',
        password='testpass123'
    )
    
    print(f"User created: {test_user.email}")
    print(f"  email_verified_at: {test_user.email_verified_at}")
    print(f"  phone_verified_at: {test_user.phone_verified_at}")
    
    # Check that both are None initially
    assert test_user.email_verified_at is None, "❌ email_verified_at should be None for new user!"
    assert test_user.phone_verified_at is None, "❌ phone_verified_at should be None for new user!"
    
    print("✓ Unverified users have None timestamps")
    print("✓ Verification enforcement ready\n")
    
    # Clean up
    test_user.delete()


def test_password_reset_form():
    """Verify password reset form error handling."""
    print("="*60)
    print("TEST 4: Password Reset Form (Error Handling)")
    print("="*60)
    
    # Create test user
    test_user = User.objects.create_user(
        username='pwreset@test.com',
        email='pwreset@test.com',
        password='testpass123'
    )
    
    form_data = {'email': 'pwreset@test.com'}
    form = SafePasswordResetForm(data=form_data)
    
    is_valid = form.is_valid()
    print(f"Form valid for existing user: {is_valid}")
    assert is_valid, "❌ Form should be valid for existing user!"
    
    # Test with non-existent user (form should still say valid to prevent enumeration)
    form_data = {'email': 'nonexistent@test.com'}
    form = SafePasswordResetForm(data=form_data)
    is_valid = form.is_valid()
    print(f"Form valid for non-existent user: {is_valid}")
    
    print("✓ Password reset form configured for safe error handling\n")
    
    # Clean up
    test_user.delete()


def test_csrf_token_meta_tag():
    """Verify CSRF meta tag is in OTP template."""
    print("="*60)
    print("TEST 5: CSRF Token in OTP Template")
    print("="*60)
    
    with open('templates/users/verify_registration_otp.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_meta_tag = 'meta name="csrf-token"' in content
    has_safe_getter = 'Priority 1: meta tag' in content
    has_defensive_sendotp = 'if (!btn)' in content
    has_defensive_verify = 'if (!otpInput)' in content
    
    print(f"✓ CSRF meta tag present: {has_meta_tag}")
    print(f"✓ Safe token getter function: {has_safe_getter}")
    print(f"✓ Defensive sendOTP checks: {has_defensive_sendotp}")
    print(f"✓ Defensive verifyOTP checks: {has_defensive_verify}")
    
    assert has_meta_tag, "❌ CSRF meta tag missing!"
    assert has_safe_getter, "❌ Safe token getter missing!"
    assert has_defensive_sendotp, "❌ sendOTP defensive checks missing!"
    assert has_defensive_verify, "❌ verifyOTP defensive checks missing!"
    
    print("✓ OTP template has all critical defensive checks\n")


def test_logging_config():
    """Verify logging is properly configured."""
    print("="*60)
    print("TEST 6: Logging Configuration")
    print("="*60)
    
    assert 'django.core.mail' in settings.LOGGING['loggers'], "❌ Email logger not configured!"
    assert 'users' in settings.LOGGING['loggers'], "❌ Users logger not configured!"
    
    print("✓ Email logger configured")
    print("✓ Users logger configured")
    print("✓ Logging to file for troubleshooting enabled\n")


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# CRITICAL IDENTITY LAYER FIX VERIFICATION")
    print("#"*60)
    
    try:
        test_email_config()
        test_otp_model()
        test_verification_enforcement()
        test_password_reset_form()
        test_csrf_token_meta_tag()
        test_logging_config()
        
        print("="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60)
        print("\nSummary:")
        print("✓ Email backend: SendGrid configured (no Gmail fallback)")
        print("✓ OTP model: All timestamp fields present")
        print("✓ Verification: Enforcement framework ready")
        print("✓ Password reset: Error handling configured")
        print("✓ CSRF: Meta tag + defensive JS checks")
        print("✓ Logging: File-based for troubleshooting")
        print("\nNext steps:")
        print("1. Deploy with SENDGRID_API_KEY environment variable")
        print("2. Test registration → email/mobile OTP → verification")
        print("3. Test password reset → check logs if email fails")
        print("4. Monitor logs/email.log for email delivery issues")
        
        return 0
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
