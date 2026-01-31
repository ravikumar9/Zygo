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
from django.core.exceptions import ValidationError


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

    PRICING_STRATEGIES = [
        ('SMART_NUDGE', 'Smart Nudge (Owner Recommendations)'),
        ('NEGOTIATION_ONLY', 'Negotiation Only (Premium / Brand-Sensitive)'),
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
    pricing_strategy = models.CharField(
        max_length=20,
        choices=PRICING_STRATEGIES,
        default='SMART_NUDGE',
        help_text="Pricing control strategy. SMART_NUDGE for 1–3★ & budget listings. NEGOTIATION_ONLY for premium/brand-sensitive listings."
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

    def get_pricing_strategy(self):
        """
        Resolve pricing strategy with safe defaults.

        Defaults:
        - 4★/5★ → NEGOTIATION_ONLY
        - 1–3★, homestay/villa → SMART_NUDGE
        """
        if self.pricing_strategy == 'NEGOTIATION_ONLY':
            return 'NEGOTIATION_ONLY'
        if self.pricing_strategy == 'SMART_NUDGE':
            if self.star_rating and self.star_rating >= 4:
                return 'NEGOTIATION_ONLY'
            return 'SMART_NUDGE'
        if self.star_rating and self.star_rating >= 4:
            return 'NEGOTIATION_ONLY'
        return 'SMART_NUDGE'

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

    # Phase 2.7.3 — Revenue Protection & Pricing Safety Fields
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Supplier/cost price — used for floor price calculations"
    )
    min_margin_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Minimum profit margin % (if set, overrides global config)"
    )
    min_safe_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Absolute minimum safe price (if set, overrides cost-based calculation)"
    )

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


class CompetitorPriceSnapshot(TimeStampedModel):
    """Logged-out competitor price capture with evidence for auditability."""

    SOURCE_CHANNELS = [
        ('desktop_web', 'Desktop Web'),
        ('mobile_web', 'Mobile Web'),
        ('android', 'Android'),
        ('ios', 'iOS'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='competitor_price_snapshots')
    source_name = models.CharField(max_length=100, help_text="Competitor brand/source name")
    source_url = models.URLField(help_text="Public, logged-out URL used for capture")
    source_channel = models.CharField(max_length=20, choices=SOURCE_CHANNELS, default='desktop_web')
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    room_name = models.CharField(max_length=150, help_text="Visible room/plan name from competitor page")
    occupancy = models.PositiveIntegerField(default=2, help_text="Number of guests covered by the price")
    total_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="All-in competitor price")
    currency = models.CharField(max_length=5, default='INR')
    includes_tax = models.BooleanField(default=True, help_text="Whether captured price is tax-inclusive")
    evidence_url = models.URLField(help_text="Immutable evidence link (screenshot/PDF) stored in logged-out context")
    evidence_storage_path = models.CharField(max_length=255, blank=True, help_text="Internal storage path for evidence")
    playwright_trace_url = models.URLField(blank=True, help_text="Trace or HAR from headed Playwright run")
    raw_payload = models.JSONField(default=dict, blank=True, help_text="Structured capture payload for replay")
    source_requires_login = models.BooleanField(
        default=False,
        help_text="Flag capture as invalid if it required authentication (must stay False)",
    )
    is_eep = models.BooleanField(default=False, help_text="Explicit Exclusive/Early booking plan captured")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hotel', 'check_in_date', 'check_out_date']),
            models.Index(fields=['source_name', 'created_at']),
        ]

    def clean(self):
        if self.source_requires_login:
            raise ValidationError("Competitor capture must be logged-out only (source_requires_login cannot be True).")
        if not self.evidence_url:
            raise ValidationError("Evidence URL is required for competitor price snapshots.")
        if self.check_out_date <= self.check_in_date:
            raise ValidationError("Check-out must be after check-in for competitor snapshot.")

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence_url)


class PricingDecisionAudit(TimeStampedModel):
    """Audit log for competitive pricing decisions with guardrails."""

    DECISION_CHOICES = [
        ('MATCH', 'Match competitor'),
        ('UNDERCUT', 'Undercut competitor'),
        ('HOLD', 'Hold price'),
        ('REJECT', 'Reject signal'),
        ('BLOCKED', 'Blocked by guardrail'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='pricing_decision_audits')
    snapshot = models.ForeignKey(
        CompetitorPriceSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pricing_audits'
    )
    eep = models.ForeignKey(
        'hotels.EstimatedEffectivePrice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pricing_audits'
    )
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    baseline_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Current GoExplorer all-in price")
    competitor_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Competitor all-in price considered")
    final_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Price decided after guardrails")
    margin_before_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Margin % before decision"
    )
    margin_after_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Margin % after decision",
    )
    rule_applied = models.CharField(max_length=120, help_text="Rule or policy that produced this decision")
    notes = models.TextField(blank=True)
    evidence_url = models.URLField(blank=True, help_text="Evidence URL used at publish time (usually snapshot's evidence)")
    publish_block_reason = models.CharField(max_length=255, blank=True, help_text="If blocked, why")
    playwright_run_id = models.CharField(
        max_length=128,
        blank=True,
        help_text="Playwright test run ID for evidence linkage"
    )
    cooldown_expires_at = models.DateTimeField(null=True, blank=True)
    enforced_soft_coupon_only = models.BooleanField(default=True)
    coupon_generated = models.ForeignKey(
        'core.PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pricing_audits_generated'
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pricing_decision_audits_created'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hotel', 'created_at']),
            models.Index(fields=['decision', 'created_at']),
        ]

    @property
    def is_publishable(self) -> bool:
        return bool(self.evidence_url) and self.decision in {'MATCH', 'UNDERCUT', 'HOLD'} and not self.publish_block_reason


class CompetitorDiscountBandConfig(TimeStampedModel):
    """Configurable discount bands per competitor platform."""

    PLATFORM_CHOICES = [
        ('agoda', 'Agoda'),
        ('mmt', 'MMT'),
        ('goibibo', 'Goibibo'),
        ('other', 'Other'),
    ]

    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, unique=True, db_index=True)
    min_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum expected discount (e.g., 8%)"
    )
    max_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Maximum expected discount (e.g., 15%)"
    )
    enabled = models.BooleanField(default=True, help_text="Whether to use this band for EEP computation")
    confidence_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.0'),
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Weight for confidence scoring if multiple sources exist"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='discount_band_updates'
    )

    class Meta:
        verbose_name = 'Competitor Discount Band Config'
        verbose_name_plural = 'Competitor Discount Band Configs'
        ordering = ['platform']

    def __str__(self):
        return f"{self.get_platform_display()}: {self.min_percent}% - {self.max_percent}%"

    def clean(self):
        if self.max_percent < self.min_percent:
            raise ValidationError("Maximum discount must be >= minimum discount")


class EstimatedEffectivePrice(TimeStampedModel):
    """Computed EEP from competitor snapshot using discount band config."""

    snapshot = models.ForeignKey(
        CompetitorPriceSnapshot,
        on_delete=models.CASCADE,
        related_name='estimated_effective_prices'
    )
    platform = models.CharField(max_length=50, help_text="Platform name (Agoda, MMT, Goibibo, etc.)")
    band_config = models.ForeignKey(
        CompetitorDiscountBandConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='computed_eeps'
    )
    public_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Public price from snapshot")
    discount_band_min = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Minimum discount % used"
    )
    discount_band_max = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Maximum discount % used"
    )
    discount_factor_used = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Actual discount factor applied (e.g., 0.10 for 10%)"
    )
    eep_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Computed EEP = public_price × (1 - discount_factor_used)"
    )
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Confidence % (0-100); <50% = unreliable"
    )
    ttl_expires_at = models.DateTimeField(help_text="EEP expires after this time (default: 30 min from creation)")
    screenshot_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reference to snapshot's evidence screenshot"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['snapshot', 'platform']),
            models.Index(fields=['ttl_expires_at']),
            models.Index(fields=['confidence_score']),
        ]

    def __str__(self):
        return f"EEP {self.platform}: ₹{self.eep_price} (confidence: {self.confidence_score}%)"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.ttl_expires_at

    @property
    def is_reliable(self) -> bool:
        return self.confidence_score >= Decimal('50') and not self.is_expired


# ============================================================================
# TRACK B: INVENTORY-AWARE PRICING LOCK
# ============================================================================

class RoomInventoryPriceLock(TimeStampedModel):
    """TRACK B: Lock pricing for inventory units during booking flow
    
    Purpose: Prevent price changes after checkout hold is created
    Frozen once: Hold created → price + coupon locked for that unit
    Blocks: repricing, coupon changes, band re-eval
    """
    room = models.ForeignKey(
        'RoomType',
        on_delete=models.CASCADE,
        related_name='price_locks'
    )
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    guest_count = models.PositiveIntegerField(default=2)
    
    locked_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Frozen price for this unit during hold"
    )
    locked_coupon_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="AUTO-SAVE-* if coupon applied"
    )
    locked_coupon_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Discount amount if coupon locked"
    )
    
    lock_reason = models.CharField(
        max_length=50,
        choices=[
            ('hold_created', 'Room Hold Created'),
            ('checkout_initiated', 'Checkout Initiated'),
            ('manual_override', 'Admin Override'),
        ],
        default='hold_created'
    )
    lock_timestamp = models.DateTimeField(auto_now_add=True)
    locked_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='room_locks_created'
    )
    locked_audit_id = models.ForeignKey(
        'PricingDecisionAudit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Which pricing decision locked this price"
    )
    
    is_active = models.BooleanField(default=True, help_text="Lock remains active during hold")
    unlock_reason = models.CharField(
        max_length=100,
        blank=True,
        help_text="Why lock was released (e.g., 'booking_completed', 'hold_expired')"
    )
    unlocked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['room', 'check_in_date', 'is_active']),
            models.Index(fields=['is_active', 'unlocked_at']),
        ]
        unique_together = ('room', 'check_in_date', 'check_out_date', 'guest_count', 'lock_timestamp')
    
    def __str__(self):
        return f"Lock: {self.room.name} {self.check_in_date}–{self.check_out_date} @ ₹{self.locked_price}"


# ============================================================================
# TRACK C: DEMAND & PRICE WAR PROTECTION
# ============================================================================

class PriceWarAlert(TimeStampedModel):
    """TRACK C: Detect competitor price oscillation & protect margin
    
    Purpose: Stop GoExplorer from chasing irrational competitors
    Trigger: >3 price changes in 30 mins = price war
    Response: Disable coupons, lock price, highlight value
    """
    hotel = models.ForeignKey(
        'Hotel',
        on_delete=models.CASCADE,
        related_name='price_war_alerts'
    )
    
    # Oscillation tracking
    snapshot_count_30min = models.PositiveIntegerField(
        default=0,
        help_text="Number of distinct competitor price snapshots in last 30 mins"
    )
    oscillation_detected = models.BooleanField(
        default=False,
        help_text="True if >3 changes detected"
    )
    oscillation_detected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When price war was detected"
    )
    
    # Response
    RESPONSE_CHOICES = [
        ('disabled_coupons', 'Coupons Disabled'),
        ('locked_price', 'Price Locked'),
        ('value_mode', 'Value Highlight Mode'),
        ('hold', 'Price Hold (Manual Review)'),
        ('resolved', 'Oscillation Resolved'),
    ]
    response_action = models.CharField(
        max_length=50,
        choices=RESPONSE_CHOICES,
        default='disabled_coupons'
    )
    response_triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When auto-response was applied"
    )
    
    # Alert metadata
    platform_source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Which platform detected (e.g., 'agoda', 'mmt')"
    )
    price_range_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Min price in 30-min window"
    )
    price_range_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Max price in 30-min window"
    )
    volatility_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="(max - min) / min * 100"
    )
    
    # Admin response
    admin_reviewed = models.BooleanField(default=False)
    admin_review_notes = models.TextField(blank=True)
    admin_override = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('resume_coupons', 'Resume Coupons'),
            ('extend_hold', 'Extend Price Hold'),
            ('escalate', 'Escalate to Management'),
        ]
    )
    
    # Resolution
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_reason = models.CharField(
        max_length=100,
        blank=True,
        help_text="Why was the price war resolved (oscillation stopped, manual override, etc.)"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hotel', 'oscillation_detected']),
            models.Index(fields=['is_resolved', 'created_at']),
        ]
    
    def __str__(self):
        status = "🔴 ACTIVE" if self.oscillation_detected and not self.is_resolved else "✅ RESOLVED"
        return f"Price War {status}: {self.hotel.name} ({self.volatility_percent}% swing)"


# ============================================================================
# TRACK D: COUPON INTELLIGENCE & CANNIBALIZATION MONITOR
# ============================================================================

class CouponCannibalizationMonitor(TimeStampedModel):
    """TRACK D: Track coupon impact on conversion & margin
    
    Purpose: Monitor coupon usage patterns, auto-adjust caps if harmful
    Tracks: coupon vs non-coupon bookings, margin delta, conversion lift
    """
    hotel = models.ForeignKey(
        'Hotel',
        on_delete=models.CASCADE,
        related_name='coupon_monitors'
    )
    
    # Window (usually 24h or 7d)
    window_start = models.DateTimeField(help_text="Start of monitoring window")
    window_end = models.DateTimeField(help_text="End of monitoring window")
    window_type = models.CharField(
        max_length=20,
        choices=[('daily', '24h'), ('weekly', '7d'), ('monthly', '30d')],
        default='daily'
    )
    
    # Coupon bookings
    coupon_bookings_count = models.PositiveIntegerField(default=0)
    coupon_bookings_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    coupon_bookings_avg_margin_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Average margin % on bookings with coupons"
    )
    coupon_total_discount_given = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total discount amount across all coupon bookings"
    )
    
    # Non-coupon bookings (baseline)
    non_coupon_bookings_count = models.PositiveIntegerField(default=0)
    non_coupon_bookings_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    non_coupon_bookings_avg_margin_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Average margin % on bookings WITHOUT coupons"
    )
    
    # Conversion impact
    coupon_conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="(coupon_bookings / sessions_with_coupon_shown) * 100"
    )
    non_coupon_conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="(non_coupon_bookings / sessions_without_coupon_shown) * 100"
    )
    conversion_lift_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="(coupon_cr - non_coupon_cr) / non_coupon_cr * 100; negative = cannibalization"
    )
    
    # Cannibalization flag
    cannibalization_detected = models.BooleanField(
        default=False,
        help_text="True if margin loss exceeds conversion gain"
    )
    cannibalization_severity = models.CharField(
        max_length=20,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        null=True,
        blank=True
    )
    
    # Auto-adjustment action
    ADJUSTMENT_CHOICES = [
        ('no_change', 'No Adjustment'),
        ('reduce_cap', 'Reduced Cap'),
        ('disable_per_hotel', 'Disabled for Hotel'),
        ('extend_ttl_warning', 'Extended TTL Warning'),
    ]
    recommended_action = models.CharField(
        max_length=50,
        choices=ADJUSTMENT_CHOICES,
        default='no_change'
    )
    action_applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)
    
    # New cap (if reduced)
    new_cap_flat = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Reduced flat cap if adjustment applied (default ₹500 → ?)"
    )
    new_cap_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Reduced percentage cap if adjustment applied (default 5% → ?)"
    )
    
    # Report
    report_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full analysis report"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hotel', 'window_start']),
            models.Index(fields=['cannibalization_detected']),
        ]
        unique_together = ('hotel', 'window_start', 'window_type')
    
    def __str__(self):
        status = "⚠️  CANNIBAL" if self.cannibalization_detected else "✅ HEALTHY"
        return f"Coupon Monitor {status}: {self.hotel.name} ({self.conversion_lift_percent:+.1f}% lift)"


# ============================================================
# PHASE 2.7.3 — REVENUE PROTECTION & PRICING SAFETY LAYER
# ============================================================

class PricingSafetyConfig(TimeStampedModel):
    """Singleton configuration for pricing safety guardrails
    
    This is the master control panel for all pricing safety rules.
    Only one record should exist (enforced via singleton pattern).
    """
    
    # Global floor pricing
    global_min_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Global minimum price for any room (fallback)"
    )
    global_min_margin_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Global minimum profit margin % (if cost_price is set)"
    )
    absolute_min_price_hard_stop = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="ABSOLUTE MINIMUM — Never allow prices below this (KILL switch)"
    )
    
    # Competitor price sanity thresholds
    competitor_drop_threshold_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('85.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Flag competitor prices dropping >X% from baseline"
    )
    competitor_hard_reject_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('95.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="REJECT competitor prices dropping >X% (likely data error)"
    )
    competitor_floor_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.65'),
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('2.00'))],
        help_text="Reject competitor prices < X × 7-day median (e.g., 0.65 = 65%)"
    )
    
    # Circuit breaker settings
    circuit_breaker_window_minutes = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        help_text="Time window for anomaly detection (minutes)"
    )
    circuit_breaker_trigger_count = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Number of anomalies to trip circuit breaker"
    )
    
    # Price velocity guards (rate of change limits)
    velocity_max_drop_percent_per_hour = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('35.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Max allowed price drop per hour (%)"
    )
    velocity_max_rise_percent_per_hour = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('40.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Max allowed price rise per hour (%)"
    )
    
    # Master kill switch
    pricing_automation_enabled = models.BooleanField(
        default=True,
        help_text="Master switch: disable to use safe fallback prices only"
    )
    
    # Phase 2.7.3.1 — Shadow Mode for Risk Observation
    SAFETY_MODES = [
        ('SHADOW', 'Shadow Mode - Observe Without Blocking'),
        ('ENFORCE', 'Enforce Mode - Block Unsafe Prices'),
        ('OFF', 'Off - No Safety Checks'),
    ]
    
    pricing_safety_mode = models.CharField(
        max_length=20,
        choices=SAFETY_MODES,
        default='SHADOW',
        help_text="SHADOW: Log would-blocks without blocking | ENFORCE: Block unsafe prices | OFF: Disable all checks"
    )
    
    shadow_mode_enabled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When shadow mode was started (for risk observation period)"
    )
    
    # Metadata
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Admin who last modified this config"
    )
    notes = models.TextField(
        blank=True,
        help_text="Admin notes for why settings were changed"
    )
    
    class Meta:
        verbose_name = "Pricing Safety Configuration"
        verbose_name_plural = "Pricing Safety Configuration"
    
    def save(self, *args, **kwargs):
        """Enforce singleton pattern"""
        if not self.pk and PricingSafetyConfig.objects.exists():
            raise ValidationError("Only one PricingSafetyConfig instance allowed (singleton)")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Get singleton instance (create with defaults if missing)"""
        config, created = cls.objects.get_or_create(pk=1)
        return config
    
    def __str__(self):
        status = "🟢 ENABLED" if self.pricing_automation_enabled else "🔴 DISABLED"
        return f"Pricing Safety Config {status}"


class PricingCircuitState(TimeStampedModel):
    """Circuit breaker state tracker (per room type or global)
    
    Tracks whether pricing automation is currently tripped due to anomalies.
    """
    
    room_type = models.ForeignKey(
        'RoomType',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Specific room type (null = global circuit)"
    )
    
    is_tripped = models.BooleanField(
        default=False,
        help_text="True if circuit breaker is currently tripped"
    )
    tripped_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When circuit breaker was tripped"
    )
    reason = models.TextField(
        blank=True,
        help_text="Why circuit breaker tripped"
    )
    safe_fallback_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Safe price to use while circuit is tripped"
    )
    
    # Auto-recovery
    auto_reset_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When circuit breaker will auto-reset (if configured)"
    )
    manual_reset_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Admin who manually reset the circuit"
    )
    
    class Meta:
        verbose_name = "Pricing Circuit State"
        verbose_name_plural = "Pricing Circuit States"
        indexes = [
            models.Index(fields=['is_tripped']),
            models.Index(fields=['room_type', 'is_tripped']),
        ]
    
    def __str__(self):
        target = f"Room {self.room_type_id}" if self.room_type else "Global"
        status = "🔴 TRIPPED" if self.is_tripped else "🟢 OK"
        return f"Circuit {target}: {status}"


class PricingSafetyEvent(TimeStampedModel):
    """Append-only audit log for all pricing safety actions
    
    Immutable record of every time a safety guard blocked/modified a price.
    """
    
    EVENT_TYPES = [
        ('FLOOR_BLOCK', 'Price Below Floor — Blocked'),
        ('COMPETITOR_REJECT', 'Competitor Price Rejected — Sanity Failed'),
        ('CIRCUIT_TRIP', 'Circuit Breaker Tripped — Too Many Anomalies'),
        ('ADMIN_KILL', 'Admin Kill Switch Activated'),
        ('VELOCITY_BLOCK', 'Price Velocity Exceeded — Blocked'),
        ('ABSOLUTE_KILL_BLOCK', 'Absolute Minimum Violated — HARD STOP'),
        ('SAFE_FALLBACK_USED', 'Safe Fallback Price Used'),
        ('SANITY_WARNING', 'Competitor Price Warning — Not Blocked'),
        ('SHADOW_FLOOR_BLOCK', 'Shadow: Would Block — Price Below Floor'),
        ('SHADOW_COMPETITOR_REJECT', 'Shadow: Would Block — Competitor Price Failed'),
        ('SHADOW_VELOCITY_BLOCK', 'Shadow: Would Block — Velocity Exceeded'),
        ('SHADOW_ABSOLUTE_KILL', 'Shadow: Would Block — Absolute Minimum'),
        ('SHADOW_CIRCUIT_TRIP', 'Shadow: Would Block — Circuit Breaker'),
        ('OWNER_NUDGE_GENERATED', 'Owner: Smart Discount Nudge Generated'),
        ('OWNER_NUDGE_ACCEPTED', 'Owner: Accepted Smart Discount Nudge'),
        ('OWNER_NUDGE_REJECTED', 'Owner: Rejected Smart Discount Nudge'),
        ('OWNER_NEGOTIATION_OPPORTUNITY', 'Owner: Negotiation Opportunity Generated'),
        ('OWNER_NEGOTIATION_PROPOSED', 'Owner: Negotiation Proposed'),
        ('OWNER_NEGOTIATION_COUNTERED', 'Owner: Negotiation Countered'),
        ('OWNER_NEGOTIATION_ACCEPTED', 'Owner: Negotiation Accepted'),
        ('OWNER_NEGOTIATION_REJECTED', 'Owner: Negotiation Rejected'),
        ('OWNER_INCENTIVE_GRANTED', 'Owner: Incentive Granted'),
    ]
    
    event_type = models.CharField(
        max_length=30,
        choices=EVENT_TYPES,
        db_index=True,
        help_text="Type of safety event"
    )
    
    # What was affected
    room_type = models.ForeignKey(
        'RoomType',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Room type involved (null if global event)"
    )
    hotel = models.ForeignKey(
        'Hotel',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Hotel involved (denormalized for fast queries)"
    )
    
    # Price data
    observed_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price that triggered the event"
    )
    safe_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Safe price used instead (if applicable)"
    )
    floor_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated floor price at time of event"
    )
    
    # Context
    reason = models.TextField(
        help_text="Human-readable explanation"
    )
    metadata_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context (thresholds, calculations, etc.)"
    )
    
    # Traceability
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Admin who triggered the event (if manual)"
    )
    source = models.CharField(
        max_length=50,
        default='system',
        help_text="Event source (system, admin, api, booking_flow, etc.)"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['room_type', '-created_at']),
            models.Index(fields=['hotel', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = "Pricing Safety Event"
        verbose_name_plural = "Pricing Safety Events"
    
    def __str__(self):
        return f"{self.get_event_type_display()} @ {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ShadowRiskEvent(TimeStampedModel):
    """
    Phase 2.7.3.1 — Shadow Mode Risk Observation
    
    Tracks "would have blocked" events during shadow mode observation period.
    Enables risk assessment before enforcement mode is enabled.
    """
    
    RISK_CATEGORIES = [
        ('FLOOR_RISK', 'Would-Block: Below Cost Floor'),
        ('ABSOLUTE_RISK', 'Would-Block: Below Absolute Minimum'),
        ('COMPETITOR_RISK', 'Would-Block: Bad Competitor Feed'),
        ('VELOCITY_RISK', 'Would-Block: Rapid Price Change'),
        ('CIRCUIT_RISK', 'Would-Block: Circuit Breaker'),
        ('MULTI_RISK', 'Would-Block: Multiple Violations'),
    ]
    
    risk_category = models.CharField(
        max_length=30,
        choices=RISK_CATEGORIES,
        help_text="Type of risk that would have been blocked"
    )
    
    hotel = models.ForeignKey(
        'Hotel',
        on_delete=models.CASCADE,
        help_text="Hotel affected"
    )
    room_type = models.ForeignKey(
        'RoomType',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Room type affected"
    )
    
    # Price context
    proposed_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price that would have been blocked"
    )
    safe_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Safe fallback price"
    )
    
    # Impact assessment
    reason = models.TextField(
        help_text="Why this price would have been blocked"
    )
    potential_revenue_impact = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated revenue loss if this booking was blocked"
    )
    booking_count_impact = models.IntegerField(
        default=1,
        help_text="Estimated bookings that would be affected"
    )
    
    # Severity tracking
    severity = models.CharField(
        max_length=20,
        choices=[
            ('LOW', 'Low Risk'),
            ('MEDIUM', 'Medium Risk'),
            ('HIGH', 'High Risk'),
            ('CRITICAL', 'Critical Risk'),
        ],
        default='MEDIUM',
        help_text="Risk severity level"
    )
    
    # Metadata
    metadata_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['risk_category', '-created_at']),
            models.Index(fields=['hotel', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
        ]
        verbose_name = "Shadow Risk Event"
        verbose_name_plural = "Shadow Risk Events"
    
    def __str__(self):
        return f"{self.get_risk_category_display()} - {self.hotel.name} (₹{self.proposed_price})"


class ShadowModeEvent(TimeStampedModel):
    """
    Shadow Mode Event - Tracks price anomalies detected without enforcement
    
    When shadow mode is enabled, detected price anomalies are logged
    but not enforced. This model stores those events for analysis.
    """
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name='shadow_events'
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shadow_events'
    )
    
    # Price comparison
    shadow_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price that would have been enforced in enforcement mode"
    )
    actual_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price actually used"
    )
    
    # Anomaly details
    anomaly_type = models.CharField(
        max_length=50,
        choices=[
            ('price_too_high', 'Price too high'),
            ('price_too_low', 'Price too low'),
            ('capacity_violation', 'Capacity violation'),
            ('inventory_mismatch', 'Inventory mismatch'),
        ]
    )
    
    anomaly_severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium'
    )
    
    # Context
    detection_source = models.CharField(
        max_length=50,
        choices=[
            ('ai_model', 'AI Model'),
            ('rule_engine', 'Rule Engine'),
            ('manual_review', 'Manual Review'),
        ],
        default='ai_model'
    )
    
    confidence_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Confidence in anomaly detection (0.0-1.0)"
    )
    
    metadata_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional detection metadata"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['room_type', '-created_at']),
            models.Index(fields=['anomaly_type', '-created_at']),
            models.Index(fields=['anomaly_severity', '-created_at']),
        ]
        verbose_name = "Shadow Mode Event"
        verbose_name_plural = "Shadow Mode Events"
    
    def __str__(self):
        return f"{self.get_anomaly_type_display()} - {self.room_type.name} (₹{self.shadow_price} vs ₹{self.actual_price})"


class SafetyConfidenceScore(TimeStampedModel):
    """
    Safety Confidence Score - Tracks system confidence in enforcement
    
    Composite score based on:
    - Data Quality (90-100 based on event count)
    - Pattern Recognition (70-100 based on exception patterns)
    - Risk Coverage (60-100 based on monitored hotels)
    
    Overall score >= 85% enables enforcement capability
    """
    
    # Period
    period_days = models.IntegerField(default=7)
    
    # Component scores
    data_quality_score = models.FloatField(default=0.0)
    pattern_recognition_score = models.FloatField(default=0.0)
    risk_coverage_score = models.FloatField(default=0.0)
    
    # Overall
    overall_score = models.FloatField(default=0.0)
    
    # Status
    is_enforcement_ready = models.BooleanField(default=False)
    
    # Details
    event_count = models.IntegerField(default=0)
    hotel_count = models.IntegerField(default=0)
    monitored_hotels = models.IntegerField(default=0)
    
    # Analysis metadata
    analysis_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed scoring breakdown"
    )
    
    recommendation = models.TextField(
        blank=True,
        help_text="Admin-facing recommendation"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Safety Confidence Score"
        verbose_name_plural = "Safety Confidence Scores"
    
    def __str__(self):
        status = "READY" if self.is_enforcement_ready else "MONITORING"
        return f"Confidence {self.overall_score}% - {status}"


class EnforcementMode(TimeStampedModel):
    """
    Enforcement Mode - Tracks pricing enforcement mode changes
    
    Modes:
    - SHADOW: Detect anomalies but don't enforce
    - ENFORCEMENT: Apply confidence score and enforce decisions
    - OFF: Disable pricing controls entirely
    """
    
    MODE_CHOICES = [
        ('SHADOW', 'Shadow Mode (detect only)'),
        ('ENFORCEMENT', 'Enforcement Mode (apply rules)'),
        ('OFF', 'Off (no controls)'),
    ]
    
    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default='SHADOW'
    )
    
    is_active = models.BooleanField(default=True)
    
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enforcement_mode_changes'
    )
    
    reason = models.TextField(
        blank=True,
        help_text="Why was this mode change made?"
    )
    
    metadata_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Enforcement Mode"
        verbose_name_plural = "Enforcement Modes"
    
    @classmethod
    def get_current_mode(cls):
        """Get the current active enforcement mode"""
        try:
            return cls.objects.filter(is_active=True).latest('created_at')
        except cls.DoesNotExist:
            # Default to SHADOW mode
            return cls.objects.create(
                mode='SHADOW',
                is_active=True,
                reason='System initialization'
            )
    
    def __str__(self):
        return f"{self.get_mode_display()} (set {self.created_at.strftime('%Y-%m-%d %H:%M')})"


class PricingException(TimeStampedModel):
    """
    Pricing Exception - Tracks pricing violations and rule exceptions
    
    Records instances where pricing rules were violated or needed exception handling.
    Used for pattern analysis and confidence scoring.
    """
    
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name='pricing_exceptions'
    )
    
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pricing_exceptions'
    )
    
    exception_type = models.CharField(
        max_length=50,
        choices=[
            ('margin_violation', 'Margin below threshold'),
            ('occupancy_violation', 'Occupancy exceeded'),
            ('price_gap_violation', 'Price gap too large'),
            ('competitor_match_failure', 'Competitor match failed'),
            ('inventory_mismatch', 'Inventory mismatch'),
        ]
    )
    
    violation_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="The problematic value (price, margin, etc.)"
    )
    
    threshold_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="The expected/allowed threshold"
    )
    
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        default='medium'
    )
    
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    metadata_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['room_type', '-created_at']),
            models.Index(fields=['exception_type', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
        ]
        verbose_name = "Pricing Exception"
        verbose_name_plural = "Pricing Exceptions"
    
    def __str__(self):
        return f"{self.get_exception_type_display()} - {self.room_type.name} ({self.get_severity_display()})"
