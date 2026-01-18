from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from core.models import TimeStampedModel, City
from core.soft_delete import SoftDeleteMixin, SoftDeleteManager, AllObjectsManager
from datetime import date


class BusOperator(SoftDeleteMixin, TimeStampedModel):
    """Bus operator/company with approval workflow (Session 3)"""
    VERIFICATION_STATUS = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]
    
    # Session 3: Approval Workflow FSM
    APPROVAL_STATUS = [
        ('draft', 'Draft (Incomplete)'),
        ('pending_verification', 'Pending Verification'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='buses/operators/', null=True, blank=True)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField()
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    # Registration & Verification (LEGACY - kept for compatibility)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bus_operator_profile')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_operators')
    
    # Business Details (MANDATORY)
    business_license = models.CharField(max_length=100, blank=True)
    pan_number = models.CharField(max_length=20, blank=True)
    gst_number = models.CharField(max_length=20, blank=True)
    registered_address = models.TextField(blank=True)
    
    # Session 3: Operator Identity (MANDATORY FOR SUBMISSION)
    company_legal_name = models.CharField(max_length=200, blank=True, help_text="Legal company name (e.g., ABC Tours Pvt Ltd)")
    operator_office_address = models.TextField(blank=True, help_text="Full office address")
    
    # Session 3: Bus Fleet Configuration (MANDATORY FOR SUBMISSION)
    bus_type = models.CharField(
        max_length=50, 
        blank=True,
        choices=[
            ('ac_seater', 'AC Seater'),
            ('non_ac_seater', 'Non-AC Seater'),
            ('sleeper', 'Sleeper'),
            ('semi_sleeper', 'Semi-Sleeper'),
        ],
        help_text="Primary bus type operated"
    )
    total_seats_per_bus = models.IntegerField(null=True, blank=True, help_text="Seats per bus")
    fleet_size = models.IntegerField(null=True, blank=True, help_text="Total number of buses")
    
    # Session 3: Route Configuration (MANDATORY FOR SUBMISSION)
    primary_source_city = models.ForeignKey(
        City, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='operators_from'
    )
    primary_destination_city = models.ForeignKey(
        City, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='operators_to'
    )
    routes_description = models.TextField(blank=True, help_text="Describe your routes, stops, and schedule")
    
    # Session 3: Pricing Configuration (MANDATORY FOR SUBMISSION)
    base_fare_per_seat = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Average base fare per seat"
    )
    gst_percentage = models.IntegerField(default=5, help_text="GST percentage")
    currency = models.CharField(max_length=3, default='INR')
    
    # Session 3: Policies (MANDATORY FOR SUBMISSION)
    cancellation_policy = models.TextField(blank=True, help_text="Detailed cancellation policy")
    cancellation_cutoff_hours = models.IntegerField(null=True, blank=True, help_text="Hours before departure for cancellation")
    refund_percentage = models.IntegerField(default=100, help_text="Refund percentage on cancellation")
    
    # Session 3: Amenities
    has_ac = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=False)
    has_charging_point = models.BooleanField(default=False)
    has_blanket = models.BooleanField(default=False)
    has_water_bottle = models.BooleanField(default=False)
    
    # Session 3: Approval Workflow (CRITICAL)
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS,
        default='draft',
        help_text="Operator approval state"
    )
    submitted_at = models.DateTimeField(null=True, blank=True, help_text="When operator submitted for approval")
    approved_at = models.DateTimeField(null=True, blank=True, help_text="When admin approved")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_bus_operators'
    )
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection (visible to operator)")
    admin_notes = models.TextField(blank=True, help_text="Internal admin notes")
    
    # Stats
    total_trips_completed = models.IntegerField(default=0)
    total_bookings = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    
    # Managers (soft delete support)
    objects = SoftDeleteManager()  # Default: excludes deleted
    all_objects = AllObjectsManager()  # Includes deleted
    
    class Meta:
        ordering = ['-rating', 'name']
        indexes = [
            models.Index(fields=['approval_status', 'is_active']),
            models.Index(fields=['user', 'approval_status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_approval_status_display()})"
    
    @property
    def is_approved(self):
        """Check if operator is approved and visible"""
        return self.approval_status == 'approved' and self.is_active
    
    @property
    def completion_percentage(self):
        """Calculate registration completeness"""
        required_fields = [
            self.company_legal_name, self.operator_office_address, self.contact_phone, self.contact_email,
            self.bus_type, self.total_seats_per_bus, self.fleet_size,
            self.primary_source_city, self.primary_destination_city,
            self.base_fare_per_seat, self.cancellation_policy, self.refund_percentage
        ]
        completed = sum(1 for field in required_fields if field)
        return int((completed / len(required_fields)) * 100)
    
    def has_required_fields(self):
        """Validate all required fields for submission"""
        checks = {
            'identity': bool(self.company_legal_name and self.company_legal_name.strip() and 
                           self.operator_office_address and self.operator_office_address.strip() and
                           self.contact_phone and self.contact_email),
            'bus_details': bool(self.bus_type and self.total_seats_per_bus and self.total_seats_per_bus > 0 and 
                              self.fleet_size and self.fleet_size > 0),
            'routes': bool(self.primary_source_city and self.primary_destination_city and 
                         self.routes_description and self.routes_description.strip()),
            'pricing': bool(self.base_fare_per_seat and self.base_fare_per_seat > 0),
            'policies': bool(self.cancellation_policy and self.cancellation_policy.strip()),
        }
        return checks, all(checks.values())


class Bus(TimeStampedModel):
    """Bus model"""
    BUS_TYPES = [
        ('seater', 'Seater'),
        ('sleeper', 'Sleeper'),
        ('semi_sleeper', 'Semi-Sleeper'),
        ('ac_seater', 'AC Seater'),
        ('ac_sleeper', 'AC Sleeper'),
        ('volvo', 'Volvo'),
        ('luxury', 'Luxury'),
    ]
    
    operator = models.ForeignKey(BusOperator, on_delete=models.CASCADE, related_name='buses')
    bus_number = models.CharField(max_length=50, unique=True)
    bus_name = models.CharField(max_length=200)
    bus_type = models.CharField(max_length=20, choices=BUS_TYPES)
    
    total_seats = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Bus Details (Industry Standard)
    manufacturing_year = models.IntegerField(null=True, blank=True, help_text="Year of manufacturing")
    registration_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    chassis_number = models.CharField(max_length=100, blank=True)
    
    # Amenities
    has_ac = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=False)
    has_charging_point = models.BooleanField(default=False)
    has_blanket = models.BooleanField(default=False)
    has_water_bottle = models.BooleanField(default=False)
    has_tv = models.BooleanField(default=False)
    has_reading_light = models.BooleanField(default=False)
    has_emergency_exit = models.BooleanField(default=True)
    has_first_aid = models.BooleanField(default=True)
    has_gps_tracking = models.BooleanField(default=False)
    has_cctv = models.BooleanField(default=False)
    
    # Ratings & Reviews
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    total_reviews = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['operator', 'bus_number']
    
    def __str__(self):
        return f"{self.operator.name} - {self.bus_number}"
    
    @property
    def bus_age(self):
        """Calculate bus age in years"""
        if self.manufacturing_year:
            return date.today().year - self.manufacturing_year
        return None
    
    def get_amenities_list(self):
        """Get list of amenities"""
        amenities = []
        if self.has_ac: amenities.append('AC')
        if self.has_wifi: amenities.append('WiFi')
        if self.has_charging_point: amenities.append('Charging Point')
        if self.has_blanket: amenities.append('Blanket')
        if self.has_water_bottle: amenities.append('Water Bottle')
        if self.has_tv: amenities.append('TV')
        if self.has_reading_light: amenities.append('Reading Light')
        if self.has_emergency_exit: amenities.append('Emergency Exit')
        if self.has_first_aid: amenities.append('First Aid')
        if self.has_gps_tracking: amenities.append('GPS Tracking')
        if self.has_cctv: amenities.append('CCTV')
        return amenities
    
    def get_primary_image(self):
        """Get primary image or fallback to first image"""
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.image
        first_image = self.images.first()
        if first_image:
            return first_image.image
        return None
    
    def _image_exists(self, image):
        """Check if image file exists"""
        if not image:
            return False
        try:
            return image.storage.exists(image.name)
        except Exception:
            return False
    
    @property
    def primary_image_url(self):
        """Get primary image URL"""
        image = self.get_primary_image()
        if self._image_exists(image):
            try:
                return image.url
            except Exception:
                return ''
        return ''
    
    @property
    def display_image_url(self):
        """Get display image URL with fallback"""
        from django.templatetags.static import static
        return self.primary_image_url or static('images/bus_placeholder.svg')


class BusImage(models.Model):
    """Gallery images for buses (Phase 3: Multi-image support)"""
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='buses/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    alt_text = models.CharField(max_length=200, blank=True, help_text="Alternative text for accessibility")
    display_order = models.IntegerField(default=0, help_text="Display order (lower numbers first)")
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['display_order', 'id']
    
    def __str__(self):
        return f"{self.bus.bus_name} - Image"


class BusRoute(TimeStampedModel):
    """Bus route between cities"""
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='routes')
    route_name = models.CharField(max_length=200)
    
    source_city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='bus_routes_from')
    destination_city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='bus_routes_to')
    
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    duration_hours = models.DecimalField(max_digits=5, decimal_places=2)
    distance_km = models.DecimalField(max_digits=7, decimal_places=2)
    
    base_fare = models.DecimalField(max_digits=10, decimal_places=2)
    
    is_active = models.BooleanField(default=True)
    
    # Days of operation
    operates_monday = models.BooleanField(default=True)
    operates_tuesday = models.BooleanField(default=True)
    operates_wednesday = models.BooleanField(default=True)
    operates_thursday = models.BooleanField(default=True)
    operates_friday = models.BooleanField(default=True)
    operates_saturday = models.BooleanField(default=True)
    operates_sunday = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['source_city', 'destination_city', 'departure_time']
    
    def __str__(self):
        return f"{self.source_city.name} to {self.destination_city.name} - {self.departure_time}"
    
    def get_available_seats(self, date):
        """Get available seats for a specific date"""
        schedule = self.schedules.filter(date=date, is_active=True).first()
        if schedule:
            return schedule.available_seats
        return self.bus.total_seats
    
    def calculate_fare(self, num_seats, convenience_fee_pct=2.0, gst_pct=5.0):
        """
        Calculate total fare for given number of seats
        
        Args:
            num_seats: Number of seats to book
            convenience_fee_pct: Convenience fee percentage (default 2%)
            gst_pct: GST percentage (default 5%)
        
        Returns:
            dict with base, fee, gst, total amounts
        """
        from decimal import Decimal
        
        base_fare = Decimal(str(self.base_fare)) * Decimal(str(num_seats))
        conv_fee = base_fare * Decimal(str(convenience_fee_pct)) / Decimal('100')
        gst = (base_fare + conv_fee) * Decimal(str(gst_pct)) / Decimal('100')
        total = base_fare + conv_fee + gst
        
        return {
            'base_fare': float(base_fare),
            'convenience_fee': float(conv_fee),
            'gst': float(gst),
            'total': float(total),
            'num_seats': num_seats,
            'per_seat': float(self.base_fare),
        }


class BoardingPoint(models.Model):
    """Boarding points for bus routes (RedBus/AbhiBus style)"""
    route = models.ForeignKey(BusRoute, on_delete=models.CASCADE, related_name='boarding_points')
    name = models.CharField(max_length=200, help_text="e.g., Majestic Bus Stand, Electronic City")
    address = models.TextField()
    landmark = models.CharField(max_length=200, blank=True, help_text="Nearby landmark")
    
    # Location
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Timing
    pickup_time = models.TimeField(help_text="Pickup time at this point")
    
    # Contact
    contact_person = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    
    # Display order
    sequence_order = models.IntegerField(default=1, help_text="Order of pickup points")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['route', 'sequence_order', 'pickup_time']
        unique_together = ['route', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.pickup_time.strftime('%H:%M')}"


class DroppingPoint(models.Model):
    """Dropping points for bus routes (RedBus/AbhiBus style)"""
    route = models.ForeignKey(BusRoute, on_delete=models.CASCADE, related_name='dropping_points')
    name = models.CharField(max_length=200, help_text="e.g., Koyambedu, CMBT")
    address = models.TextField()
    landmark = models.CharField(max_length=200, blank=True, help_text="Nearby landmark")
    
    # Location
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Timing
    drop_time = models.TimeField(help_text="Drop time at this point")
    
    # Contact
    contact_person = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    
    # Display order
    sequence_order = models.IntegerField(default=1, help_text="Order of drop points")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['route', 'sequence_order', 'drop_time']
        unique_together = ['route', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.drop_time.strftime('%H:%M')}"


class BusStop(models.Model):
    """Intermediate stops for a bus route"""
    route = models.ForeignKey(BusRoute, on_delete=models.CASCADE, related_name='stops')
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    stop_name = models.CharField(max_length=200)
    stop_order = models.IntegerField()
    arrival_time = models.TimeField()
    departure_time = models.TimeField()
    
    class Meta:
        ordering = ['route', 'stop_order']
        unique_together = ['route', 'stop_order']
    
    def __str__(self):
        return f"{self.route} - {self.stop_name}"


class BusSchedule(TimeStampedModel):
    """Bus schedule for specific dates - tracks daily availability"""
    route = models.ForeignKey(BusRoute, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    available_seats = models.IntegerField(help_text="Seats currently available")
    booked_seats = models.IntegerField(default=0, help_text="Seats already booked")
    
    fare = models.DecimalField(max_digits=10, decimal_places=2, help_text="Dynamic pricing per seat")
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)
    
    # Window seat pricing (premium)
    window_seat_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['route', 'date']
        ordering = ['date']
    
    def __str__(self):
        available = self.available_seats or 0
        return f"{self.route} - {self.date} ({available} seats left)"
    
    def book_seats(self, num_seats):
        """Book seats and update availability"""
        available = self.available_seats or 0
        if available >= num_seats:
            self.available_seats = (available - num_seats)
            self.booked_seats = (self.booked_seats or 0) + num_seats
            self.save()
            return True
        return False
    
    @property
    def occupancy_percentage(self):
        """Calculate occupancy percentage"""
        available = self.available_seats or 0
        booked = self.booked_seats or 0
        total = available + booked
        if total > 0:
            return round((booked / total) * 100, 1)
        return 0
    
    @property
    def is_almost_full(self):
        """Check if bus is almost full (>80% booked)"""
        return self.occupancy_percentage > 80


class SeatLayout(models.Model):
    """Seat layout for buses"""
    SEAT_TYPES = [
        ('seater', 'Seater'),
        ('sleeper_lower', 'Sleeper Lower'),
        ('sleeper_upper', 'Sleeper Upper'),
    ]
    
    RESERVED_FOR_CHOICES = [
        ('general', 'General'),
        ('ladies', 'Ladies Only'),
        ('disabled', 'Disabled'),
    ]
    
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='seat_layout')
    seat_number = models.CharField(max_length=10)
    seat_type = models.CharField(max_length=20, choices=SEAT_TYPES)
    row = models.IntegerField()
    column = models.IntegerField()
    deck = models.IntegerField(default=1)  # 1 for lower deck, 2 for upper deck
    
    # Ladies seat reservation
    reserved_for = models.CharField(max_length=20, choices=RESERVED_FOR_CHOICES, default='general', 
                                     help_text="Reserve seats for specific passenger types")
    
    class Meta:
        unique_together = ['bus', 'seat_number']
        ordering = ['deck', 'row', 'column']
    
    def __str__(self):
        return f"{self.bus.bus_number} - Seat {self.seat_number} ({self.get_reserved_for_display()})"
    
    def can_be_booked_by(self, passenger_gender):
        """Check if seat can be booked by passenger gender"""
        if self.reserved_for == 'general':
            return True
        elif self.reserved_for == 'ladies':
            return passenger_gender == 'F'  # Only females can book ladies seats
        elif self.reserved_for == 'disabled':
            return True  # Disabled passengers can book disabled seats
        return False
