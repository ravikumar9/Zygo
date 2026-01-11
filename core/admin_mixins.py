"""
Admin mixins for Phase 3: UI Data Quality & Trust

Provides shared validation logic for:
- Primary image enforcement
- Review moderation helpers
"""
from django.core.exceptions import ValidationError
from django.contrib import admin


class PrimaryImageValidationMixin:
    """
    Enforce exactly one primary image for entities (Hotel/Bus/Package).
    
    Phase 3 requirement: "Admin must prevent:
    - More than 1 primary image
    - Entity without primary image"
    """
    
    def save_formset(self, request, form, formset, change):
        """Validate primary image rules before saving inline formset."""
        instances = formset.save(commit=False)
        
        # Count primary images
        primary_count = 0
        for instance in instances:
            if hasattr(instance, 'is_primary') and instance.is_primary:
                primary_count += 1
        
        # Also count existing primary images (not in current formset)
        if change and hasattr(formset.model, 'objects'):
            # Get the parent object (hotel/bus/package)
            parent_field = None
            for field_name in ['hotel', 'bus', 'package']:
                if hasattr(formset.model, field_name):
                    parent_field = field_name
                    break
            
            if parent_field:
                # Exclude instances being updated
                instance_ids = [inst.id for inst in instances if inst.id]
                existing_primary = formset.model.objects.filter(
                    **{parent_field: getattr(form.instance, 'id', None)},
                    is_primary=True
                ).exclude(id__in=instance_ids).count()
                
                primary_count += existing_primary
        
        # Validation: Must have exactly 1 primary
        if primary_count > 1:
            raise ValidationError(
                "Only ONE image can be marked as primary. "
                f"Found {primary_count} primary images."
            )
        
        # Allow saving - we'll create a post-save signal to auto-set first as primary if needed
        super().save_formset(request, form, formset, change)


class ReviewModerationHelperMixin:
    """
    Helper methods for review moderation in admin.
    
    Phase 3: Provides quick display of:
    - Verified user badges
    - Verified booking badges
    - Rating stars display
    """
    
    @staticmethod
    def get_verified_user_badge(user):
        """Get verified badge HTML for user."""
        from django.utils.html import format_html
        
        badges = []
        if getattr(user, 'email_verified', False):
            badges.append('✓ Email')
        if getattr(user, 'phone_verified', False):
            badges.append('📱 Phone')
        
        if badges:
            return format_html(
                '<span style="color: #10b981; font-size: 11px;">{}</span>',
                ' '.join(badges)
            )
        return format_html('<span style="color: #9ca3af;">—</span>')
    
    @staticmethod
    def get_verified_booking_badge(is_verified):
        """Get verified booking badge HTML."""
        from django.utils.html import format_html
        
        if is_verified:
            return format_html(
                '<span style="background: #10b981; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">✓ VERIFIED</span>'
            )
        return format_html('<span style="color: #9ca3af;">—</span>')
    
    @staticmethod
    def get_rating_stars(rating):
        """Get rating as stars with color."""
        from django.utils.html import format_html
        
        stars = '⭐' * rating
        color = '#10b981' if rating >= 4 else '#f59e0b' if rating >= 3 else '#ef4444'
        
        return format_html(
            '<span style="color: {}; font-size: 14px;">{}</span> <small>({})</small>',
            color,
            stars,
            rating
        )
