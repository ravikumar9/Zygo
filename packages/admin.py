from django.contrib import admin
from django.utils.html import format_html
from .models import Package, PackageImage, PackageItinerary, PackageInclusion, PackageDeparture
from core.admin_mixins import PrimaryImageValidationMixin
from core.admin_utils import SoftDeleteAdminMixin, soft_delete_selected, restore_selected


class PackageImageInline(admin.TabularInline):
    model = PackageImage
    extra = 1
    fields = ['image', 'caption', 'alt_text', 'display_order', 'is_primary']


class PackageItineraryInline(admin.TabularInline):
    model = PackageItinerary
    extra = 1
    fields = ['day_number', 'title', 'description', 'meals_included', 'accommodation']
    ordering = ['day_number']


class PackageInclusionInline(admin.TabularInline):
    model = PackageInclusion
    extra = 1
    fields = ['description', 'is_included']


class PackageDepartureInline(admin.TabularInline):
    model = PackageDeparture
    extra = 1
    fields = ['departure_date', 'return_date', 'available_slots', 'price_per_person', 'is_active']
    readonly_fields = ['departure_date']


@admin.register(Package)
class PackageAdmin(SoftDeleteAdminMixin, PrimaryImageValidationMixin, admin.ModelAdmin):
    list_display = ['name', 'package_type', 'duration_display', 'starting_price', 'deletion_status', 'is_active', 'status_indicator', 'image_preview']
    list_filter = ['is_deleted', 'package_type', 'is_featured', 'is_active', 'duration_days']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'image_preview', 'deleted_at', 'deleted_by']
    list_editable = ['is_active']
    filter_horizontal = ['destination_cities']
    inlines = [PackageImageInline, PackageItineraryInline, PackageInclusionInline, PackageDepartureInline]
    actions = [soft_delete_selected, restore_selected, 'make_active', 'make_inactive', 'feature_packages']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'itinerary_text', 'package_type', 'destination_cities')
        }),
        ('Duration', {
            'fields': ('duration_days', 'duration_nights')
        }),
        ('Pricing', {
            'fields': ('starting_price',)
        }),
        ('Inclusions', {
            'fields': ('includes_hotel', 'includes_transport', 'includes_meals', 'includes_sightseeing', 'includes_guide')
        }),
        ('Meal Plan', {
            'fields': ('breakfast_included', 'lunch_included', 'dinner_included')
        }),
        ('Group Size', {
            'fields': ('min_group_size', 'max_group_size')
        }),
        ('Rating & Reviews', {
            'fields': ('rating', 'review_count')
        }),
        ('Media & Status', {
            'fields': ('image', 'image_preview', 'is_featured', 'is_active', 'created_at', 'updated_at')
        }),
    )
    
    def duration_display(self, obj):
        return f"{obj.duration_days}D/{obj.duration_nights}N"
    duration_display.short_description = 'Duration'
    
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
                '<img src="{}" width="100" height="75" style="border-radius: 4px; object-fit: cover;" />',
                obj.image.url
            )
        return format_html('<em style="color: #999;">No image</em>')
    image_preview.short_description = 'Preview'
    
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"✓ Activated {updated} package(s)")
    make_active.short_description = "✓ Mark selected as active"
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"✗ Deactivated {updated} package(s)")
    make_inactive.short_description = "✗ Mark selected as inactive"
    
    def feature_packages(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"⭐ Featured {updated} package(s)")
    feature_packages.short_description = "⭐ Feature selected"


@admin.register(PackageDeparture)
class PackageDepartureAdmin(admin.ModelAdmin):
    list_display = ['package', 'departure_date', 'return_date', 'available_slots', 'price_per_person', 'is_active']
    list_filter = ['is_active', 'departure_date', 'package__package_type']
    search_fields = ['package__name']
    date_hierarchy = 'departure_date'
    list_editable = ['available_slots', 'price_per_person', 'is_active']
