from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import BusOperator, Bus, BusImage, BusRoute, BusStop, BusSchedule, SeatLayout, BoardingPoint, DroppingPoint
from core.admin_mixins import PrimaryImageValidationMixin


class BusImageInline(admin.TabularInline):
    """Gallery images for buses (Phase 3)"""
    model = BusImage
    extra = 1
    fields = ['image', 'caption', 'alt_text', 'display_order', 'is_primary']


def verify_operator(modeladmin, request, queryset):
    """Admin action to verify bus operators"""
    from django.utils import timezone
    updated = queryset.update(
        verification_status='verified', 
        verified_at=timezone.now(),
        verified_by=request.user
    )
    modeladmin.message_user(request, f"{updated} operator(s) verified successfully!")

verify_operator.short_description = "✅ Verify selected operators"


def reject_operator(modeladmin, request, queryset):
    """Admin action to reject bus operators"""
    updated = queryset.update(verification_status='rejected')
    modeladmin.message_user(request, f"{updated} operator(s) rejected!")

reject_operator.short_description = "❌ Reject selected operators"


def suspend_operator(modeladmin, request, queryset):
    """Admin action to suspend bus operators"""
    updated = queryset.update(verification_status='suspended')
    modeladmin.message_user(request, f"{updated} operator(s) suspended!")

suspend_operator.short_description = "⏸️ Suspend selected operators"


@admin.register(BusOperator)
class BusOperatorAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_status_badge', 'contact_phone', 'contact_email', 'rating', 'total_buses', 'is_active']
    list_filter = ['verification_status', 'is_active', 'rating']
    search_fields = ['name', 'contact_phone', 'contact_email', 'gst_number', 'pan_number']
    list_editable = ['is_active']
    readonly_fields = ['verified_at', 'verified_by', 'created_at', 'updated_at']
    actions = [verify_operator, reject_operator, suspend_operator]
    
    fieldsets = (
        ('Business Information', {
            'fields': ('name', 'description', 'logo', 'contact_phone', 'contact_email')
        }),
        ('User Account', {
            'fields': ('user',)
        }),
        ('Legal Details', {
            'fields': ('business_license', 'pan_number', 'gst_number', 'registered_address')
        }),
        ('Verification', {
            'fields': ('verification_status', 'verified_at', 'verified_by'),
            'classes': ('collapse',)
        }),
        ('Ratings & Stats', {
            'fields': ('rating', 'total_trips_completed', 'total_bookings'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_badge(self, obj):
        """Display verification status as colored badge"""
        colors = {
            'pending': '#FFA500',      # Orange
            'verified': '#28a745',     # Green
            'rejected': '#dc3545',     # Red
            'suspended': '#6f42c1',    # Purple
        }
        color = colors.get(obj.verification_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_verification_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def total_buses(self, obj):
        """Display total buses for operator"""
        count = obj.buses.count()
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 3px 8px; border-radius: 3px;">{} buses</span>',
            count
        )
    total_buses.short_description = 'Buses'


@admin.register(Bus)
class BusAdmin(PrimaryImageValidationMixin, admin.ModelAdmin):
    list_display = ['bus_number', 'bus_name', 'operator', 'bus_type', 'bus_age_display', 'total_seats', 'average_rating', 'is_active']
    list_filter = ['bus_type', 'is_active', 'operator', 'manufacturing_year']
    search_fields = ['bus_number', 'bus_name', 'operator__name', 'registration_number']
    list_editable = ['is_active', 'bus_type']  # ← Allow inline editing of multiple buses
    list_select_related = ['operator']
    readonly_fields = ['created_at', 'updated_at', 'get_amenities_display']
    actions = ['enable_wifi', 'enable_ac', 'disable_ac', 'mark_as_active', 'mark_as_inactive']
    inlines = [BusImageInline]  # Phase 3: Multi-image support
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('operator', 'bus_number', 'bus_name', 'bus_type', 'total_seats')
        }),
        ('Vehicle Details', {
            'fields': ('manufacturing_year', 'registration_number', 'chassis_number'),
            'classes': ('collapse',)
        }),
        ('Amenities', {
            'fields': ('has_ac', 'has_wifi', 'has_charging_point', 'has_blanket', 'has_water_bottle', 
                       'has_tv', 'has_reading_light', 'has_emergency_exit', 'has_first_aid',
                       'has_gps_tracking', 'has_cctv', 'get_amenities_display'),
            'classes': ('collapse',)
        }),
        ('Ratings & Reviews', {
            'fields': ('average_rating', 'total_reviews'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def bus_age_display(self, obj):
        """Display bus age"""
        if obj.bus_age:
            return f"{obj.bus_age} years"
        return "N/A"
    bus_age_display.short_description = 'Bus Age'
    
    def get_amenities_display(self, obj):
        """Display all amenities as list"""
        amenities = obj.get_amenities_list()
        if amenities:
            return mark_safe('<br>'.join([f'✓ {a}' for a in amenities]))
        return 'No amenities'
    get_amenities_display.short_description = 'Amenities Summary'
    
    def enable_wifi(self, request, queryset):
        """Bulk action: Enable WiFi on selected buses"""
        updated = queryset.update(has_wifi=True)
        self.message_user(request, f"[OK] WiFi enabled on {updated} bus(es)")
    enable_wifi.short_description = "Enable WiFi on selected"
    
    def enable_ac(self, request, queryset):
        """Bulk action: Enable AC on selected buses"""
        updated = queryset.update(has_ac=True)
        self.message_user(request, f"[OK] AC enabled on {updated} bus(es)")
    enable_ac.short_description = "Enable AC on selected"
    
    def disable_ac(self, request, queryset):
        """Bulk action: Disable AC on selected buses"""
        updated = queryset.update(has_ac=False)
        self.message_user(request, f"[OK] AC disabled on {updated} bus(es)")
    disable_ac.short_description = "Disable AC on selected"
    
    def mark_as_active(self, request, queryset):
        """Bulk action: Mark buses as active"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"[OK] {updated} bus(es) marked as active")
    mark_as_active.short_description = "Mark selected as active"
    
    def mark_as_inactive(self, request, queryset):
        """Bulk action: Mark buses as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"[OK] {updated} bus(es) marked as inactive")
    mark_as_inactive.short_description = "Mark selected as inactive"


class BoardingPointInline(admin.TabularInline):
    model = BoardingPoint
    extra = 1
    fields = ['sequence_order', 'name', 'city', 'pickup_time', 'contact_phone']
    ordering = ['sequence_order']


class DroppingPointInline(admin.TabularInline):
    model = DroppingPoint
    extra = 1
    fields = ['sequence_order', 'name', 'city', 'drop_time', 'contact_phone']
    ordering = ['sequence_order']


class BusStopInline(admin.TabularInline):
    model = BusStop
    extra = 1
    fields = ['city', 'stop_name', 'stop_order', 'arrival_time', 'departure_time']


@admin.register(BusRoute)
class BusRouteAdmin(admin.ModelAdmin):
    list_display = ['route_name', 'source_city', 'destination_city', 'departure_time', 'arrival_time', 'duration_hours', 'base_fare', 'is_active']
    list_filter = ['is_active', 'source_city', 'destination_city', 'bus__operator']
    search_fields = ['route_name', 'source_city__name', 'destination_city__name', 'bus__bus_number']
    list_editable = ['is_active', 'base_fare']
    list_select_related = ['bus', 'bus__operator', 'source_city', 'destination_city']
    inlines = [BoardingPointInline, DroppingPointInline, BusStopInline]
    
    fieldsets = (
        ('Route Information', {
            'fields': ('bus', 'route_name', 'source_city', 'destination_city')
        }),
        ('Timing', {
            'fields': ('departure_time', 'arrival_time', 'duration_hours', 'distance_km')
        }),
        ('Pricing', {
            'fields': ('base_fare',)
        }),
        ('Operation Days', {
            'fields': ('operates_monday', 'operates_tuesday', 'operates_wednesday', 'operates_thursday', 
                       'operates_friday', 'operates_saturday', 'operates_sunday'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(BusSchedule)
class BusScheduleAdmin(admin.ModelAdmin):
    list_display = ['route', 'date', 'available_seats', 'booked_seats', 'occupancy_display', 'fare', 'is_active']
    list_filter = ['date', 'is_active', 'route__source_city', 'route__destination_city', 'is_cancelled']
    search_fields = ['route__route_name', 'route__source_city__name', 'route__destination_city__name']
    list_select_related = ['route', 'route__bus', 'route__source_city', 'route__destination_city']
    date_hierarchy = 'date'
    list_editable = ['available_seats', 'fare', 'is_active']
    readonly_fields = ['booked_seats', 'occupancy_display', 'is_almost_full']
    
    fieldsets = (
        ('Schedule', {
            'fields': ('route', 'date')
        }),
        ('Availability', {
            'fields': ('available_seats', 'booked_seats', 'occupancy_display')
        }),
        ('Pricing', {
            'fields': ('fare', 'window_seat_charge')
        }),
        ('Status', {
            'fields': ('is_active', 'is_cancelled', 'cancellation_reason', 'is_almost_full')
        }),
    )
    
    def occupancy_display(self, obj):
        """Display occupancy percentage with color"""
        pct = obj.occupancy_percentage
        if pct < 50:
            color = '#28a745'  # Green
        elif pct < 80:
            color = '#FFA500'  # Orange
        else:
            color = '#dc3545'  # Red
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{:.1f}%</span>',
            color,
            pct
        )
    occupancy_display.short_description = 'Occupancy'


@admin.register(BoardingPoint)
class BoardingPointAdmin(admin.ModelAdmin):
    list_display = ['name', 'route', 'city', 'pickup_time', 'sequence_order', 'is_active']
    list_filter = ['is_active', 'city', 'route__source_city', 'route__destination_city']
    search_fields = ['name', 'address', 'landmark', 'city__name']
    list_editable = ['is_active']
    list_select_related = ['route', 'city']
    ordering = ['route', 'sequence_order']
    
    fieldsets = (
        ('Location', {
            'fields': ('route', 'name', 'city', 'address', 'landmark', 'pincode', 'sequence_order')
        }),
        ('Coordinates', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Contact', {
            'fields': ('contact_person', 'contact_phone'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('pickup_time',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(DroppingPoint)
class DroppingPointAdmin(admin.ModelAdmin):
    list_display = ['name', 'route', 'city', 'drop_time', 'sequence_order', 'is_active']
    list_filter = ['is_active', 'city', 'route__source_city', 'route__destination_city']
    search_fields = ['name', 'address', 'landmark', 'city__name']
    list_editable = ['is_active']
    list_select_related = ['route', 'city']
    ordering = ['route', 'sequence_order']
    
    fieldsets = (
        ('Location', {
            'fields': ('route', 'name', 'city', 'address', 'landmark', 'pincode', 'sequence_order')
        }),
        ('Coordinates', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Contact', {
            'fields': ('contact_person', 'contact_phone'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('drop_time',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(SeatLayout)
class SeatLayoutAdmin(admin.ModelAdmin):
    list_display = ['bus', 'seat_number', 'seat_type', 'row', 'column', 'deck']
    list_filter = ['seat_type', 'deck', 'bus__operator']
    search_fields = ['bus__bus_number', 'seat_number']
    list_select_related = ['bus', 'bus__operator']
    ordering = ['bus', 'deck', 'row', 'column']
