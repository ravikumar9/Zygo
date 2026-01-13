"""
OTP service for sending and verifying email and mobile OTPs.
Phase 2: Security - User Identity Verification

Supports both pre-user phone-based OTP (registration) and user-linked OTP (password reset).

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
email_logger = logging.getLogger('django.core.mail')


class OTPService:
    """Service for OTP generation, sending, and verification.
    
    Supports two OTP flows:
    1. Pre-registration: phone-based OTP (no user required)
    2. Post-registration: user-linked OTP (user required for email, optional for SMS)
    """
    
    RESEND_COOLDOWN_SECONDS = 30
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 3
    
    @classmethod
    def can_resend(cls, contact, otp_type, purpose='registration'):
        """Check if user can request a new OTP (cooldown check).
        
        For pre-registration flow: uses contact (phone) as lookup.
        
        Returns:
            tuple: (can_resend: bool, wait_seconds: int)
        """
        last_otp = UserOTP.objects.filter(
            contact=contact,
            otp_type=otp_type,
            purpose=purpose,
            is_verified=False
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
        """Send OTP to user's email (requires User instance).
        
        Args:
            user: User instance (required)
            email: Optional email override (defaults to user.email)
            
        Returns:
            dict: {'success': bool, 'message': str, 'otp_id': int}
        """
        target_email = email or user.email
        if not target_email:
            return {'success': False, 'message': 'No email address provided'}
        
        # Check resend cooldown
        can_resend, wait_seconds = cls.can_resend(target_email, 'email', 'registration')
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
            otp_type='email',
            contact=target_email,
            purpose='registration',
            user=user,
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
            if not getattr(settings, 'EMAIL_HOST_PASSWORD', None):
                email_logger.error(
                    "SendGrid API key missing; cannot send email OTP to %s (user_id=%s)",
                    target_email,
                    user.id,
                )
                return {
                    'success': False,
                    'message': 'Email service misconfigured. Please contact support.'
                }

            notification = NotificationService.send_email(
                to=target_email,
                subject='GoExplorer - Email Verification Code',
                template='notifications/email/otp_email.html',
                context=context,
                user=user,
            )
            is_dry_run = getattr(notification, 'provider_reference', '') == 'dry-run'
            if not notification or notification.status != 'sent' or is_dry_run:
                error_msg = getattr(notification, 'error_message', '') if notification else ''
                email_logger.error(
                    f"Email OTP not sent (status={getattr(notification, 'status', 'unknown')}) to {target_email}"
                    f" user_id={user.id} error={error_msg}"
                )
                return {
                    'success': False,
                    'message': 'Failed to send OTP email. Please retry or contact support.'
                }

            email_logger.info(f"Email OTP sent successfully to {target_email} (user_id={user.id})")
            logger.info(f"Email OTP sent to {target_email} for user {user.id}")
        except Exception as e:
            email_logger.error(f"Failed to send email OTP to {target_email} (user_id={user.id}): {e}", exc_info=True)
            logger.error(f"Failed to send email OTP to {target_email}: {e}", exc_info=True)
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
    def send_mobile_otp(cls, phone, purpose='registration', user=None):
        """Send OTP to phone via SMS.
        
        Pre-registration flow: phone + purpose (user=None)
        Post-registration flow: user instance with user.phone
        
        Args:
            phone: Phone number to send to
            purpose: 'registration', 'password_reset', etc.
            user: Optional User instance (for context/logging)
            
        Returns:
            dict: {'success': bool, 'message': str, 'otp_id': int}
        """
        if not phone:
            return {'success': False, 'message': 'No phone number provided'}
        
        # Check resend cooldown based on phone (not user)
        can_resend, wait_seconds = cls.can_resend(phone, 'mobile', purpose)
        if not can_resend:
            return {
                'success': False,
                'message': f'Please wait {wait_seconds} seconds before requesting another OTP'
            }
        
        # Invalidate any previous pending OTPs for this phone/purpose
        UserOTP.objects.filter(
            contact=phone,
            otp_type='mobile',
            purpose=purpose,
            is_verified=False
        ).update(is_verified=True)
        
        # Create new OTP (no user required for pre-registration)
        otp_record = UserOTP.create_otp(
            otp_type='mobile',
            contact=phone,
            purpose=purpose,
            user=user,
            expiry_minutes=cls.OTP_EXPIRY_MINUTES
        )
        
        # Send via SMS using NotificationService (MSG91)
        template_id = getattr(settings, 'MSG91_OTP_TEMPLATE_ID', settings.MSG91_DEFAULT_TEMPLATE_ID)

        if not getattr(settings, 'MSG91_AUTHKEY', None) or not template_id:
            logger.error(
                "MSG91 credentials/template missing; cannot send mobile OTP to %s (purpose=%s)",
                phone,
                purpose,
            )
            return {
                'success': False,
                'message': 'SMS service not configured. Please contact support for verification.'
            }
        
        try:
            notification = NotificationService.send_sms(
                phone=phone,
                template_id=template_id,
                variables={'otp': otp_record.otp_code},
                user=user,
            )
            is_dry_run = getattr(notification, 'provider_reference', '') == 'dry-run'
            if not notification or notification.status != 'sent' or is_dry_run:
                error_msg = getattr(notification, 'error_message', '') if notification else ''
                logger.error(
                    f"Mobile OTP not sent (status={getattr(notification, 'status', 'unknown')}) to {phone}"
                    f" purpose={purpose} error={error_msg}"
                )
                return {
                    'success': False,
                    'message': 'Failed to send OTP SMS. Please retry.'
                }

            logger.info(f"Mobile OTP sent to {phone} (purpose={purpose})")
        except Exception as e:
            logger.error(f"Failed to send mobile OTP to {phone}: {e}", exc_info=True)
            return {
                'success': False,
                'message': 'Failed to send OTP. Please try again.'
            }
        
        return {
            'success': True,
            'message': f'OTP sent to {phone}',
            'otp_id': otp_record.id,
        }
    
    @classmethod
    @transaction.atomic
    def verify_email_otp(cls, user, otp_code):
        """Verify email OTP for a user.
        
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
    def verify_mobile_otp_by_contact(cls, phone, otp_code, purpose='registration'):
        """Verify mobile OTP by phone number (pre-registration flow).
        
        Args:
            phone: Phone number that OTP was sent to
            otp_code: OTP code entered
            purpose: 'registration', 'password_reset', etc.
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Get latest unverified mobile OTP for this phone
        otp_record = UserOTP.get_pending_by_contact(phone, 'mobile', purpose)
        
        if not otp_record:
            return {'success': False, 'message': 'No pending OTP found. Please request a new one.'}
        
        # Verify OTP
        success, message = otp_record.verify(otp_code)
        logger.info(f"Mobile OTP verification for {phone}: {success}")
        
        return {'success': success, 'message': message}
    
    @classmethod
    @transaction.atomic
    def verify_mobile_otp(cls, user, otp_code):
        """Verify mobile OTP for a user (post-registration flow).
        
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
