from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.files.storage import default_storage
from django.templatetags.static import static
from decimal import Decimal
from datetime import datetime, date
from core.models import TimeStampedModel, City
from core.soft_delete import SoftDeleteMixin, SoftDeleteManager, AllObjectsManager


class Hotel(SoftDeleteMixin, TimeStampedModel):
    """Hotel model with soft delete support"""
    STAR_RATINGS = [
        (1, '1 Star'),
        (2, '2 Star'),
        (3, '3 Star'),
        (4, '4 Star'),
        (5, '5 Star'),
    ]

    INVENTORY_SOURCES = [
        ('external_cm', 'External Channel Manager'),
        ('internal_cm', 'Internal (GoExplorer)'),
    ]

    PROPERTY_TYPES = [
        ('hotel', 'Hotel'),
        ('resort', 'Resort'),
        ('villa', 'Villa'),
        ('homestay', 'Homestay'),
        ('lodge', 'Lodge / Residency / Cottage'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='hotels')
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    property_type = models.CharField(
        max_length=20,
        choices=PROPERTY_TYPES,
        default='hotel',
        help_text="Property category (hotel/resort/villa/homestay/lodge)"
    )
    property_rules = models.TextField(blank=True, help_text="House rules, check-in policies, ID requirements")
    amenities_rules = models.TextField(blank=True, help_text="Amenity details and usage rules shown as a paragraph")
    
    star_rating = models.IntegerField(choices=STAR_RATINGS, default=3)
    review_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0
    )
    review_count = models.IntegerField(default=0)
    
    image = models.ImageField(upload_to='hotels/', null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Inventory ownership
    inventory_source = models.CharField(
        max_length=20,
        choices=INVENTORY_SOURCES,
        default='internal_cm',
        help_text="Defines whether this property is managed by an external channel manager or GoExplorer internal inventory",
    )
    channel_manager_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional external channel manager provider name",
    )
    
    # Amenities
    has_wifi = models.BooleanField(default=True)
    has_parking = models.BooleanField(default=False)
    has_pool = models.BooleanField(default=False)
    has_gym = models.BooleanField(default=False)
    has_restaurant = models.BooleanField(default=False)
    has_spa = models.BooleanField(default=False)
    has_ac = models.BooleanField(default=True)
    
    checkin_time = models.TimeField(default='14:00')
    checkout_time = models.TimeField(default='11:00')
    cancellation_policy = models.TextField(blank=True, help_text="Cancellation and refund policy")
    
    # Cancellation Rules
    CANCELLATION_TYPES = [
        ('NO_CANCELLATION', 'No Cancellation'),
        ('UNTIL_CHECKIN', 'Allowed Until Check-in'),
        ('X_DAYS_BEFORE', 'Allowed X Days Before Check-in'),
    ]
    REFUND_MODES = [
        ('WALLET', 'Wallet'),
        ('ORIGINAL', 'Original Payment'),
    ]
    cancellation_type = models.CharField(
        max_length=20,
        choices=CANCELLATION_TYPES,
        default='UNTIL_CHECKIN'
    )
    cancellation_days = models.PositiveIntegerField(null=True, blank=True)
    refund_percentage = models.PositiveIntegerField(default=100)
    refund_mode = models.CharField(
        max_length=20,
        choices=REFUND_MODES,
        default='WALLET'
    )
    
    # GST (Goods and Services Tax)
    gst_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=18.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="GST percentage (default: 18%)"
    )
    
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField()
    
    # Managers (soft delete support)
    objects = SoftDeleteManager()  # Default: excludes deleted
    all_objects = AllObjectsManager()  # Includes deleted
    
    class Meta:
        ordering = ['-is_featured', '-review_rating', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.city.name}"

    # Image helpers
    def _image_exists(self, image_field):
        """Return True if the image exists on disk/storage."""
        try:
            if not image_field:
                return False
            if not image_field.name:
                return False
            exists = default_storage.exists(image_field.name)
            return exists
        except Exception as e:
            return False

    def get_primary_image(self):
        """Return the primary image file with sensible fallbacks."""
        if self._image_exists(self.image):
            return self.image

        primary = self.images.filter(is_primary=True).first()
        if primary and self._image_exists(primary.image):
            return primary.image

        first = self.images.first()
        if first and self._image_exists(first.image):
            return first.image
        
        return None

    @property
    def primary_image_url(self):
        image = self.get_primary_image()
        if self._image_exists(image):
            try:
                return image.url
            except Exception:
                return ''
        return ''

    @property
    def display_image_url(self):
        """Return primary image URL or fallback placeholder"""
        image_url = self.primary_image_url
        if image_url:
            return image_url
        return '/static/images/hotel_placeholder.svg'

    def can_cancel_booking(self, check_in_date):
        """Check if a booking can be cancelled based on property rules.
        
        Args:
            check_in_date: date object
            
        Returns:
            (bool, str): (can_cancel, reason)
        """
        from datetime import datetime, date, timedelta
        
        today = date.today() if isinstance(check_in_date, date) and not isinstance(check_in_date, datetime) else datetime.now().date()
        
        if self.cancellation_type == 'NO_CANCELLATION':
            return False, 'This property does not allow cancellations'
        
        if self.cancellation_type == 'UNTIL_CHECKIN':
            if check_in_date > today:
                return True, f'Allowed until check-in ({check_in_date})'
            return False, f'Cancellation only allowed before check-in ({check_in_date})'
        
        if self.cancellation_type == 'X_DAYS_BEFORE':
            if not self.cancellation_days:
                return False, 'Cancellation days not configured'
            cutoff_date = check_in_date - timedelta(days=self.cancellation_days)
            if today <= cutoff_date:
                return True, f'Allowed until {cutoff_date.strftime("%b %d, %Y")}'
            return False, f'Cancellation only allowed until {cutoff_date.strftime("%b %d, %Y")}'
        
        return False, 'Unknown cancellation policy'


class HotelImage(models.Model):
    """Additional images for hotels"""
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='hotels/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    alt_text = models.CharField(max_length=200, blank=True, help_text="Alternative text for accessibility")
    display_order = models.IntegerField(default=0, help_text="Display order (lower numbers first)")
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['display_order', 'id']
    
    def __str__(self):
        return f"{self.hotel.name} - Image"



class RoomType(TimeStampedModel):
    """Room types for hotels"""
    ROOM_TYPES = [
        ('standard', 'Standard Room'),
        ('deluxe', 'Deluxe Room'),
        ('suite', 'Suite'),
        ('family', 'Family Room'),
        ('executive', 'Executive Room'),
    ]
    
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='room_types')
    name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='standard')
    description = models.TextField()
    
    max_occupancy = models.IntegerField(default=2)
    number_of_beds = models.IntegerField(default=1)
    room_size = models.IntegerField(help_text='Size in square feet', null=True, blank=True)
    
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Room amenities
    has_balcony = models.BooleanField(default=False)
    has_tv = models.BooleanField(default=True)
    has_minibar = models.BooleanField(default=False)
    has_safe = models.BooleanField(default=False)
    
    total_rooms = models.IntegerField(default=1)
    is_available = models.BooleanField(default=True)
    
    image = models.ImageField(upload_to='hotels/rooms/', null=True, blank=True)
    
    class Meta:
        ordering = ['hotel', 'base_price']
    
    def __str__(self):
        return f"{self.hotel.name} - {self.name}"


class RoomMealPlan(TimeStampedModel):
    """Meal plan options for room types"""
    PLAN_TYPES = [
        ('room_only', 'Room Only'),
        ('room_breakfast', 'Room + Breakfast'),
        ('room_half_board', 'Room + Breakfast + Dinner'),
        ('room_full_board', 'Room + All Meals'),
    ]
    
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='meal_plans')
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    name = models.CharField(max_length=100, help_text="Display name for this meal plan")
    description = models.TextField(blank=True)
    
    # Pricing strategy: absolute or delta
    price_per_night = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Total price per night including room and meals (absolute pricing)"
    )
    
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0, help_text="Lower numbers appear first")
    
    class Meta:
        ordering = ['room_type', 'display_order', 'id']
        unique_together = [['room_type', 'plan_type']]
    
    def __str__(self):
        return f"{self.room_type.name} - {self.get_plan_type_display()}"
    
    def calculate_total_price(self, num_rooms, num_nights):
        """Calculate total price for given rooms and nights"""
        return self.price_per_night * num_rooms * num_nights


class ChannelManagerRoomMapping(TimeStampedModel):
    """Maps internal room types to external channel manager room identifiers."""

    PROVIDER_CHOICES = [
        ('generic', 'Generic'),
        ('staah', 'STAAH'),
        ('ratehawk', 'RateHawk'),
        ('djubo', 'Djubo'),
        ('other', 'Other'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='channel_mappings')
    room_type = models.OneToOneField('RoomType', on_delete=models.CASCADE, related_name='channel_mapping')
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, default='generic')
    external_room_id = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['hotel__name', 'room_type__name']
        verbose_name = 'Channel Manager Mapping'
        verbose_name_plural = 'Channel Manager Mappings'

    def __str__(self):
        return f"{self.hotel.name} -> {self.external_room_id} ({self.provider})"


class RoomAvailability(models.Model):
    """Track room availability by date"""
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='availability')
    date = models.DateField()
    available_rooms = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['room_type', 'date']
        ordering = ['date']
    
    def __str__(self):
        return f"{self.room_type} - {self.date}"


class HotelDiscount(TimeStampedModel):
    """Discounts for hotels/rooms"""
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('cashback', 'Cashback'),
    ]
    
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='discounts')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='percentage')
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    description = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    # Validity
    valid_from = models.DateTimeField(default=timezone.now)
    valid_till = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Conditions
    min_booking_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum discount amount if type is percentage"
    )
    usage_limit = models.IntegerField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-valid_from']
    
    def __str__(self):
        return f"{self.hotel.name} - {self.description}"
    
    def is_valid(self):
        """Check if discount is still valid"""
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_till and
            (self.usage_limit is None or self.usage_count < self.usage_limit)
        )
    
    def calculate_discount(self, amount):
        """Calculate discount for given amount"""
        if amount < self.min_booking_amount:
            return Decimal('0.00')
        
        if self.discount_type == 'percentage':
            discount = (amount * self.discount_value) / Decimal('100')
            if self.max_discount:
                discount = min(discount, self.max_discount)
            return discount
        elif self.discount_type == 'fixed':
            return min(self.discount_value, amount)
        elif self.discount_type == 'cashback':
            return self.discount_value
        return Decimal('0.00')


class PriceLog(TimeStampedModel):
    """Log for price changes (audit trail)"""
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='price_logs')
    old_price = models.DecimalField(max_digits=10, decimal_places=2)
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    change_date = models.DateField(null=True, blank=True, help_text="Date when price changes take effect")
    reason = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.room_type} - {self.old_price} -> {self.new_price}"
