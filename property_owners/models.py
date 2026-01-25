from django.db import models
from django.conf import settings
from core.models import TimeStampedModel, City


class PropertyType(models.Model):
    """Types of properties"""
    TYPES = [
        ('homestay', 'Homestay'),
        ('resort', 'Resort'),
        ('villa', 'Villa'),
        ('guesthouse', 'Guest House'),
        ('farmstay', 'Farm Stay'),
        ('houseboat', 'Houseboat'),
    ]
    
    name = models.CharField(max_length=50, choices=TYPES, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.get_name_display()


class PropertyOwner(TimeStampedModel):
    """Property owner profile for homestays, resorts, villas"""
    VERIFICATION_STATUS = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='property_owner_profile')
    
    # Business Details
    business_name = models.CharField(max_length=200)
    property_type = models.ForeignKey(PropertyType, on_delete=models.SET_NULL, null=True)
    description = models.TextField(help_text="Description of your property")
    
    # Owner Details
    owner_name = models.CharField(max_length=200)
    owner_phone = models.CharField(max_length=20)
    owner_email = models.EmailField()
    
    # Property Location
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    address = models.TextField()
    pincode = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Legal Details
    gst_number = models.CharField(max_length=20, blank=True, help_text="Optional: GST registration number")
    pan_number = models.CharField(max_length=20, blank=True, help_text="Optional: PAN for tax purposes")
    business_license = models.CharField(max_length=100, blank=True)
    
    # Bank Details
    bank_account_name = models.CharField(max_length=200, blank=True)
    bank_account_number = models.CharField(max_length=20, blank=True)
    bank_ifsc = models.CharField(max_length=20, blank=True)
    
    # Verification
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_property_owners')
    verification_notes = models.TextField(blank=True)
    
    # Ratings
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.IntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.business_name} by {self.owner_name}"


class Property(TimeStampedModel):
    """Individual property listings with approval workflow"""
    
    # State Machine (Phase-2)
    PROPERTY_STATUS = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    owner = models.ForeignKey(PropertyOwner, on_delete=models.CASCADE, related_name='properties')
    
    # Core Details (MANDATORY)
    name = models.CharField(max_length=200)
    description = models.TextField()
    property_type = models.ForeignKey(PropertyType, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Location (MANDATORY)
    city = models.ForeignKey(City, on_delete=models.PROTECT, null=True, blank=True)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Contact (MANDATORY)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    
    # Rules & Policies (MANDATORY - stored as JSON for flexibility)
    checkin_time = models.TimeField(null=True, blank=True, help_text="e.g., 14:00")
    checkout_time = models.TimeField(null=True, blank=True, help_text="e.g., 11:00")
    property_rules = models.TextField(blank=True, help_text="Check-in/out policies, pets, smoking, etc.")
    
    # Cancellation Policy (MANDATORY)
    cancellation_policy = models.TextField(blank=True)
    cancellation_type = models.CharField(max_length=50, blank=True, choices=[
        ('no_cancellation', 'No Cancellation'),
        ('until_checkin', 'Free cancellation until check-in'),
        ('x_days_before', 'Free cancellation X days before check-in'),
    ])
    cancellation_days = models.IntegerField(null=True, blank=True)
    refund_percentage = models.IntegerField(default=100, help_text="Refund percentage")
    has_wifi = models.BooleanField(default=False)
    has_parking = models.BooleanField(default=False)
    has_pool = models.BooleanField(default=False)
    has_gym = models.BooleanField(default=False)
    has_restaurant = models.BooleanField(default=False)
    has_spa = models.BooleanField(default=False)
    has_ac = models.BooleanField(default=False)
    amenities = models.TextField(blank=True, help_text="Additional amenities (free text)")
    
    # Pricing (MANDATORY)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Price per night")
    currency = models.CharField(max_length=3, default='INR')
    gst_percentage = models.IntegerField(default=18)
    
    # Capacity (MANDATORY)
    max_guests = models.IntegerField(default=2)
    num_bedrooms = models.IntegerField(default=1)
    num_bathrooms = models.IntegerField(default=1)
    
    # Media (MANDATORY - minimum images required)
    image = models.ImageField(upload_to='properties/', null=True, blank=True)
    
    # Rating & Reviews
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.IntegerField(default=0)
    
    # Approval Workflow (Phase-2)
    status = models.CharField(
        max_length=20,
        choices=PROPERTY_STATUS,
        default='DRAFT',
        db_index=True,
        help_text="DRAFT → PENDING → APPROVED/REJECTED"
    )
    submitted_at = models.DateTimeField(null=True, blank=True, help_text="When owner submitted for verification")
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_properties')
    rejection_reason = models.TextField(null=True, blank=True, help_text="Reason for rejection (visible to owner)")
    admin_notes = models.TextField(blank=True, help_text="Internal admin notes (not visible to owner)")
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-is_featured', '-average_rating', 'name']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['owner', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} by {self.owner.business_name} [{self.get_status_display()}]"
    
    @property
    def is_approved(self):
        """Check if property is approved (used in booking queries)"""
        # Backward compatibility: treat both fields; prefer new status
        if hasattr(self, 'status'):
            return self.status == 'APPROVED' and self.is_active
        return getattr(self, 'approval_status', None) == 'approved' and self.is_active

    def submit_for_approval(self):
        from django.utils import timezone
        assert self.status in ['DRAFT', 'REJECTED'], "Submit allowed only from DRAFT or REJECTED"
        assert self.room_types.exists(), "At least one room type required"
        old = self.status
        self.status = 'PENDING'
        self.submitted_at = timezone.now()
        self.save(update_fields=['status', 'submitted_at'])
        self.log_status_change(old, self.status, event='PROPERTY_SUBMITTED')

    def approve(self, admin_user):
        from django.db import transaction
        from django.utils import timezone
        from decimal import Decimal
        from hotels.models import Hotel, RoomType, HotelImage, RoomImage
        assert self.status == 'PENDING', "Approve allowed only from PENDING"
        assert self.room_types.exists(), "At least one room type required before approval"
        assert self.images.filter(is_primary=True).exists() or self.image or self.room_types.filter(images__is_primary=True).exists(), "At least one primary image required before approval"
        with transaction.atomic():
            # Create/update Hotel linked to this Property
            hotel = Hotel.objects.filter(owner_property=self).first()
            if not hotel:
                hotel = Hotel(
                    owner_property=self,
                    name=self.name,
                    description=self.description,
                    city=self.city,
                    address=self.address or '',
                    contact_phone=self.contact_phone or '',
                    contact_email=self.contact_email or '',
                    gst_percentage=Decimal(str(self.gst_percentage or 18)),
                    is_active=True,
                )
            else:
                hotel.name = self.name
                hotel.description = self.description
                hotel.city = self.city
                hotel.address = self.address or ''
                hotel.contact_phone = self.contact_phone or ''
                hotel.contact_email = self.contact_email or ''
                hotel.gst_percentage = Decimal(str(self.gst_percentage or 18))
                hotel.is_active = True
            hotel.owner_property = self
            hotel.property_rules = self.property_rules or ''
            hotel.cancellation_policy = self.cancellation_policy or ''
            hotel.has_wifi = bool(getattr(self, 'has_wifi', False))
            hotel.has_parking = bool(getattr(self, 'has_parking', False))
            hotel.has_pool = bool(getattr(self, 'has_pool', False))
            hotel.has_gym = bool(getattr(self, 'has_gym', False))
            hotel.has_restaurant = bool(getattr(self, 'has_restaurant', False))
            hotel.has_spa = bool(getattr(self, 'has_spa', False))
            hotel.has_ac = bool(getattr(self, 'has_ac', True))
            hotel.save()

            # Sync property images → HotelImage
            for pimg in self.images.all():
                try:
                    himg = HotelImage.objects.filter(hotel=hotel, image=pimg.image).first()
                    if not himg:
                        himg = HotelImage(hotel=hotel, image=pimg.image)
                    himg.caption = pimg.caption or ''
                    himg.is_primary = bool(pimg.is_primary)
                    himg.category = 'property'
                    himg.save()
                except Exception:
                    continue

            # Sync PropertyRoomType → RoomType
            for pr in self.room_types.all():
                r = RoomType.objects.filter(hotel=hotel, name=pr.name).first()
                if not r:
                    r = RoomType(hotel=hotel, name=pr.name)
                r.description = pr.description or ''
                r.room_size = pr.room_size or 200
                r.base_price = Decimal(str(pr.base_price or 0))
                r.max_occupancy = pr.max_occupancy or 2
                r.max_adults = max(1, min(r.max_occupancy, 2))
                r.max_children = max(0, r.max_occupancy - r.max_adults)
                r.number_of_beds = pr.number_of_beds or 1
                r.bed_type = 'double'
                r.total_rooms = pr.total_rooms or 1
                r.discount_type = pr.discount_type or 'none'
                r.discount_value = Decimal(str(pr.discount_value or 0))
                r.discount_valid_from = pr.discount_valid_from
                r.discount_valid_to = pr.discount_valid_to
                r.discount_is_active = bool(pr.discount_is_active)
                r.is_refundable = True
                r.is_available = True
                r.status = 'APPROVED'
                r.save()

                # Sync room images
                try:
                    for primg in pr.images.all():
                        ri = RoomImage.objects.filter(room_type=r, image=primg.image).first()
                        if not ri:
                            ri = RoomImage(room_type=r, image=primg.image)
                        ri.is_primary = bool(primg.is_primary)
                        ri.display_order = primg.display_order
                        ri.save()
                except Exception:
                    pass

            # Finalize approval
            old = self.status
            self.status = 'APPROVED'
            self.approved_at = timezone.now()
            self.approved_by = admin_user
            self.rejection_reason = None
            self.save(update_fields=['status', 'approved_at', 'approved_by', 'rejection_reason'])
            self.log_status_change(old, self.status, event='PROPERTY_APPROVED', actor_id=getattr(admin_user, 'id', None))

    def reject(self, reason):
        assert str(reason).strip(), "Rejection reason required"
        old = self.status
        self.status = 'REJECTED'
        self.rejection_reason = reason
        self.save(update_fields=['status', 'rejection_reason'])
        self.log_status_change(old, self.status, event='PROPERTY_REJECTED')

    def mark_pending_on_edit(self, actor_id=None):
        if self.status == 'APPROVED':
            old = self.status
            self.status = 'PENDING'
            self.save(update_fields=['status'])
            self.log_status_change(old, self.status, event='PROPERTY_STATUS_CHANGED', actor_id=actor_id)

    def log_status_change(self, old_status, new_status, event='PROPERTY_STATUS_CHANGED', actor_id=None):
        import logging
        logger = logging.getLogger('property_approval')
        logger.info(
            f"[{event}] property_id={self.id} old_status={old_status} new_status={new_status} actor_id={actor_id}"
        )
    
    @property
    def completion_percentage(self):
        """Calculate property submission completeness"""
        required_fields = [
            self.name, self.description, self.property_type,
            self.city, self.address, self.pincode, self.contact_phone, self.contact_email,
            self.property_rules, self.cancellation_policy,
            self.base_price, self.max_guests, self.num_bedrooms
        ]
        completed = sum(1 for field in required_fields if field)
        return int((completed / len(required_fields)) * 100)

    @property
    def total_room_inventory(self):
        """Total number of sellable rooms across all room types."""
        if not self.pk:
            return 0
        from django.db.models import Sum
        return self.room_types.aggregate(total=Sum('total_rooms')).get('total') or 0
    
    def has_required_fields(self):
        """Strict validation using PropertyRoomType fields (pre-approval).
        Admin approval is disabled unless:
        - Each room: room_size>0, number_of_beds>=1, max_occupancy>=1, base_price>0
        - Each room: >=3 images (PropertyRoomImage)
        - Each room: meal_plans list non-empty
        - Property core fields present
        Returns (checks, is_complete)
        """
        room_issues = []
        
        # CRITICAL: Must have at least one room
        if not self.pk:
            return {'error': 'Property not saved'}, False
        
        rooms = self.room_types.all()
        if not rooms.exists():
            return {'error': 'No rooms added'}, False
        
        for room in rooms:
            issues = []
            if not room.room_size or room.room_size <= 0:
                issues.append('room_size')
            if not room.number_of_beds or room.number_of_beds < 1:
                issues.append('number_of_beds')
            if not room.max_occupancy or room.max_occupancy < 1:
                issues.append('max_occupancy')
            if not room.base_price or room.base_price <= 0:
                issues.append('base_price')
            image_count = room.images.count() if hasattr(room, 'images') else 0
            if image_count < 3:
                issues.append(f'images={image_count}_need_3')
            try:
                plans = room.meal_plans or []
            except Exception:
                plans = []
            if not plans or len(plans) == 0:
                issues.append('meal_plan_missing')
            if issues:
                room_issues.append(f"{room.name}: {', '.join(issues)}")
        
        # HOTEL-LEVEL (optional pre-approval): policies may be added later
        has_policies = True
        
        # Basic hotel fields
        room_primary_exists = any(r.images.filter(is_primary=True).exists() for r in rooms)
        checks = {
            'name': bool(self.name and self.name.strip()),
            'description': bool(self.description and self.description.strip()),
            'city': self.city is not None,
            'contact_phone': bool(self.contact_phone),
            'contact_email': bool(self.contact_email),
            'images': self.images.filter(is_primary=True).exists() or bool(self.image) or room_primary_exists,
            'rooms': True,  # Already validated above
            'rooms_complete': len(room_issues) == 0,
            'policies': has_policies,
        }
        
        # Add room issues for display
        if room_issues:
            checks['room_issues'] = room_issues
        
        is_complete = all(checks.values())
        return checks, is_complete


class PropertyBooking(TimeStampedModel):
    """Booking for properties"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    property = models.ForeignKey(Property, on_delete=models.PROTECT, related_name='bookings')
    guest_name = models.CharField(max_length=200)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=20)
    
    check_in = models.DateField()
    check_out = models.DateField()
    num_guests = models.IntegerField(default=1)
    
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    special_requests = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Booking at {self.property.name} by {self.guest_name}"


class PropertyImage(TimeStampedModel):
    """Images for a property listing"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/', null=True, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.property.name}"


class PropertyAmenity(models.Model):
    """Catalog of amenities that properties can reference"""
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True)
    icon = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name

# ============================================================================
# ROLE-BASED SYSTEM FOR PRODUCTION SCALABILITY
# ============================================================================

class UserRole(models.Model):
    """User role assignments for multi-tenant system"""
    ROLE_CHOICES = [
        ('admin', 'Platform Admin'),
        ('property_owner', 'Property Owner'),
        ('operator', 'Bus Operator'),
        ('corporate', 'Corporate Partner'),
        ('employee', 'Employee'),
        ('customer', 'Customer'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_role')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "User Roles"
    
    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()}"


class PropertyUpdateRequest(TimeStampedModel):
    """Property owners submit updates for admin approval (production workflow)"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    CHANGE_TYPES = [
        ('room_types', 'Room Types'),
        ('pricing', 'Pricing'),
        ('images', 'Images'),
        ('amenities', 'Amenities'),
        ('rules', 'Rules'),
        ('meal_plans', 'Meal Plans'),
        ('discount', 'Property Discount'),
    ]
    
    owner = models.ForeignKey(PropertyOwner, on_delete=models.CASCADE, related_name='update_requests')
    property = models.ForeignKey('Property', on_delete=models.CASCADE, related_name='update_requests', null=True, blank=True)
    room_type = models.ForeignKey('PropertyRoomType', on_delete=models.CASCADE, related_name='room_update_requests', null=True, blank=True)

    change_type = models.CharField(max_length=50, choices=CHANGE_TYPES)
    owner_remark = models.TextField(blank=True)
    admin_remark = models.TextField(blank=True)

    title = models.CharField(max_length=200)
    description = models.TextField()
    old_data = models.JSONField(default=dict, blank=True)
    new_data = models.JSONField(default=dict)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_property_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def _apply_property_changes(self):
        """Apply changes stored in new_data to the target property/room"""
        from decimal import Decimal
        if self.property:
            allowed_fields = ['property_rules', 'amenities', 'base_price', 'gst_percentage', 'discount_type', 'discount_value']
            target = self.property
            for field, value in self.new_data.items():
                if field not in allowed_fields:
                    continue
                if field in ['base_price', 'discount_value'] and value is not None:
                    try:
                        value = Decimal(str(value))
                    except Exception:
                        continue
                setattr(target, field, value)
            target.save()
        if self.room_type:
            allowed_room_fields = [
                'base_price', 'discount_type', 'discount_value', 'discount_valid_from', 'discount_valid_to',
                'discount_is_active', 'amenities', 'meal_plans', 'room_size', 'number_of_beds', 'max_occupancy',
                'total_rooms'
            ]
            room = self.room_type
            for field, value in self.new_data.items():
                if field not in allowed_room_fields:
                    continue
                if field in ['base_price', 'discount_value'] and value is not None:
                    try:
                        value = Decimal(str(value))
                    except Exception:
                        continue
                setattr(room, field, value)
            room.save()

    def approve(self, admin_user):
        """Approve, apply, and audit changes"""
        from django.utils import timezone
        self._apply_property_changes()
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.admin_remark = self.admin_remark or ''
        self.save()
    
    def reject(self, admin_user, reason=''):
        """Reject update request"""
        from django.utils import timezone
        self.status = 'rejected'
        self.rejection_reason = reason
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.owner.business_name} - {self.get_change_type_display()} ({self.get_status_display()})"


class RoomUpdateRequest(TimeStampedModel):
    """Fine-grained room update requests (per-room audit)"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    owner = models.ForeignKey(PropertyOwner, on_delete=models.CASCADE, related_name='room_update_requests')
    room_type = models.ForeignKey('PropertyRoomType', on_delete=models.CASCADE, related_name='pending_updates')
    change_type = models.CharField(max_length=50, choices=[
        ('pricing', 'Pricing'),
        ('images', 'Images'),
        ('amenities', 'Amenities'),
        ('meal_plans', 'Meal Plans'),
    ])
    owner_remark = models.TextField(blank=True)
    admin_remark = models.TextField(blank=True)
    old_data = models.JSONField(default=dict, blank=True)
    new_data = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_room_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def apply_changes(self):
        from decimal import Decimal
        room = self.room_type
        for field, value in self.new_data.items():
            if field in ['base_price', 'discount_value'] and value is not None:
                try:
                    value = Decimal(str(value))
                except Exception:
                    continue
            setattr(room, field, value)
        room.save()

    def approve(self, admin_user):
        from django.utils import timezone
        self.apply_changes()
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self, admin_user, reason=''):
        from django.utils import timezone
        self.status = 'rejected'
        self.rejection_reason = reason
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.room_type.name} update ({self.get_status_display()})"


class PropertyRoomType(TimeStampedModel):
    """
    Room types for properties (Phase-2 architecture).
    Separate from hotels.RoomType to support property self-service.
    """
    ROOM_TYPES = [
        ('standard', 'Standard Room'),
        ('deluxe', 'Deluxe Room'),
        ('suite', 'Suite'),
        ('family', 'Family Room'),
        ('dormitory', 'Dormitory'),
    ]
    
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='room_types')
    
    # Room Details
    name = models.CharField(max_length=100, help_text="Room type name (e.g., Deluxe Ocean View)")
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='standard')
    description = models.TextField(help_text="Room description, features, view details")
    
    # Capacity
    max_occupancy = models.PositiveIntegerField(default=2)
    number_of_beds = models.PositiveIntegerField(default=1)
    room_size = models.PositiveIntegerField(null=True, blank=True, help_text="Size in square feet")
    
    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base price per night")
    DISCOUNT_TYPES = [
        ('none', 'No Discount'),
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPES,
        default='none',
        help_text="Choose either percentage or flat discount (mutually exclusive)."
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Discount value based on discount type."
    )
    discount_valid_from = models.DateField(null=True, blank=True)
    discount_valid_to = models.DateField(null=True, blank=True)
    discount_is_active = models.BooleanField(default=False)
    
    # Inventory
    total_rooms = models.PositiveIntegerField(help_text="Total number of this room type available")
    
    # Amenities (JSON field for flexibility)
    amenities = models.JSONField(
        default=list,
        help_text="Room-specific amenities (balcony, TV, minibar, safe, etc.)"
    )
    
    # Meal Plans (owner-defined per room type)
    # Structure: [{"type": "room_only", "price": 2500.00}, ...]
    meal_plans = models.JSONField(
        default=list,
        help_text="List of meal plans with absolute per-night pricing for this room"
    )
    
    # Images
    image = models.ImageField(upload_to='property_rooms/', null=True, blank=True, help_text="Legacy primary image")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['property', 'base_price']
        verbose_name = "Property Room Type"
        verbose_name_plural = "Property Room Types"
    
    def __str__(self):
        return f"{self.property.name} - {self.name}"

    class ApprovedQuerySet(models.QuerySet):
        def visible(self):
            return self.filter(property__status='APPROVED', property__is_active=True)

    objects = ApprovedQuerySet.as_manager()
    
    def current_price(self):
        """Get current effective price (discounted if available, else base)"""
        return self.get_effective_price()
    
    def has_discount(self):
        """Check if room has an active discount"""
        return self._is_discount_window_active() and self.discount_type != 'none'

    def _is_discount_window_active(self):
        from datetime import date
        if not self.discount_is_active or self.discount_type == 'none':
            return False
        today = date.today()
        if self.discount_valid_from and today < self.discount_valid_from:
            return False
        if self.discount_valid_to and today > self.discount_valid_to:
            return False
        return True

    def get_effective_price(self):
        from decimal import Decimal
        amount = Decimal(self.base_price or 0)
        if not self._is_discount_window_active():
            return amount
        if self.discount_type == 'percentage':
            discount_amt = (amount * Decimal(self.discount_value)) / Decimal('100')
        elif self.discount_type == 'fixed':
            discount_amt = Decimal(self.discount_value)
        else:
            discount_amt = Decimal('0')
        final = amount - discount_amt
        return final if final > Decimal('0') else Decimal('0')


class PropertyRoomImage(TimeStampedModel):
    """Multiple images per property room type (owner-managed).
    
    GUARANTEE: Exactly one primary image per room_type at all times.
    - If saving with is_primary=True, demote all others for this room
    - If saving first image with no primary, auto-set as primary
    """

    room_type = models.ForeignKey(PropertyRoomType, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_rooms/gallery/')
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
            PropertyRoomImage.objects.filter(room_type=self.room_type).exclude(pk=self.pk).update(is_primary=False)
        # If no primary exists for this room and this is being saved, set as primary
        elif self.room_type.images.filter(is_primary=True).count() == 0:
            self.is_primary = True
        
        super().save(*args, **kwargs)


class SeasonalPricing(TimeStampedModel):
    """Seasonal pricing managed by property owner"""
    room_type = models.ForeignKey('hotels.RoomType', on_delete=models.CASCADE, related_name='seasonal_pricing')
    owner = models.ForeignKey(PropertyOwner, on_delete=models.CASCADE)
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    occupancy_threshold = models.IntegerField(default=70, help_text="Min occupancy % to apply discount")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def effective_price(self, occupancy_percentage=100):
        """Get effective price based on occupancy threshold"""
        from decimal import Decimal
        if occupancy_percentage >= self.occupancy_threshold:
            discount_amount = self.base_price * Decimal(self.discount_percentage) / Decimal('100')
            return self.base_price - discount_amount
        return self.base_price
    
    def __str__(self):
        return f"{self.room_type} - {self.start_date} to {self.end_date}"


class AdminApprovalLog(TimeStampedModel):
    """Log of all admin approvals for audit trail"""
    APPROVAL_TYPE_CHOICES = [
        ('property_owner', 'Property Owner Verification'),
        ('update_request', 'Update Request'),
        ('image', 'Image Upload'),
        ('pricing', 'Pricing Change'),
    ]
    
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='approval_logs')
    approval_type = models.CharField(max_length=50, choices=APPROVAL_TYPE_CHOICES)
    
    subject = models.CharField(max_length=255)
    details = models.JSONField(default=dict)
    
    decision = models.CharField(max_length=20, choices=[('approved', 'Approved'), ('rejected', 'Rejected')])
    reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_approval_type_display()} - {self.decision} on {self.created_at.date()}"