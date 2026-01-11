"""
Review admin with moderation controls.
Phase 3: UI Data Quality & Trust

Admin capabilities:
- Approve/Unapprove reviews
- Hide reviews (soft delete)
- Filter by approval status, rating, entity
- Bulk actions for moderation
- View booking verification
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import HotelReview, BusReview, PackageReview


class ReviewAdminMixin:
    """Mixin for common review admin functionality."""
    
    list_display = ['id', 'user_email', 'entity_name', 'rating_stars', 'is_approved', 'is_verified', 'created_at_short']
    list_filter = ['is_approved', 'is_hidden', 'rating', 'created_at']
    search_fields = ['user__email', 'user__username', 'comment', 'booking_id']
    readonly_fields = ['created_at', 'updated_at', 'approved_at', 'approved_by', 'user', 'booking_id']
    date_hierarchy = 'created_at'
    
    actions = ['approve_reviews', 'unapprove_reviews', 'hide_reviews', 'unhide_reviews']
    
    fieldsets = (
        ('Review Details', {
            'fields': ('user', 'rating', 'title', 'comment')
        }),
        ('Verification', {
            'fields': ('booking_id',),
            'description': 'Booking reference for verified reviews'
        }),
        ('Moderation', {
            'fields': ('is_approved', 'approved_at', 'approved_by', 'is_hidden'),
            'description': 'Only approved reviews are visible on frontend'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        """Display user email with verified badge."""
        badges = []
        if obj.user.email_verified:
            badges.append('✓')
        if obj.user.phone_verified:
            badges.append('📱')
        
        badge_str = ' '.join(badges) if badges else ''
        return format_html(
            '{} <span style="color: #10b981;">{}</span>',
            obj.user.email,
            badge_str
        )
    user_email.short_description = 'User'
    
    def rating_stars(self, obj):
        """Display rating as stars."""
        stars = '⭐' * obj.rating
        color = '#10b981' if obj.rating >= 4 else '#f59e0b' if obj.rating >= 3 else '#ef4444'
        return format_html(
            '<span style="color: {}; font-size: 16px;">{}</span> {}',
            color,
            stars,
            obj.rating
        )
    rating_stars.short_description = 'Rating'
    
    def is_verified(self, obj):
        """Display verified booking badge."""
        if obj.is_verified_booking:
            return format_html(
                '<span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 4px;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: #9ca3af;">—</span>'
        )
    is_verified.short_description = 'Verified Booking'
    
    def created_at_short(self, obj):
        """Short date display."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_short.short_description = 'Created'
    
    def approve_reviews(self, request, queryset):
        """Approve selected reviews."""
        updated = 0
        for review in queryset:
            if not review.is_approved:
                review.is_approved = True
                review.approved_at = timezone.now()
                review.approved_by = request.user
                review.save(update_fields=['is_approved', 'approved_at', 'approved_by'])
                updated += 1
        
        self.message_user(request, f'✓ Approved {updated} review(s)')
    approve_reviews.short_description = '✓ Approve selected reviews'
    
    def unapprove_reviews(self, request, queryset):
        """Unapprove selected reviews."""
        updated = queryset.filter(is_approved=True).update(
            is_approved=False,
            approved_at=None,
            approved_by=None
        )
        self.message_user(request, f'✗ Unapproved {updated} review(s)')
    unapprove_reviews.short_description = '✗ Unapprove selected reviews'
    
    def hide_reviews(self, request, queryset):
        """Hide selected reviews (soft delete)."""
        updated = queryset.update(is_hidden=True)
        self.message_user(request, f'🙈 Hidden {updated} review(s)')
    hide_reviews.short_description = '🙈 Hide selected reviews'
    
    def unhide_reviews(self, request, queryset):
        """Unhide selected reviews."""
        updated = queryset.update(is_hidden=False)
        self.message_user(request, f'👁 Unhidden {updated} review(s)')
    unhide_reviews.short_description = '👁 Unhide selected reviews'


@admin.register(HotelReview)
class HotelReviewAdmin(ReviewAdminMixin, admin.ModelAdmin):
    """Hotel review admin."""
    
    def entity_name(self, obj):
        """Display hotel name."""
        try:
            return obj.hotel.name if obj.hotel else '—'
        except Exception:
            return '—'
    entity_name.short_description = 'Hotel'


@admin.register(BusReview)
class BusReviewAdmin(ReviewAdminMixin, admin.ModelAdmin):
    """Bus review admin."""
    
    def entity_name(self, obj):
        """Display bus name."""
        try:
            return obj.bus.bus_number if obj.bus else '—'
        except Exception:
            return '—'
    entity_name.short_description = 'Bus'


@admin.register(PackageReview)
class PackageReviewAdmin(ReviewAdminMixin, admin.ModelAdmin):
    """Package review admin."""
    
    def entity_name(self, obj):
        """Display package name."""
        try:
            return obj.package.name if obj.package else '—'
        except Exception:
            return '—'
    entity_name.short_description = 'Package'

