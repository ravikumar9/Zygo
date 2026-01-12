"""
OTP service for sending and verifying email and mobile OTPs.
Phase 2: Security - User Identity Verification

Uses NotificationService from Phase 1 for delivery.
"""
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from notifications.services import NotificationService
from .models_otp import UserOTP

logger = logging.getLogger(__name__)
email_logger = logging.getLogger('django.core.mail')  # Django's built-in email logger


class OTPService:
    """Service for OTP generation, sending, and verification."""
    
    RESEND_COOLDOWN_SECONDS = 30
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 3
    
    @classmethod
    def can_resend(cls, user, otp_type):
        """Check if user can request a new OTP (cooldown check).
        
        Returns:
            tuple: (can_resend: bool, wait_seconds: int)
        """
        last_otp = UserOTP.objects.filter(
            user=user,
            otp_type=otp_type,
            is_verified=False  # Only check pending OTPs for cooldown
        ).order_by('-created_at').first()
        
        if not last_otp:
            return True, 0
        
        elapsed = (timezone.now() - last_otp.created_at).total_seconds()
        if elapsed < cls.RESEND_COOLDOWN_SECONDS:
            wait_seconds = int(cls.RESEND_COOLDOWN_SECONDS - elapsed)
            return False, wait_seconds
        
        return True, 0
    
    @classmethod
    @transaction.atomic
    def send_email_otp(cls, user, email=None):
        """Send OTP to user's email.
        
        Args:
            user: User instance
            email: Optional email override (defaults to user.email)
            
        Returns:
            dict: {'success': bool, 'message': str, 'otp_id': int}
        """
        target_email = email or user.email
        if not target_email:
            return {'success': False, 'message': 'No email address provided'}
        
        # Check resend cooldown
        can_resend, wait_seconds = cls.can_resend(user, 'email')
        if not can_resend:
            return {
                'success': False,
                'message': f'Please wait {wait_seconds} seconds before requesting another OTP'
            }
        
        # Invalidate any previous pending OTPs
        UserOTP.objects.filter(
            user=user,
            otp_type='email',
            is_verified=False
        ).update(is_verified=True)
        
        # Create new OTP
        otp_record = UserOTP.create_otp(
            user=user,
            otp_type='email',
            contact=target_email,
            expiry_minutes=cls.OTP_EXPIRY_MINUTES
        )
        
        # Send via email using NotificationService
        context = {
            'name': user.first_name or user.username,
            'otp': otp_record.otp_code,
            'expiry_minutes': cls.OTP_EXPIRY_MINUTES,
            'message': f'Your verification code is: {otp_record.otp_code}',
        }
        
        try:
            NotificationService.send_email(
                to=target_email,
                subject='GoExplorer - Email Verification Code',
                template='notifications/email/otp_email.html',
                context=context,
                user=user,
            )
            email_logger.info(f"Email OTP sent successfully to {target_email} (user_id={user.id})")
            logger.info(f"Email OTP sent to {target_email} for user {user.id}")
        except Exception as e:
            email_logger.error(f"Failed to send email OTP to {target_email} (user_id={user.id}): {e}", exc_info=True)
            logger.error(f"Failed to send email OTP to {target_email}: {e}", exc_info=True)
            # Don't fail silently - let the caller know something went wrong
            return {
                'success': False,
                'message': 'Failed to send OTP. Please try again.'
            }
        
        return {
            'success': True,
            'message': f'OTP sent to {target_email}',
            'otp_id': otp_record.id,
        }
    
    @classmethod
    @transaction.atomic
    def send_mobile_otp(cls, user, phone=None):
        """Send OTP to user's phone via SMS.
        
        Args:
            user: User instance
            phone: Optional phone override (defaults to user.phone)
            
        Returns:
            dict: {'success': bool, 'message': str, 'otp_id': int}
        """
        target_phone = phone or user.phone
        if not target_phone:
            return {'success': False, 'message': 'No phone number provided'}
        
        # Check resend cooldown
        can_resend, wait_seconds = cls.can_resend(user, 'mobile')
        if not can_resend:
            return {
                'success': False,
                'message': f'Please wait {wait_seconds} seconds before requesting another OTP'
            }
        
        # Invalidate any previous pending OTPs
        UserOTP.objects.filter(
            user=user,
            otp_type='mobile',
            is_verified=False
        ).update(is_verified=True)
        
        # Create new OTP
        otp_record = UserOTP.create_otp(
            user=user,
            otp_type='mobile',
            contact=target_phone,
            expiry_minutes=cls.OTP_EXPIRY_MINUTES
        )
        
        # Send via SMS using NotificationService (MSG91)
        template_id = getattr(settings, 'MSG91_OTP_TEMPLATE_ID', settings.MSG91_DEFAULT_TEMPLATE_ID)
        
        try:
            NotificationService.send_sms(
                phone=target_phone,
                template_id=template_id,
                variables={'otp': otp_record.otp_code},
                user=user,
            )
            logger.info(f"Mobile OTP sent to {target_phone} for user {user.id}")
        except Exception as e:
            logger.error(f"Failed to send mobile OTP to {target_phone}: {e}", exc_info=True)
            # Don't fail silently - let the caller know something went wrong
            return {
                'success': False,
                'message': 'Failed to send OTP. Please try again.'
            }
        
        return {
            'success': True,
            'message': f'OTP sent to {target_phone}',
            'otp_id': otp_record.id,
        }
    
    @classmethod
    @transaction.atomic
    def verify_email_otp(cls, user, otp_code):
        """Verify email OTP.
        
        Args:
            user: User instance
            otp_code: OTP code entered by user
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Get latest unverified email OTP
        otp_record = UserOTP.objects.filter(
            user=user,
            otp_type='email',
            is_verified=False
        ).order_by('-created_at').first()
        
        if not otp_record:
            return {'success': False, 'message': 'No pending OTP found. Please request a new one.'}
        
        # Verify OTP
        success, message = otp_record.verify(otp_code)
        
        if success:
            # Update user verification status
            user.email_verified = True
            user.email_verified_at = timezone.now()
            user.save(update_fields=['email_verified', 'email_verified_at'])
            logger.info(f"Email verified for user {user.id}")
        
        return {'success': success, 'message': message}
    
    @classmethod
    @transaction.atomic
    def verify_mobile_otp(cls, user, otp_code):
        """Verify mobile OTP.
        
        Args:
            user: User instance
            otp_code: OTP code entered by user
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Get latest unverified mobile OTP
        otp_record = UserOTP.objects.filter(
            user=user,
            otp_type='mobile',
            is_verified=False
        ).order_by('-created_at').first()
        
        if not otp_record:
            return {'success': False, 'message': 'No pending OTP found. Please request a new one.'}
        
        # Verify OTP
        success, message = otp_record.verify(otp_code)
        
        if success:
            # Update user verification status
            user.phone_verified = True
            user.phone_verified_at = timezone.now()
            user.save(update_fields=['phone_verified', 'phone_verified_at'])
            logger.info(f"Phone verified for user {user.id}")
        
        return {'success': success, 'message': message}
    
    @classmethod
    def get_verification_status(cls, user):
        """Get user's current verification status.
        
        Returns:
            dict: Verification status for email and phone
        """
        return {
            'email_verified': user.email_verified,
            'email_verified_at': user.email_verified_at.isoformat() if user.email_verified_at else None,
            'phone_verified': user.phone_verified,
            'phone_verified_at': user.phone_verified_at.isoformat() if user.phone_verified_at else None,
            'is_fully_verified': user.email_verified and user.phone_verified,
        }
