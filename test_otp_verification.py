"""
OTP Verification Test Script
Tests email and mobile OTP send/verify flows locally
"""
import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.otp_service import OTPService
from users.models_otp import UserOTP
import time

User = get_user_model()


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_success(text):
    print(f"✓ {text}")


def print_error(text):
    print(f"✗ {text}")


def print_info(text):
    print(f"ℹ {text}")


class OTPTester:
    def __init__(self):
        self.user = None
        self.test_results = []
    
    def setup_test_user(self):
        """Create or get test user"""
        print_header("Setting up test user")
        
        email = "test_otp@goexplorer.com"
        phone = "919876543210"
        
        # Clean up existing test user
        User.objects.filter(email=email).delete()
        
        # Create new test user
        self.user = User.objects.create_user(
            username=email,
            email=email,
            password="test123",
            first_name="Test",
            last_name="User",
            phone=phone
        )
        
        print_success(f"Created test user: {self.user.email}")
        print_success(f"Phone: {self.user.phone}")
        return True
    
    def test_send_email_otp(self):
        """Test sending email OTP"""
        print_header("Test 1: Send Email OTP")
        
        result = OTPService.send_email_otp(self.user)
        
        if result['success']:
            print_success(f"Email OTP sent: {result['message']}")
            
            # Check OTP was created
            otp = UserOTP.objects.filter(
                user=self.user,
                otp_type='email'
            ).order_by('-created_at').first()
            
            if otp:
                print_info(f"OTP Code: {otp.otp_code} (check your email)")
                print_info(f"Expires at: {otp.expires_at}")
                self.test_results.append(("Send Email OTP", True))
                return otp.otp_code
            else:
                print_error("OTP record not found in database")
                self.test_results.append(("Send Email OTP", False))
                return None
        else:
            print_error(f"Failed to send email OTP: {result['message']}")
            self.test_results.append(("Send Email OTP", False))
            return None
    
    def test_verify_email_otp(self, otp_code):
        """Test verifying email OTP"""
        print_header("Test 2: Verify Email OTP")
        
        # Test with wrong OTP first
        result = OTPService.verify_email_otp(self.user, "000000")
        if not result['success']:
            print_success(f"Wrong OTP rejected: {result['message']}")
        else:
            print_error("Wrong OTP was accepted!")
        
        # Test with correct OTP
        result = OTPService.verify_email_otp(self.user, otp_code)
        
        if result['success']:
            print_success(f"Email OTP verified: {result['message']}")
            
            # Check user verification status
            self.user.refresh_from_db()
            if self.user.email_verified:
                print_success("User email_verified flag set to True")
                print_info(f"Verified at: {self.user.email_verified_at}")
                self.test_results.append(("Verify Email OTP", True))
                return True
            else:
                print_error("User email_verified flag not set")
                self.test_results.append(("Verify Email OTP", False))
                return False
        else:
            print_error(f"Failed to verify email OTP: {result['message']}")
            self.test_results.append(("Verify Email OTP", False))
            return False
    
    def test_send_mobile_otp(self):
        """Test sending mobile OTP"""
        print_header("Test 3: Send Mobile OTP")
        
        result = OTPService.send_mobile_otp(self.user)
        
        if result['success']:
            print_success(f"Mobile OTP sent: {result['message']}")
            
            # Check OTP was created
            otp = UserOTP.objects.filter(
                user=self.user,
                otp_type='mobile'
            ).order_by('-created_at').first()
            
            if otp:
                print_info(f"OTP Code: {otp.otp_code} (check your SMS)")
                print_info(f"Expires at: {otp.expires_at}")
                self.test_results.append(("Send Mobile OTP", True))
                return otp.otp_code
            else:
                print_error("OTP record not found in database")
                self.test_results.append(("Send Mobile OTP", False))
                return None
        else:
            print_error(f"Failed to send mobile OTP: {result['message']}")
            self.test_results.append(("Send Mobile OTP", False))
            return None
    
    def test_verify_mobile_otp(self, otp_code):
        """Test verifying mobile OTP"""
        print_header("Test 4: Verify Mobile OTP")
        
        # Test with wrong OTP first
        result = OTPService.verify_mobile_otp(self.user, "000000")
        if not result['success']:
            print_success(f"Wrong OTP rejected: {result['message']}")
        else:
            print_error("Wrong OTP was accepted!")
        
        # Test with correct OTP
        result = OTPService.verify_mobile_otp(self.user, otp_code)
        
        if result['success']:
            print_success(f"Mobile OTP verified: {result['message']}")
            
            # Check user verification status
            self.user.refresh_from_db()
            if self.user.phone_verified:
                print_success("User phone_verified flag set to True")
                print_info(f"Verified at: {self.user.phone_verified_at}")
                self.test_results.append(("Verify Mobile OTP", True))
                return True
            else:
                print_error("User phone_verified flag not set")
                self.test_results.append(("Verify Mobile OTP", False))
                return False
        else:
            print_error(f"Failed to verify mobile OTP: {result['message']}")
            self.test_results.append(("Verify Mobile OTP", False))
            return False
    
    def test_resend_cooldown(self):
        """Test resend cooldown"""
        print_header("Test 5: Resend Cooldown")
        
        # Invalidate previous OTPs
        UserOTP.objects.filter(user=self.user, otp_type='email').update(is_verified=True)
        
        # Send first OTP (creates a new pending OTP)
        result = OTPService.send_email_otp(self.user)
        if not result['success']:
            print_error(f"Failed to send initial OTP: {result['message']}")
            self.test_results.append(("Resend Cooldown", False))
            return False
        
        # Try to send immediately (should be blocked by cooldown)
        result = OTPService.send_email_otp(self.user)
        
        if not result['success'] and 'wait' in result['message'].lower():
            print_success(f"Cooldown enforced: {result['message']}")
            self.test_results.append(("Resend Cooldown", True))
            return True
        else:
            print_error("Cooldown not enforced!")
            self.test_results.append(("Resend Cooldown", False))
            return False
    
    def test_otp_expiry(self):
        """Test OTP expiry (would take 5 minutes in real scenario)"""
        print_header("Test 6: OTP Expiry (simulated)")
        
        # Create an expired OTP manually
        from datetime import timedelta
        from django.utils import timezone
        
        expired_otp = UserOTP.objects.create(
            user=self.user,
            otp_type='email',
            otp_code='999999',
            contact=self.user.email,
            expires_at=timezone.now() - timedelta(minutes=1)  # Already expired
        )
        
        # Try to verify expired OTP
        result = OTPService.verify_email_otp(self.user, '999999')
        
        if not result['success'] and 'expired' in result['message'].lower():
            print_success(f"Expired OTP rejected: {result['message']}")
            self.test_results.append(("OTP Expiry", True))
            return True
        else:
            print_error("Expired OTP was accepted!")
            self.test_results.append(("OTP Expiry", False))
            return False
    
    def test_max_attempts(self):
        """Test max attempts limit"""
        print_header("Test 7: Max Attempts Limit")
        
        # Invalidate previous OTPs
        UserOTP.objects.filter(user=self.user, otp_type='email').update(is_verified=True)
        
        # Create new OTP
        result = OTPService.send_email_otp(self.user)
        time.sleep(1)  # Wait for cooldown
        
        # Try wrong OTP 3 times
        for i in range(3):
            result = OTPService.verify_email_otp(self.user, "000000")
            print_info(f"Attempt {i+1}: {result['message']}")
        
        # Try 4th time - should be blocked
        result = OTPService.verify_email_otp(self.user, "000000")
        
        if not result['success'] and 'maximum' in result['message'].lower():
            print_success(f"Max attempts enforced: {result['message']}")
            self.test_results.append(("Max Attempts", True))
            return True
        else:
            print_error("Max attempts not enforced!")
            self.test_results.append(("Max Attempts", False))
            return False
    
    def test_verification_status(self):
        """Test getting verification status"""
        print_header("Test 8: Verification Status")
        
        status = OTPService.get_verification_status(self.user)
        
        print_info(f"Email verified: {status['email_verified']}")
        print_info(f"Phone verified: {status['phone_verified']}")
        print_info(f"Fully verified: {status['is_fully_verified']}")
        
        if isinstance(status, dict) and 'email_verified' in status:
            print_success("Verification status retrieved successfully")
            self.test_results.append(("Verification Status", True))
            return True
        else:
            print_error("Failed to get verification status")
            self.test_results.append(("Verification Status", False))
            return False
    
    def print_summary(self):
        """Print test summary"""
        print_header("Test Summary")
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            if result:
                print_success(f"{test_name}")
            else:
                print_error(f"{test_name}")
        
        print(f"\n{passed}/{total} tests passed")
        
        if passed == total:
            print_success("\nAll tests passed! ✨")
        else:
            print_error(f"\n{total - passed} test(s) failed")
        
        return passed == total
    
    def run_all_tests(self):
        """Run all OTP tests"""
        print_header("OTP Verification Test Suite")
        
        # Setup
        if not self.setup_test_user():
            print_error("Failed to setup test user")
            return False
        
        # Test email OTP flow
        email_otp = self.test_send_email_otp()
        if email_otp:
            self.test_verify_email_otp(email_otp)
        
        # Wait for cooldown
        print_info("\nWaiting for cooldown (30 seconds)...")
        time.sleep(31)
        
        # Test mobile OTP flow
        mobile_otp = self.test_send_mobile_otp()
        if mobile_otp:
            self.test_verify_mobile_otp(mobile_otp)
        
        # Test edge cases
        self.test_resend_cooldown()
        self.test_otp_expiry()
        
        # Wait for cooldown before max attempts test
        print_info("\nWaiting for cooldown (30 seconds)...")
        time.sleep(31)
        
        self.test_max_attempts()
        self.test_verification_status()
        
        # Summary
        return self.print_summary()


if __name__ == '__main__':
    tester = OTPTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
