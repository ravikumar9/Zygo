"""
OTP verification models for email and mobile verification.
Phase 2: Security - User Identity Verification

Supports both pre-user (phone-based) and user-linked OTPs.
Phone-based OTPs are used for registration (before user creation).
User-linked OTPs are used for post-registration password reset, etc.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets


class UserOTP(models.Model):
    """Track OTP verification attempts for email and mobile.
    
    Supports two flows:
    1. Pre-registration: phone-based OTP (user=None, phone=required)
    2. Post-registration: user-linked OTP (user=required, phone optional)
    """
    
    OTP_TYPE_CHOICES = [
        ('email', 'Email OTP'),
        ('mobile', 'Mobile OTP'),
    ]
    
    PURPOSE_CHOICES = [
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
        ('verification', 'General Verification'),
    ]
    
    # User link (optional for pre-registration flow)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='otp_attempts',
        null=True,
        blank=True,
        help_text="User instance if linked; None for pre-registration phone-based OTP"
    )
    
    # Contact info (email or phone)
    contact = models.CharField(
        max_length=255, 
        help_text="Email or phone number where OTP was sent"
    )
    
    # OTP details
    otp_type = models.CharField(max_length=10, choices=OTP_TYPE_CHOICES)
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(
        max_length=20, 
        choices=PURPOSE_CHOICES, 
        default='registration',
        help_text="Purpose of OTP (registration, password_reset, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Attempts tracking
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'otp_type', '-created_at']),
            models.Index(fields=['contact', 'otp_type', 'purpose']),
        ]
        verbose_name = 'User OTP'
        verbose_name_plural = 'User OTPs'
    
    def __str__(self):
        user_str = self.user.username if self.user else f"phone:{self.contact}"
        return f"{user_str} - {self.get_otp_type_display()} ({self.purpose})"
    
    @classmethod
    def generate_otp(cls):
        """Generate a secure 6-digit OTP."""
        return str(secrets.randbelow(1000000)).zfill(6)
    
    @classmethod
    def create_otp(cls, otp_type, contact, purpose='registration', user=None, expiry_minutes=5):
        """Create a new OTP for verification.
        
        Args:
            otp_type: 'email' or 'mobile'
            contact: Email address or phone number
            purpose: 'registration', 'password_reset', etc.
            user: Optional User instance (None for pre-registration)
            expiry_minutes: OTP validity in minutes
            
        Returns:
            UserOTP instance
        """
        otp_code = cls.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        
        return cls.objects.create(
            user=user,
            otp_type=otp_type,
            otp_code=otp_code,
            contact=contact,
            purpose=purpose,
            expires_at=expires_at,
        )
    
    @classmethod
    def get_pending_by_contact(cls, contact, otp_type, purpose='registration'):
        """Retrieve pending OTP for a contact (phone or email).
        
        Used in pre-registration flow where user doesn't exist yet.
        """
        return cls.objects.filter(
            contact=contact,
            otp_type=otp_type,
            purpose=purpose,
            is_verified=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
    
    def is_expired(self):
        """Check if OTP has expired."""
        return timezone.now() > self.expires_at
    
    def can_attempt(self):
        """Check if more attempts are allowed."""
        return self.attempts < self.max_attempts and not self.is_verified
    
    def verify(self, entered_otp):
        """Verify the entered OTP against stored OTP.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if self.is_verified:
            return False, "OTP already verified"
        
        if self.is_expired():
            return False, "OTP has expired"
        
        if not self.can_attempt():
            return False, f"Maximum attempts ({self.max_attempts}) exceeded"
        
        self.attempts += 1
        self.save(update_fields=['attempts'])
        
        if self.otp_code == entered_otp:
            self.is_verified = True
            self.verified_at = timezone.now()
            self.save(update_fields=['is_verified', 'verified_at'])
            return True, "OTP verified successfully"
        
        return False, f"Invalid OTP. {self.max_attempts - self.attempts} attempts remaining"
    
    def invalidate(self):
        """Invalidate this OTP (mark as verified to prevent reuse)."""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save(update_fields=['is_verified', 'verified_at'])
