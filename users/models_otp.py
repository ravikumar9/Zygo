"""
OTP verification models for email and mobile verification.
Phase 2: Security - User Identity Verification
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets


class UserOTP(models.Model):
    """Track OTP verification attempts for email and mobile."""
    
    OTP_TYPE_CHOICES = [
        ('email', 'Email OTP'),
        ('mobile', 'Mobile OTP'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='otp_attempts')
    otp_type = models.CharField(max_length=10, choices=OTP_TYPE_CHOICES)
    otp_code = models.CharField(max_length=6)
    contact = models.CharField(max_length=255, help_text="Email or phone number where OTP was sent")
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'otp_type', '-created_at']),
            models.Index(fields=['contact', 'otp_type']),
        ]
        verbose_name = 'User OTP'
        verbose_name_plural = 'User OTPs'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_otp_type_display()} - {self.contact}"
    
    @classmethod
    def generate_otp(cls):
        """Generate a secure 6-digit OTP."""
        return str(secrets.randbelow(1000000)).zfill(6)
    
    @classmethod
    def create_otp(cls, user, otp_type, contact, expiry_minutes=5):
        """Create a new OTP for user verification."""
        otp_code = cls.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        
        return cls.objects.create(
            user=user,
            otp_type=otp_type,
            otp_code=otp_code,
            contact=contact,
            expires_at=expires_at,
        )
    
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
        self.save(update_fields=['is_verified'])
