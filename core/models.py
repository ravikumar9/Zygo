from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from datetime import timedelta
from decimal import Decimal


class TimeStampedModel(models.Model):
    """Abstract base model with created and updated timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class City(models.Model):
    """Cities for hotels, buses, and packages"""
    name = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    code = models.CharField(max_length=10, unique=True)  # e.g., DEL, BLR, MUM
    is_popular = models.BooleanField(default=False)
    image = models.ImageField(upload_to='cities/', null=True, blank=True)
    
    class Meta:
        verbose_name_plural = 'Cities'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name}, {self.state}"


class PromoCode(TimeStampedModel):
    """
    Promo codes for discounts on bookings.
    Fully admin-controlled with one-click enable/disable.
    """
    DISCOUNT_TYPE_CHOICES = [
        ('flat', 'Flat Discount'),
        ('percentage', 'Percentage Discount'),
    ]
    
    SERVICE_TYPE_CHOICES = [
        ('all', 'All Services'),
        ('hotel', 'Hotels Only'),
        ('bus', 'Buses Only'),
        ('package', 'Packages Only'),
    ]
    
    code = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        help_text='Promo code (e.g., SUMMER2026, WELCOME50)'
    )
    description = models.TextField(
        blank=True,
        help_text='Internal description for admin reference'
    )
    
    # Discount configuration
    discount_type = models.CharField(
        max_length=20, 
        choices=DISCOUNT_TYPE_CHOICES,
        default='percentage',
        help_text='Type of discount to apply'
    )
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Discount amount (₹ for flat, % for percentage)'
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Maximum discount amount (for percentage discounts)'
    )
    min_booking_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Minimum booking amount required to use this code'
    )
    
    # Applicability
    applicable_to = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
        default='all',
        help_text='Which services this promo code applies to'
    )
    
    # Validity
    valid_from = models.DateTimeField(
        default=timezone.now,
        help_text='Promo code becomes active from this date'
    )
    valid_until = models.DateTimeField(
        help_text='Promo code expires after this date'
    )
    
    # Usage limits
    max_total_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum total uses across all users (leave blank for unlimited)'
    )
    max_uses_per_user = models.PositiveIntegerField(
        default=1,
        help_text='Maximum uses per user'
    )
    total_uses = models.PositiveIntegerField(
        default=0,
        help_text='Current total uses (auto-incremented)'
    )
    
    # Control
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='ONE-CLICK TOGGLE: Enable/disable this promo code instantly'
    )
    
    class Meta:
        verbose_name = 'Promo Code'
        verbose_name_plural = 'Promo Codes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]
    
    def __str__(self):
        return f"{self.code} ({self.get_discount_display()})"
    
    def clean(self):
        """Validation"""
        # Default nullable numeric fields to avoid None comparisons in admin/serializers
        if self.min_booking_amount is None:
            self.min_booking_amount = Decimal('0')
        if self.max_total_uses is None:
            self.max_total_uses = 0
        if self.max_discount_amount is None:
            self.max_discount_amount = Decimal('0')

        if self.valid_until and self.valid_from and self.valid_until <= self.valid_from:
            raise ValidationError('Valid until date must be after valid from date')
        
        if self.discount_type == 'percentage' and self.discount_value > 100:
            raise ValidationError('Percentage discount cannot exceed 100%')
    
    def is_valid(self):
        """Check if promo code is currently valid"""
        if not self.is_active:
            return False, "Promo code is inactive"
        
        now = timezone.now()
        if now < self.valid_from:
            return False, "Promo code not yet active"
        
        if now > self.valid_until:
            return False, "Promo code has expired"
        
        if self.max_total_uses and self.total_uses >= self.max_total_uses:
            return False, "Promo code usage limit reached"
        
        return True, "Valid"
    
    def get_discount_display(self):
        """Get formatted discount display"""
        if self.discount_type == 'flat':
            return f"₹{self.discount_value} OFF"
        else:
            return f"{self.discount_value}% OFF"
    
    def calculate_discount(self, booking_amount, service_type='all'):
        """
        Calculate discount amount for a booking.
        
        Args:
            booking_amount: Total booking amount
            service_type: Type of service (hotel/bus/package)
        
        Returns:
            tuple: (discount_amount, error_message)
        """
        # Check validity
        is_valid, message = self.is_valid()
        if not is_valid:
            return 0, message
        
        # Check service type
        if self.applicable_to != 'all' and self.applicable_to != service_type:
            return 0, f"Promo code not applicable to {service_type} bookings"
        
        # Check minimum booking amount
        if self.min_booking_amount and booking_amount < self.min_booking_amount:
            return 0, f"Minimum booking amount ₹{self.min_booking_amount} required"
        
        # Calculate discount
        if self.discount_type == 'flat':
            discount = min(float(self.discount_value), float(booking_amount))
        else:  # percentage
            discount = float(booking_amount) * float(self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, float(self.max_discount_amount))
        
        return discount, None
    
    def record_usage(self):
        """Increment usage counter"""
        self.total_uses += 1
        self.save(update_fields=['total_uses'])


class PromoCodeUsage(TimeStampedModel):
    """Track promo code usage per user"""
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.CASCADE,
        related_name='usages'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='promo_usages'
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='promo_usages'
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Actual discount applied'
    )
    
    class Meta:
        verbose_name = 'Promo Code Usage'
        verbose_name_plural = 'Promo Code Usages'
        indexes = [
            models.Index(fields=['user', 'promo_code']),
        ]
    
    def __str__(self):
        return f"{self.promo_code.code} used by {self.user.email}"


class CorporateDiscount(TimeStampedModel):
    """
    Corporate discounts based on email domain.
    Auto-applied during booking.
    """
    DISCOUNT_TYPE_CHOICES = [
        ('flat', 'Flat Discount'),
        ('percentage', 'Percentage Discount'),
    ]
    
    SERVICE_TYPE_CHOICES = [
        ('all', 'All Services'),
        ('hotel', 'Hotels Only'),
        ('bus', 'Buses Only'),
        ('package', 'Packages Only'),
    ]
    
    company_name = models.CharField(
        max_length=200,
        help_text='Company name (e.g., Tata Consultancy Services)'
    )
    email_domain = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Email domain (e.g., tcs.com, infosys.com)'
    )
    
    # Discount configuration
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percentage'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Maximum discount amount (for percentage discounts)'
    )
    
    # Applicability
    applicable_to = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
        default='all'
    )
    
    # Control
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='ONE-CLICK TOGGLE: Enable/disable corporate discount instantly'
    )
    
    class Meta:
        verbose_name = 'Corporate Discount'
        verbose_name_plural = 'Corporate Discounts'
        ordering = ['company_name']
    
    def __str__(self):
        return f"{self.company_name} (@{self.email_domain})"
    
    def clean(self):
        """Validation"""
        # Normalize email domain
        self.email_domain = self.email_domain.lower().strip()
        
        if self.discount_type == 'percentage' and self.discount_value > 100:
            raise ValidationError('Percentage discount cannot exceed 100%')
    
    def get_discount_display(self):
        """Get formatted discount display"""
        if self.discount_type == 'flat':
            return f"₹{self.discount_value} OFF"
        else:
            return f"{self.discount_value}% OFF"
    
    def calculate_discount(self, booking_amount, service_type='all'):
        """
        Calculate discount amount for a booking.
        
        Args:
            booking_amount: Total booking amount
            service_type: Type of service (hotel/bus/package)
        
        Returns:
            float: discount amount
        """
        if not self.is_active:
            return 0
        
        # Check service type
        if self.applicable_to != 'all' and self.applicable_to != service_type:
            return 0
        
        # Calculate discount
        if self.discount_type == 'flat':
            discount = min(float(self.discount_value), float(booking_amount))
        else:  # percentage
            discount = float(booking_amount) * float(self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, float(self.max_discount_amount))
        
        return discount
    
    @classmethod
    def get_for_email(cls, email):
        """
        Get active corporate discount for an email address.
        
        Args:
            email: User email address
        
        Returns:
            CorporateDiscount instance or None
        """
        if not email:
            return None
        
        domain = email.lower().split('@')[-1]
        try:
            return cls.objects.get(email_domain=domain, is_active=True)
        except cls.DoesNotExist:
            return None


class CorporateAccount(TimeStampedModel):
    """
    Corporate account for organizations seeking bulk booking discounts.
    Status flow: pending_verification → approved / rejected
    Upon approval, a corporate-specific coupon is auto-generated.
    """
    STATUS_CHOICES = [
        ('pending_verification', 'Pending Verification'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    ACCOUNT_TYPE_CHOICES = [
        ('business', 'Business'),
        ('enterprise', 'Enterprise'),
        ('startup', 'Startup'),
        ('government', 'Government'),
    ]

    # Organization details
    company_name = models.CharField(max_length=200, help_text='Official company name')
    email_domain = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Official email domain (e.g., company.com) - users with this domain auto-linked'
    )
    gst_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='GST number (optional now, required for approval)'
    )
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default='business'
    )

    # Contact person (primary administrator)
    contact_person_name = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=15)

    # Linked admin user (submitting user becomes admin)
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='administered_corporate_accounts'
    )

    # Status and approval
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending_verification',
        db_index=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_corporate_accounts'
    )
    rejection_reason = models.TextField(blank=True)

    # Auto-generated corporate coupon (created upon approval)
    corporate_coupon = models.OneToOneField(
        'PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_corporate_account'
    )

    # Control
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Corporate Account'
        verbose_name_plural = 'Corporate Accounts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email_domain', 'status']),
            models.Index(fields=['status', 'is_active']),
        ]

    def __str__(self):
        return f"{self.company_name} (@{self.email_domain}) [{self.get_status_display()}]"

    def clean(self):
        """Validation"""
        self.email_domain = self.email_domain.lower().strip()
        if self.status == 'approved' and not self.gst_number:
            raise ValidationError('GST number is required for approval.')

    def approve(self, admin_user):
        """
        Approve corporate account and auto-generate corporate coupon.
        Coupon defaults: 10% discount, max ₹1,000 cap, applies to hotels + buses.
        """
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.approved_by = admin_user
        self.save(update_fields=['status', 'approved_at', 'approved_by', 'updated_at'])

        # Auto-generate corporate-specific coupon if not already exists
        if not self.corporate_coupon:
            from core.models import PromoCode
            coupon_code = f"CORP_{self.email_domain.split('.')[0].upper()}"[:50]
            
            # Ensure uniqueness
            counter = 1
            original_code = coupon_code
            while PromoCode.objects.filter(code=coupon_code).exists():
                coupon_code = f"{original_code}{counter}"
                counter += 1

            coupon = PromoCode.objects.create(
                code=coupon_code,
                description=f"Corporate discount for {self.company_name} ({self.email_domain})",
                discount_type='percentage',
                discount_value=Decimal('10.00'),  # 10% discount
                max_discount_amount=Decimal('1000.00'),  # Max cap ₹1,000
                min_booking_amount=None,  # No minimum
                applicable_to='all',  # Hotels + Buses + Packages
                valid_from=timezone.now(),
                valid_until=timezone.now() + timedelta(days=365),  # 1 year validity
                max_total_uses=None,  # Unlimited total uses
                max_uses_per_user=10,  # 10 uses per user
                is_active=True,
            )
            self.corporate_coupon = coupon
            self.save(update_fields=['corporate_coupon', 'updated_at'])

    def reject(self, admin_user, reason):
        """Reject corporate account."""
        self.status = 'rejected'
        self.rejected_at = timezone.now()
        self.approved_by = admin_user  # Reuse approved_by for rejected_by
        self.rejection_reason = reason
        self.save(update_fields=['status', 'rejected_at', 'approved_by', 'rejection_reason', 'updated_at'])

    def get_linked_users(self):
        """Get all users with matching email domain."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(email__iendswith=f'@{self.email_domain}')

    @classmethod
    def get_for_email(cls, email):
        """
        Get approved corporate account for an email address.
        Returns None if no approved account exists for this domain.
        """
        if not email:
            return None
        domain = email.lower().split('@')[-1]
        try:
            return cls.objects.get(email_domain=domain, status='approved', is_active=True)
        except cls.DoesNotExist:
            return None
