"""
Reviews models with admin moderation support.
Phase 3: UI Data Quality, Trust & Admin Control

Industry-standard review system:
- Reviews are NOT auto-visible
- Admin has full control (approve/hide)
- Linked to bookings for verification
- Soft delete only
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TimeStampedModel


class Review(TimeStampedModel):
    """Base review model with moderation support."""
    
    REVIEW_TYPES = [
        ('hotel', 'Hotel Review'),
        ('bus', 'Bus Review'),
        ('package', 'Package Review'),
    ]
    
    # Entity type
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPES)
    
    # Content
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    
    # Moderation (CRITICAL for trust)
    is_approved = models.BooleanField(
        default=False,
        help_text="Only approved reviews are visible on frontend"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Soft delete
    is_hidden = models.BooleanField(default=False, help_text="Hide without deleting")
    
    # Booking verification (REQUIRED for trust)
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, help_text="Link to booking for verification")
    
    # Helpful votes
    helpful_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['review_type', 'is_approved', '-created_at']),
        ]
        abstract = True
    
    def __str__(self):
        return f"{self.rating}⭐"
    
    @property
    def is_verified_booking(self):
        """Check if review is linked to a completed, paid booking."""
        return bool(self.booking and self.booking.status == 'completed' and self.booking.paid_amount > 0)

    def clean(self):
        """Enforce: reviews only for completed, paid bookings."""
        from django.core.exceptions import ValidationError
        if self.booking and (self.booking.status != 'completed' or self.booking.paid_amount <= 0):
            raise ValidationError(
                f"Review cannot be created. Booking must be COMPLETED with payment. Current status: {self.booking.status}"
            )


class HotelReview(Review):
    """Hotel reviews with moderation."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hotel_reviews')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hotel_reviews_approved'
    )
    hotel = models.ForeignKey('hotels.Hotel', on_delete=models.CASCADE, related_name='reviews')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Hotel Review'
        verbose_name_plural = 'Hotel Reviews'
    
    def __str__(self):
        return f"{self.hotel.name} - {self.rating}⭐ by {self.user.email}"


class BusReview(Review):
    """Bus reviews with moderation."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bus_reviews')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bus_reviews_approved'
    )
    bus = models.ForeignKey('buses.Bus', on_delete=models.CASCADE, related_name='reviews')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bus Review'
        verbose_name_plural = 'Bus Reviews'
    
    def __str__(self):
        return f"{self.bus.bus_name} - {self.rating}⭐ by {self.user.email}"


class PackageReview(Review):
    """Package reviews with moderation."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='package_reviews')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='package_reviews_approved'
    )
    package = models.ForeignKey('packages.Package', on_delete=models.CASCADE, related_name='reviews')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Package Review'
        verbose_name_plural = 'Package Reviews'
    
    def __str__(self):
        return f"{self.package.name} - {self.rating}⭐ by {self.user.email}"

