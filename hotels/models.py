from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.files.storage import default_storage
from django.templatetags.static import static
from decimal import Decimal
from datetime import datetime, date
from core.models import TimeStampedModel, City
from core.soft_delete import SoftDeleteMixin, SoftDeleteManager, AllObjectsManager


class MealPlan(TimeStampedModel):
    """Global meal plan definitions (Goibibo-style)
    
    Admin creates meal plans once, then rooms link to them.
    Examples: Room Only, Breakfast Included, Half Board, Full Board
    """
    PLAN_TYPES = [
        ('room_only', 'Room Only'),
        ('breakfast', 'Breakfast Included'),
        ('half_board', 'Half Board (Breakfast + Lunch/Dinner)'),
        ('full_board', 'Full Board (All Meals)'),
        ('all_inclusive', 'All Inclusive'),
    ]
    
    name = models.CharField(max_length=100, unique=True, help_text="Display name (e.g., 'Breakfast Included')")
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    inclusions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of included items (e.g., ['Breakfast', 'Wi-Fi'])"
    )
    description = models.TextField(blank=True, help_text="What's included in this meal plan")
    is_refundable = models.BooleanField(default=True, help_text="Can bookings with this meal plan be refunded?")
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0, help_text="Lower numbers appear first")
    
    class Meta:
        ordering = ['display_order', 'id']
    
    def __str__(self):
        return self.name


class PolicyCategory(TimeStampedModel):
    """Policy categories for structured property policies (Goibibo-style)
    
    Examples: ID Proof, Smoking Policy, Pet Policy, Food & Beverage, Cancellation
    """
    CATEGORY_TYPES = [
        ('must_read', 'Must Read'),
        ('guest_profile', 'Guest Profile'),
        ('id_proof', 'ID Proof Required'),
        ('smoking', 'Smoking & Alcohol'),
        ('food', 'Food & Beverage'),
        ('pets', 'Pet Policy'),
        ('cancellation', 'Cancellation Policy'),
        ('checkin_checkout', 'Check-in & Check-out'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100, help_text="Display name (e.g., 'ID Proof Required')")
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, unique=True)
    icon_class = models.CharField(max_length=50, blank=True, help_text="CSS icon class (optional)")
    display_order = models.IntegerField(default=0, help_text="Lower numbers appear first in guest UI")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['display_order', 'id']
        verbose_name_plural = "Policy Categories"
    
    def __str__(self):
        return self.name


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

    # Goibibo-style feature: Hourly stays availability (UI badge + flow enable)
    hourly_stays_enabled = models.BooleanField(
        default=False,
        help_text="Enable hourly stay booking flow (6h/12h/24h)"
    )

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
    # Admin approval linkage: Only properties approved are visible in UI
    # Link Hotel to Property Owner submission for admin-gated visibility
    owner_property = models.ForeignKey('property_owners.Property', on_delete=models.SET_NULL, null=True, blank=True, related_name='hotel')
    
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
        """Return primary image URL with cache-busting or fallback placeholder"""
        image_url = self.primary_image_url
        if image_url:
            # Add cache-busting based on updated_at timestamp
            from django.utils import timezone
            timestamp = int(self.updated_at.timestamp()) if hasattr(self, 'updated_at') and self.updated_at else int(timezone.now().timestamp())
            separator = '&' if '?' in image_url else '?'
            return f"{image_url}{separator}v={timestamp}"
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

    def get_structured_cancellation_policy(self):
        """Return hotel-level cancellation policy in structured format.
        
        This is the SINGLE SOURCE OF TRUTH for cancellation policies.
        Room-level policies are deprecated - hotel policies apply to all rooms.
        
        Returns:
            dict with keys: policy_type, refund_percentage, policy_text, cancellation_hours
        """
        # Map hotel cancellation_type to policy_type
        if self.cancellation_type == 'NO_CANCELLATION':
            policy_type = 'NON_REFUNDABLE'
            policy_text = 'Non-refundable booking. Cancellations and changes are not allowed.'
            refund_pct = 0
            cancel_hours = None
        elif self.cancellation_type == 'UNTIL_CHECKIN':
            # Determine if full or partial refund
            if self.refund_percentage >= 100:
                policy_type = 'FREE'
                policy_text = f'Free cancellation until check-in time. {self.refund_percentage}% refund if cancelled before check-in.'
            elif self.refund_percentage > 0:
                policy_type = 'PARTIAL'
                policy_text = f'Partial refund available. {self.refund_percentage}% refund if cancelled before check-in.'
            else:
                policy_type = 'NON_REFUNDABLE'
                policy_text = 'Non-refundable booking despite cancellation window.'
            refund_pct = self.refund_percentage
            # Use 24 hours before check-in as default
            cancel_hours = 24
        elif self.cancellation_type == 'X_DAYS_BEFORE':
            if self.refund_percentage >= 100:
                policy_type = 'FREE'
                policy_text = f'Free cancellation up to {self.cancellation_days} days before check-in. {self.refund_percentage}% refund.'
            elif self.refund_percentage > 0:
                policy_type = 'PARTIAL'
                policy_text = f'Partial refund of {self.refund_percentage}% if cancelled at least {self.cancellation_days} days before check-in.'
            else:
                policy_type = 'NON_REFUNDABLE'
                policy_text = f'Non-refundable booking.'
            refund_pct = self.refund_percentage
            # Convert days to hours
            cancel_hours = (self.cancellation_days or 2) * 24
        else:
            policy_type = 'NON_REFUNDABLE'
            policy_text = 'Cancellation policy not configured.'
            refund_pct = 0
            cancel_hours = None
        
        return {
            'policy_type': policy_type,
            'refund_percentage': refund_pct,
            'policy_text': policy_text,
            'cancellation_hours': cancel_hours,  # Hours before check-in
        }


class HotelImage(TimeStampedModel):
    """Additional images for hotels"""
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='hotels/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    alt_text = models.CharField(max_length=200, blank=True, help_text="Alternative text for accessibility")
    display_order = models.IntegerField(default=0, help_text="Display order (lower numbers first)")
    is_primary = models.BooleanField(default=False)
    IMAGE_CATEGORY_CHOICES = [
        ('property', 'Property Photos'),
        ('room', 'Room Photos'),
        ('traveller', 'Traveller Photos'),
    ]
    category = models.CharField(
        max_length=20,
        choices=IMAGE_CATEGORY_CHOICES,
        default='property',
        help_text="Categorize images for gallery sections"
    )
    
    class Meta:
        ordering = ['display_order', 'id']
    
    def __str__(self):
        return f"{self.hotel.name} - Image"
    
    def get_url_with_cache_busting(self):
        """Return image URL with cache-busting timestamp"""
        if self.image:
            from django.utils import timezone
            timestamp = int(self.updated_at.timestamp()) if self.updated_at else int(timezone.now().timestamp())
            url = self.image.url
            separator = '&' if '?' in url else '?'
            return f"{url}{separator}v={timestamp}"
        return ''


class PropertyPolicy(TimeStampedModel):
    """Structured property policies (Goibibo-style)
    
    Each policy belongs to a category and displays in accordion on guest page.
    Examples:
    - Category: ID Proof → "Government ID required at check-in"
    - Category: Smoking → "Smoking is not allowed in rooms"
    - Category: Pets → "Pets are not allowed"
    """
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='policies')
    category = models.ForeignKey(PolicyCategory, on_delete=models.PROTECT, related_name='hotel_policies')
    label = models.CharField(max_length=255, help_text="Policy statement (e.g., 'Pets are not allowed')")
    description = models.TextField(blank=True, help_text="Additional details (optional)")
    is_highlighted = models.BooleanField(
        default=False,
        help_text="Show in 'Must Read' section at top"
    )
    display_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['category__display_order', 'display_order', 'id']
        verbose_name_plural = "Property Policies"
    
    def __str__(self):
        return f"{self.hotel.name} - {self.category.name}: {self.label}"


class RoomType(TimeStampedModel):
    """Room types for hotels"""
    ROOM_TYPES = [
        ('standard', 'Standard Room'),
        ('deluxe', 'Deluxe Room'),
        ('suite', 'Suite'),
        ('family', 'Family Room'),
        ('executive', 'Executive Room'),
    ]
    
    # Status for property registration workflow (Step 2)
    STATUS_CHOICES = [
        ('DRAFT', 'Draft - Being configured'),
        ('READY', 'Ready - All fields complete'),
        ('APPROVED', 'Approved - Admin verified'),
    ]
    
    BED_TYPE_CHOICES = [
        ('single', 'Single Bed'),
        ('double', 'Double Bed'),
        ('queen', 'Queen Bed'),
        ('king', 'King Bed'),
        ('twin', 'Twin Beds'),
        ('bunk', 'Bunk Bed'),
    ]
    
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='room_types')
    name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='standard')
    description = models.TextField()
    
    # Goibibo-style capacity fields (MANDATORY for approval)
    max_adults = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of adults allowed"
    )
    max_children = models.PositiveIntegerField(
        default=0,
        help_text="Maximum number of children allowed (can be 0)"
    )
    max_occupancy = models.IntegerField(default=2, help_text="Total max guests (auto-calculated from adults + children)")
    
    # Goibibo-style room details (MANDATORY for approval)
    bed_type = models.CharField(
        max_length=20,
        choices=BED_TYPE_CHOICES,
        blank=True,
        help_text="Bed type (e.g., King, Twin)"
    )
    number_of_beds = models.IntegerField(default=1)
    room_size = models.IntegerField(
        help_text='Size in square feet (sqft) - MANDATORY for approval',
        null=True,
        blank=True
    )
    
    base_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Hourly stays support (Goibibo-style)
    supports_hourly = models.BooleanField(
        default=False,
        help_text="Allow hourly booking for this room type"
    )
    hourly_price_6h = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price for 6-hour stay"
    )
    hourly_price_12h = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price for 12-hour stay"
    )
    hourly_price_24h = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price for 24-hour stay"
    )
    
    # Refundability (Goibibo-style)
    is_refundable = models.BooleanField(
        default=True,
        help_text="Can bookings for this room be refunded/cancelled?"
    )
    
    # Status field for property owner workflow
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="DRAFT: in progress, READY: awaiting approval"
    )

    # Room-level discount (mutually exclusive type)
    DISCOUNT_TYPES = [
        ('none', 'No Discount'),
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPES,
        default='none',
        help_text="Room-level discount type (mutually exclusive)."
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Discount value based on discount_type."
    )
    discount_valid_from = models.DateField(null=True, blank=True)
    discount_valid_to = models.DateField(null=True, blank=True)
    discount_is_active = models.BooleanField(default=False)
    
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

    # Image helpers
    def _image_exists(self, image_field):
        try:
            if not image_field:
                return False
            if not getattr(image_field, 'name', None):
                return False
            return image_field.storage.exists(image_field.name)
        except Exception:
            return False

    def get_primary_image(self):
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
    def display_image_url(self):
        img = self.get_primary_image()
        if img and self._image_exists(img):
            try:
                return img.url
            except Exception:
                pass
        from django.templatetags.static import static
        return static('images/room_placeholder.svg')
    
    @property
    def is_draft(self):
        """Check if room is in draft state (incomplete)"""
        return self.status == 'DRAFT'
    
    @property
    def is_complete(self):
        """Check if room has ALL Goibibo-level required fields for approval
        
        MANDATORY fields (Admin CANNOT approve without these):
        - Name, description
        - max_adults >= 1
        - max_children >= 0  
        - bed_type (cannot be blank)
        - room_size (sqft) > 0
        - base_price > 0
        - >= 3 images
        - At least 1 meal plan OR Room Only marked
        """
        # Basic fields
        if not self.name or not self.description:
            return False
        
        # Goibibo-level capacity requirements
        if not self.max_adults or self.max_adults < 1:
            return False
        if self.max_children is None:  # Can be 0, but must be set
            return False
        
        # Goibibo-level room details
        if not self.bed_type:  # MANDATORY
            return False
        if not self.room_size or self.room_size <= 0:  # MANDATORY
            return False
        
        # Pricing
        if self.base_price <= 0:
            return False
        
        # Images: minimum 3 (Goibibo standard)
        if self.images.count() < 3:
            return False
        
        # Meal plans: must have at least 1 active meal plan
        if not self.meal_plans.filter(is_active=True).exists():
            return False
        
        return True
    
    def set_ready(self):
        """Mark room as READY after all fields complete"""
        if self.is_complete:
            self.status = 'READY'
            self.save(update_fields=['status'])
            return True
        return False
    
    @property
    def inventory_count(self):
        """Get current inventory count (for booking form display)"""
        from datetime import date
        today = date.today()
        availability = self.availability.filter(date=today).first()
        if availability:
            return availability.available_rooms
        return self.total_rooms  # Fallback to configured total

    # Pricing helpers
    def _is_discount_window_active(self):
        """Return True if the discount window is active today."""
        if not self.discount_is_active or self.discount_type == 'none':
            return False
        today = date.today()
        if self.discount_valid_from and today < self.discount_valid_from:
            return False
        if self.discount_valid_to and today > self.discount_valid_to:
            return False
        return True

    def get_effective_price(self):
        """Compute discounted tariff without altering GST slab.

        Returns Decimal, never below zero.
        """
        amount = Decimal(self.base_price or 0)
        if not self._is_discount_window_active():
            return amount

        if self.discount_type == 'percentage':
            discount_amt = (amount * self.discount_value) / Decimal('100')
        elif self.discount_type == 'fixed':
            discount_amt = self.discount_value
        else:
            discount_amt = Decimal('0')

        discounted = amount - discount_amt
        if discounted < Decimal('0'):
            discounted = Decimal('0')
        return discounted

    def get_hourly_price(self, hours: int):
        """Return configured hourly price for a given slot.

        Hours must be one of [6, 12, 24]. Falls back to per-night effective price
        when hourly is unsupported or slot unset.
        """
        if not self.supports_hourly:
            return self.get_effective_price()
        slot = int(hours or 0)
        if slot == 6 and self.hourly_price_6h is not None:
            return Decimal(self.hourly_price_6h)
        if slot == 12 and self.hourly_price_12h is not None:
            return Decimal(self.hourly_price_12h)
        if slot == 24 and self.hourly_price_24h is not None:
            return Decimal(self.hourly_price_24h)
        return self.get_effective_price()

    def get_active_cancellation_policy(self):
        """Return the latest active cancellation policy for this room type."""
        return (
            self.cancellation_policies.filter(is_active=True)
            .order_by('-created_at')
            .first()
        )


class RoomCancellationPolicy(TimeStampedModel):
    """Immutable cancellation policy stored at the room level."""

    POLICY_TYPES = [
        ('FREE', 'Free Cancellation'),
        ('PARTIAL', 'Partial Refund'),
        ('NON_REFUNDABLE', 'Non-Refundable'),
    ]

    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name='cancellation_policies'
    )
    policy_type = models.CharField(
        max_length=20,
        choices=POLICY_TYPES,
        default='NON_REFUNDABLE'
    )
    free_cancel_until = models.DateTimeField(null=True, blank=True)
    refund_percentage = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of paid amount to refund (0-100)"
    )
    policy_text = models.TextField(help_text="Human-readable policy snapshot")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        return f"{self.room_type.name} - {self.get_policy_type_display()}"

    def as_snapshot(self):
        """Return a dict snapshot to freeze into a booking."""
        return {
            'policy_type': self.policy_type,
            'free_cancel_until': self.free_cancel_until,
            'refund_percentage': self.refund_percentage,
            'policy_text': self.policy_text,
        }


class RoomMealPlan(TimeStampedModel):
    """Links rooms to global meal plans with pricing (Goibibo-style)
    
    Room base_price = room only
    Meal plan price = base_price + price_delta
    
    Example:
    - Room Only (price_delta = 0)
    - Breakfast (+₹500 per night)
    - Full Board (+₹1500 per night)
    """
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='meal_plans')
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.PROTECT, related_name='room_meal_plans', null=True, blank=True)
    
    # Pricing: Delta from base_price (Goibibo-style)
    price_delta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Additional cost per night for this meal plan (can be 0 for Room Only)"
    )
    
    is_default = models.BooleanField(
        default=False,
        help_text="Pre-select this meal plan for this room?"
    )
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0, help_text="Lower numbers appear first")
    
    class Meta:
        ordering = ['room_type', 'display_order', 'meal_plan__display_order', 'id']
        unique_together = [['room_type', 'meal_plan']]
    
    def __str__(self):
        return f"{self.room_type.name} - {self.meal_plan.name}"
    
    def get_total_price_per_night(self):
        """Calculate total price per night (base + meal plan delta)"""
        return self.room_type.base_price + self.price_delta
    
    def calculate_total_price(self, num_rooms, num_nights):
        """Calculate total price for given rooms and nights"""
        return self.get_total_price_per_night() * num_rooms * num_nights


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

class RoomImage(TimeStampedModel):
    """Multiple images for room types with cache-busting support.
    
    GUARANTEE: Exactly one primary image per room_type at all times.
    - If saving with is_primary=True, demote all others for this room
    - If saving first image with no primary, auto-set as primary
    """
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='hotels/rooms/')
    is_primary = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-is_primary', 'display_order', 'id']
    
    def __str__(self):
        return f"{self.room_type.name} - Image {self.display_order}"
    
    def save(self, *args, **kwargs):
        """Enforce primary image uniqueness at save time."""
        # If this image is marked primary, demote all others for this room
        if self.is_primary:
            RoomImage.objects.filter(room_type=self.room_type).exclude(pk=self.pk).update(is_primary=False)
        # If no primary exists for this room and this is being saved, set as primary
        elif self.room_type.images.filter(is_primary=True).count() == 0:
            self.is_primary = True
        
        super().save(*args, **kwargs)
    
    @property
    def image_url_with_cache_busting(self):
        """Return image URL with cache-busting parameter"""
        if self.image:
            base_url = self.image.url
            timestamp = int(self.updated_at.timestamp())
            separator = '&' if '?' in base_url else '?'
            return f"{base_url}{separator}v={timestamp}"
        return None


class RoomBlock(TimeStampedModel):
    """Room blocking calendar - block/unblock dates for inventory management.
    
    Property owners can block specific dates or ranges to prevent bookings.
    Rules:
    - Cannot block dates with existing confirmed bookings
    - Can block single dates or ranges
    - Bookings must check availability before creation
    """
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='blocks')
    blocked_from = models.DateField(help_text="Start date (inclusive)")
    blocked_to = models.DateField(help_text="End date (inclusive)")
    reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional reason for blocking (e.g., 'Maintenance', 'Owner use')"
    )
    is_active = models.BooleanField(default=True, help_text="Active blocks prevent bookings")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='room_blocks_created'
    )
    
    class Meta:
        ordering = ['blocked_from', 'blocked_to']
        indexes = [
            models.Index(fields=['room_type', 'blocked_from', 'blocked_to']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.room_type.name}: {self.blocked_from} to {self.blocked_to}"
    
    def clean(self):
        """Validate date range and check for existing bookings."""
        from django.core.exceptions import ValidationError
        from datetime import date
        
        # Validate date range
        if self.blocked_to < self.blocked_from:
            raise ValidationError("End date must be after or equal to start date")
        
        # Cannot block past dates
        if self.blocked_from < date.today():
            raise ValidationError("Cannot block past dates")
        
        # Check for existing confirmed bookings in this date range
        from bookings.models import HotelBooking
        overlapping_bookings = HotelBooking.objects.filter(
            room_type=self.room_type,
            check_in_date__lte=self.blocked_to,
            check_out_date__gte=self.blocked_from,
            status__in=['RESERVED', 'CONFIRMED', 'CHECKED_IN']
        )
        
        if overlapping_bookings.exists():
            booking_ids = ', '.join([f"#{b.id}" for b in overlapping_bookings[:3]])
            raise ValidationError(
                f"Cannot block dates with existing bookings: {booking_ids}"
            )
    
    @classmethod
    def is_available(cls, room_type, check_in_date, check_out_date):
        """Check if room is available for given date range (not blocked).
        
        Args:
            room_type: RoomType instance
            check_in_date: date object
            check_out_date: date object
        
        Returns:
            (bool, str): (is_available, reason if blocked)
        """
        blocks = cls.objects.filter(
            room_type=room_type,
            is_active=True,
            blocked_from__lte=check_out_date,
            blocked_to__gte=check_in_date
        )
        
        if blocks.exists():
            block = blocks.first()
            reason = block.reason or "Owner blocked"
            return False, f"Room unavailable: {reason} ({block.blocked_from} to {block.blocked_to})"
        
        return True, ""