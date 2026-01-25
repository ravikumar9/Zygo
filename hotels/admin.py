from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Hotel, HotelImage, RoomType, RoomMealPlan, RoomAvailability, RoomBlock,
    ChannelManagerRoomMapping, MealPlan, PolicyCategory, PropertyPolicy
)
from core.admin_mixins import PrimaryImageValidationMixin
from core.admin_utils import SoftDeleteAdminMixin, soft_delete_selected, restore_selected


class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 1
    fields = ['image', 'caption', 'alt_text', 'display_order', 'is_primary']
    ordering = ['display_order', 'id']


class PropertyPolicyInline(admin.TabularInline):
    model = PropertyPolicy
    extra = 1
    fields = ['category', 'label', 'description', 'is_highlighted', 'display_order']
    ordering = ['category__display_order', 'display_order', 'id']


class RoomMealPlanInline(admin.TabularInline):
    model = RoomMealPlan
    extra = 0
    fields = ['meal_plan', 'price_delta', 'is_default', 'is_active', 'display_order']
    ordering = ['display_order', 'id']


class RoomTypeInline(admin.TabularInline):
    model = RoomType
    extra = 1
    fields = ['name', 'room_type', 'max_occupancy', 'base_price', 'total_rooms', 'is_available']


@admin.register(Hotel)
class HotelAdmin(SoftDeleteAdminMixin, PrimaryImageValidationMixin, admin.ModelAdmin):
    list_display = ['name', 'city', 'property_type_tag', 'star_rating', 'review_rating', 'rooms_count', 'approval_status', 'is_active']
    list_filter = ['is_deleted', 'is_active', 'property_type', 'star_rating', 'city', 'has_wifi', 'has_pool', 'has_gym', 'inventory_source']
    search_fields = ['name', 'city__name', 'address']
    list_editable = ['is_active', 'star_rating']
    list_select_related = ['city']
    readonly_fields = ['created_at', 'updated_at', 'image_preview', 'deleted_at', 'deleted_by', 'approval_summary']
    inlines = [HotelImageInline, PropertyPolicyInline]
    actions = [soft_delete_selected, restore_selected]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'city', 'address', 'latitude', 'longitude', 'contact_phone', 'contact_email')
        }),
        ('Hotel Classification', {
            'fields': ('property_type', 'star_rating', 'review_rating', 'review_count'),
            'description': 'Hotel type, star, and guest ratings'
        }),
        ('Images & Media', {
            'fields': ('image', 'image_preview'),
            'description': 'Primary image. Additional images managed inline.'
        }),
        ('Inventory Management (CRITICAL)', {
            'fields': ('inventory_source', 'channel_manager_name'),
            'description': 'INTERNAL: GoExplorer managed. EXTERNAL: External CM'
        }),
        ('Hotel Amenities', {
            'fields': ('has_wifi', 'has_parking', 'has_pool', 'has_gym', 'has_restaurant', 'has_spa', 'has_ac')
        }),
        ('Check-in & Check-out', {
            'fields': ('checkin_time', 'checkout_time')
        }),
        ('Cancellation Policy (Hotel-Level)', {
            'fields': ('cancellation_type', 'cancellation_days', 'refund_percentage', 'refund_mode', 'cancellation_policy'),
            'classes': ('wide',),
            'description': 'Default cancellation terms'
        }),
        ('House Rules', {
            'fields': ('property_rules', 'amenities_rules'),
            'classes': ('wide',),
            'description': 'Text content appearing in guest page'
        }),
        ('Visibility & Status', {
            'fields': ('is_featured', 'is_active', 'approval_summary'),
            'description': 'Feature = homepage. Active = visible.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_active', 'make_inactive', 'feature_hotels', 'unfeature_hotels']
    
    def rooms_count(self, obj):
        approved = obj.room_types.filter(status='APPROVED').count()
        total = obj.room_types.count()
        return format_html(
            '<span style="background-color: #2196f3; color: white; padding: 2px 8px; border-radius: 3px;">{}/{} ✓</span>',
            approved, total
        )
    rooms_count.short_description = 'Rooms'
    
    def approval_status(self, obj):
        approved = obj.room_types.filter(status='APPROVED').count()
        total = obj.room_types.count()
        if total == 0:
            return format_html('<span style="color: #999;">No rooms</span>')
        if approved == total:
            return format_html('<span style="color: #4caf50; font-weight: 600;">✓ All</span>')
        return format_html('<span style="color: #ff9800; font-weight: 600;">⧗ {}/{}</span>', approved, total)
    approval_status.short_description = 'Approval'
    
    def approval_summary(self, obj):
        approved = obj.room_types.filter(status='APPROVED').count()
        ready = obj.room_types.filter(status='READY').count()
        draft = obj.room_types.filter(status='DRAFT').count()
        return format_html(
            '<div style="background-color: #f5f5f5; padding: 1rem; border-radius: 4px; border-left: 4px solid #2196f3;"><p style="margin: 0; color: #333; font-weight: 600;">Room Approval Summary</p><p style="margin: 0.5rem 0 0 0; color: #555; font-size: 0.9rem;">✓ Approved: {}<br/>→ Ready: {}<br/>✎ Draft: {}</p></div>',
            approved, ready, draft
        )
    approval_summary.short_description = 'Approval Status'
    
    def property_type_tag(self, obj):
        color_map = {
            'hotel': '#0066cc',
            'resort': '#009900',
            'villa': '#cc6600',
            'homestay': '#990099',
            'lodge': '#cc0000'
        }
        property_type = obj.property_type
        color = color_map.get(property_type, '#999999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; text-transform: capitalize;">{}</span>',
            color, property_type
        )
    property_type_tag.short_description = 'Type'
    
    def status_indicator(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: #009900; font-weight: bold;">● ACTIVE</span>'
            )
        return format_html(
            '<span style="color: #cc0000; font-weight: bold;">● INACTIVE</span>'
        )
    status_indicator.short_description = 'Status'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="150" height="100" style="border-radius: 4px; object-fit: cover;" />',
                obj.image.url
            )
        return format_html('<em style="color: #999;">No image uploaded</em>')
    image_preview.short_description = 'Preview'
    
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"✓ Activated {updated} hotel(s)")
    make_active.short_description = "✓ Mark selected as active"
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"✗ Deactivated {updated} hotel(s)")
    make_inactive.short_description = "✗ Mark selected as inactive"
    
    def feature_hotels(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"⭐ Featured {updated} hotel(s)")
    feature_hotels.short_description = "⭐ Feature selected"
    
    def unfeature_hotels(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"⭐ Unfeatured {updated} hotel(s)")
    unfeature_hotels.short_description = "☆ Unfeature selected"
    
    def enable_amenities(self, request, queryset):
        """Bulk action: Enable WiFi + Pool + Gym for selected hotels"""
        updated = queryset.update(has_wifi=True, has_pool=True, has_gym=True)
        self.message_user(request, f"[OK] WiFi + Pool + Gym enabled on {updated} hotel(s)")
    enable_amenities.short_description = "Enable WiFi/Pool/Gym on selected"


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'hotel', 'room_type', 'max_occupancy', 'base_price', 'total_rooms', 'is_available', 'meal_plan_count', 'status_tag', 'approval_check']
    list_filter = ['room_type', 'is_available', 'hotel__city', 'status']
    search_fields = ['name', 'hotel__name']
    list_select_related = ['hotel', 'hotel__city']
    list_editable = ['is_available']
    inlines = [RoomMealPlanInline]
    readonly_fields = ['created_at', 'updated_at', 'status_indicator']
    
    fieldsets = (
        ('Room Information', {
            'fields': ('hotel', 'name', 'description', 'room_type')
        }),
        ('Capacity (MANDATORY)', {
            'fields': ('max_adults', 'max_children', 'max_occupancy'),
            'description': 'Define how many adults/children'
        }),
        ('Room Details (MANDATORY)', {
            'fields': ('bed_type', 'number_of_beds', 'room_size'),
            'description': 'Bed config and size in sqft'
        }),
        ('Amenities', {
            'fields': ('has_balcony', 'has_tv', 'has_minibar', 'has_safe')
        }),
        ('Pricing & Discounts', {
            'fields': ('base_price', 'discount_type', 'discount_value', 'discount_valid_from', 'discount_valid_to', 'discount_is_active', 'is_refundable')
        }),
        ('Inventory', {
            'fields': ('total_rooms', 'is_available')
        }),
        ('Images (MIN 3)', {
            'fields': ('image',)
        }),
        ('Approval', {
            'fields': ('status', 'status_indicator'),
            'description': 'DRAFT → READY → APPROVED'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_ready_for_approval', 'approve_rooms', 'reject_rooms']
    
    def meal_plan_count(self, obj):
        count = obj.meal_plans.filter(is_active=True).count()
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 2px 8px; border-radius: 3px;">{} plans</span>',
            count
        )
    meal_plan_count.short_description = 'Meal Plans'
    
    def status_tag(self, obj):
        colors = {'DRAFT': '#ff9800', 'READY': '#2196f3', 'APPROVED': '#4caf50'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 3px; font-weight: 600;\">{}</span>',
            colors.get(obj.status, '#999'), obj.get_status_display()
        )
    status_tag.short_description = 'Status'
    
    def approval_check(self, obj):
        if obj.is_complete:
            return format_html('<span style="color: #4caf50; font-weight: 600;">✓ Ready</span>')
        incomplete = []
        if not obj.bed_type: incomplete.append('bed')
        if not obj.room_size or obj.room_size <= 0: incomplete.append('size')
        if obj.images.count() < 3: incomplete.append(f'img({obj.images.count()}/3)')
        if not obj.meal_plans.filter(is_active=True).exists(): incomplete.append('meals')
        return format_html('<span style="color: #f44336; font-weight: 600;">✗ {}</span>', ', '.join(incomplete))
    approval_check.short_description = 'Ready?'
    
    def status_indicator(self, obj):
        if obj.is_complete:
            return format_html(
                '<div style="background-color: #e8f5e9; padding: 1rem; border-radius: 4px; border-left: 4px solid #4caf50;"><p style="margin: 0; color: #2e7d32;"><strong>✓ COMPLETE & READY FOR APPROVAL</strong></p></div>'
            )
        return format_html(
            '<div style="background-color: #fff3e0; padding: 1rem; border-radius: 4px; border-left: 4px solid #ff9800;"><p style="margin: 0; color: #e65100;"><strong>✗ INCOMPLETE - FIX: bed_type, room_size, 3+ images, meal plans</strong></p></div>'
        )
    status_indicator.short_description = 'Status'
    
    def mark_ready_for_approval(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.is_complete:
                obj.set_ready()
                count += 1
        self.message_user(request, f'✓ Marked {count} room(s) as READY')
    mark_ready_for_approval.short_description = '→ Mark READY for approval'
    
    def approve_rooms(self, request, queryset):
        count = queryset.filter(status='READY').update(status='APPROVED')
        self.message_user(request, f'✓ Approved {count} room(s)')
    approve_rooms.short_description = '✓ Approve selected'
    
    def reject_rooms(self, request, queryset):
        count = queryset.update(status='DRAFT')
        self.message_user(request, f'✗ Returned {count} room(s) to DRAFT')
    reject_rooms.short_description = '✗ Return to DRAFT'


@admin.register(RoomMealPlan)
class RoomMealPlanAdmin(admin.ModelAdmin):
    list_display = ['room_type_display', 'meal_plan', 'price_delta', 'total_price', 'is_default', 'is_active', 'display_order']
    list_filter = ['is_active', 'is_default', 'meal_plan', 'room_type__hotel__city']
    search_fields = ['room_type__name', 'meal_plan__name', 'room_type__hotel__name']
    list_select_related = ['room_type', 'room_type__hotel', 'meal_plan']
    list_editable = ['is_active', 'display_order']
    ordering = ['room_type', 'display_order', 'id']
    
    fieldsets = (
        ('Meal Plan Link', {
            'fields': ('room_type', 'meal_plan')
        }),
        ('Pricing', {
            'fields': ('price_delta',),
            'description': 'Additional cost per night above base_price (can be 0 for Room Only)'
        }),
        ('Display Settings', {
            'fields': ('is_default', 'is_active', 'display_order'),
        }),
    )
    
    def room_type_display(self, obj):
        return f"{obj.room_type.hotel.name} - {obj.room_type.name}"
    room_type_display.short_description = "Room"
    
    def total_price(self, obj):
        """Display total price per night (base + delta)"""
        return f"₹{obj.get_total_price_per_night()}"
    total_price.short_description = "Total/Night"
    room_type_display.short_description = 'Room Type / Hotel'


@admin.register(RoomBlock)
class RoomBlockAdmin(admin.ModelAdmin):
    """Admin for room blocking (Sprint-1)"""
    list_display = ['room_type', 'blocked_from', 'blocked_to', 'reason', 'is_active', 'created_by']
    list_filter = ['is_active', 'blocked_from', 'room_type__hotel']
    search_fields = ['room_type__name', 'room_type__hotel__name', 'reason']
    date_hierarchy = 'blocked_from'
    list_select_related = ['room_type', 'room_type__hotel', 'created_by']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        ('Room & Dates', {
            'fields': ('room_type', 'blocked_from', 'blocked_to', 'is_active')
        }),
        ('Details', {
            'fields': ('reason', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on new objects
            obj.created_by = request.user
        obj.full_clean()  # Validate before save
        super().save_model(request, obj, form, change)


# Keep old RoomAvailability admin for inventory management
@admin.register(RoomAvailability)
class RoomAvailabilityAdmin(admin.ModelAdmin):
    """Admin for room availability inventory (date-based pricing/availability)"""
    list_display = ['room_type', 'date', 'available_rooms', 'price']
    list_filter = ['date', 'room_type__hotel']
    search_fields = ['room_type__name', 'room_type__hotel__name']
    date_hierarchy = 'date'


@admin.register(ChannelManagerRoomMapping)

class ChannelManagerRoomMappingAdmin(admin.ModelAdmin):
    list_display = ['hotel', 'room_type', 'provider', 'external_room_id', 'is_active']
    list_filter = ['provider', 'is_active', 'hotel__city']
    search_fields = ['hotel__name', 'room_type__name', 'external_room_id']
    list_select_related = ['hotel', 'room_type']


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    """Admin for global meal plan definitions"""
    list_display = ['name', 'plan_type', 'is_refundable', 'is_active', 'display_order']
    list_filter = ['is_active', 'is_refundable', 'plan_type']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'display_order']
    ordering = ['display_order', 'id']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'plan_type', 'description')
        }),
        ('Inclusions', {
            'fields': ('inclusions',),
            'description': 'JSON list of what\'s included (e.g., ["Breakfast", "Wi-Fi"])'
        }),
        ('Settings', {
            'fields': ('is_refundable', 'is_active', 'display_order')
        }),
    )


@admin.register(PolicyCategory)
class PolicyCategoryAdmin(admin.ModelAdmin):
    """Admin for policy categories"""
    list_display = ['name', 'category_type', 'icon_class', 'is_active', 'display_order']
    list_filter = ['is_active', 'category_type']
    search_fields = ['name']
    list_editable = ['is_active', 'display_order']
    ordering = ['display_order', 'id']


@admin.register(PropertyPolicy)
class PropertyPolicyAdmin(admin.ModelAdmin):
    """Admin for hotel property policies"""
    list_display = ['hotel', 'category', 'label', 'is_highlighted', 'display_order']
    list_filter = ['category', 'is_highlighted', 'hotel__city']
    search_fields = ['hotel__name', 'label', 'description']
    list_select_related = ['hotel', 'category']
    list_editable = ['display_order']
    ordering = ['hotel', 'category__display_order', 'display_order', 'id']
    
    fieldsets = (
        ('Policy', {
            'fields': ('hotel', 'category', 'label', 'description')
        }),
        ('Display', {
            'fields': ('is_highlighted', 'display_order')
        }),
    )
