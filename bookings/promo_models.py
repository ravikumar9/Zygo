"""Promo code models and validation logic"""
from django.db import models
from django.utils import timezone
from decimal import Decimal


class PromoCode(models.Model):
    """Promo code for discounts"""
    DISCOUNT_TYPE_CHOICES = [
        ('PERCENTAGE', 'Percentage'),
        ('FLAT', 'Flat Amount'),
    ]
    
    code = models.CharField(max_length=20, unique=True, db_index=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='PERCENTAGE')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_booking_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    max_uses = models.IntegerField(default=1000)
    uses_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'promo_codes'
        verbose_name = 'Promo Code'
        verbose_name_plural = 'Promo Codes'
    
    def __str__(self):
        return f"{self.code} ({self.discount_type})"
    
    def is_valid(self):
        """Check if promo code is currently valid"""
        now = timezone.now()
        return (
            self.is_active
            and self.valid_from <= now <= self.valid_until
            and self.uses_count < self.max_uses
        )
    
    def can_apply_to_amount(self, amount):
        """Check if promo can be applied to given amount"""
        return amount >= self.min_booking_amount
    
    def calculate_discount(self, base_amount):
        """Calculate discount amount for given base amount"""
        if not self.is_valid() or not self.can_apply_to_amount(base_amount):
            return Decimal('0')
        
        if self.discount_type == 'PERCENTAGE':
            discount = base_amount * (self.discount_value / Decimal('100'))
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = self.discount_value
        
        return min(discount, base_amount)
    
    def increment_usage(self):
        """Increment usage counter"""
        self.uses_count += 1
        self.save(update_fields=['uses_count'])


class PromoCodeUsage(models.Model):
    """Track promo code usage by users"""
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, null=True, blank=True)
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'promo_code_usages'
        verbose_name = 'Promo Code Usage'
        verbose_name_plural = 'Promo Code Usages'
    
    def __str__(self):
        return f"{self.promo_code.code} used at {self.used_at}"
