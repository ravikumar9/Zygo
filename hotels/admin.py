from django.contrib import admin
from django.utils.html import format_html
from .models import Hotel, HotelImage, RoomType, RoomAvailability, ChannelManagerRoomMapping


class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 1
    fields = ['image', 'alt_text', 'display_order']


class RoomTypeInline(admin.TabularInline):
    model = RoomType
    extra = 1
    fields = ['name', 'room_type', 'max_occupancy', 'base_price', 'total_rooms', 'is_available']


class RoomAvailabilityInline(admin.TabularInline):
    model = RoomAvailability
    extra = 0
    fields = ['date', 'available_rooms']
    can_delete = False
    readonly_fields = ['date']


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'property_type_tag', 'star_rating', 'review_rating', 'status_indicator', 'is_active']
    list_filter = ['is_active', 'property_type', 'star_rating', 'city', 'has_wifi', 'has_pool', 'has_gym']
    search_fields = ['name', 'city__name', 'address']
    list_editable = ['is_active']
    list_select_related = ['city']
    readonly_fields = ['created_at', 'updated_at', 'image_preview']
    inlines = [HotelImageInline, RoomTypeInline, RoomAvailabilityInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'city', 'address', 'latitude', 'longitude')
        }),
        ('Hotel Classification', {
            'fields': ('property_type', 'star_rating'),
            'description': 'Hotel type and star classification'
        }),
        ('Images', {
            'fields': ('image', 'image_preview'),
            'description': 'Primary image (will be used as thumbnail)'
        }),
        ('Ratings & Reviews', {
            'fields': ('star_rating', 'review_rating', 'review_count')
        }),
        ('Inventory & Channel Manager', {
            'fields': ('inventory_source', 'channel_manager_name')
        }),
        ('Amenities', {
            'fields': ('has_wifi', 'has_parking', 'has_pool', 'has_gym', 'has_restaurant', 'has_spa', 'has_ac')
        }),
        ('Property Rules & Policies', {
            'fields': ('property_rules',),
            'classes': ('wide',),
            'description': 'Enter check-in/out times, cancellation rules, payment terms'
        }),
        ('Check-in/Check-out', {
            'fields': ('checkin_time', 'checkout_time')
        }),
        ('Contact', {
            'fields': ('contact_phone', 'contact_email')
        }),
        ('Status', {
            'fields': ('is_featured', 'is_active', 'created_at', 'updated_at')
        }),
    )
    
    actions = ['make_active', 'make_inactive', 'feature_hotels', 'unfeature_hotels']
    
    def property_type_tag(self, obj):
        color_map = {
            'Hotel': '#0066cc',
            'Resort': '#009900',
            'Villa': '#cc6600',
            'Homestay': '#990099',
            'Lodge': '#cc0000'
        }
        property_type = getattr(obj, 'property_type', 'Hotel')
        color = color_map.get(property_type, '#999999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            property_type
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
        self.message_user(request, f"☆ Unfeatured {updated} hotel(s)")
    unfeature_hotels.short_description = "☆ Unfeature selected"


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'hotel', 'room_type', 'max_occupancy', 'base_price', 'total_rooms', 'is_available']
    list_filter = ['room_type', 'is_available', 'hotel__city']
    search_fields = ['name', 'hotel__name']
    list_select_related = ['hotel', 'hotel__city']
    list_editable = ['is_available']


@admin.register(RoomAvailability)
class RoomAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['room_type', 'date', 'available_rooms', 'price']
    list_select_related = ['room_type', 'room_type__hotel']
    list_filter = ['date', 'room_type__hotel']
    search_fields = ['room_type__name', 'room_type__hotel__name']
    date_hierarchy = 'date'


@admin.register(ChannelManagerRoomMapping)
class ChannelManagerRoomMappingAdmin(admin.ModelAdmin):
    list_display = ['hotel', 'room_type', 'provider', 'external_room_id', 'is_active']
    list_filter = ['provider', 'is_active', 'hotel__city']
    search_fields = ['hotel__name', 'room_type__name', 'external_room_id']
    list_select_related = ['hotel', 'room_type']
