"""
Admin utilities for crash-proof display methods.
"""
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import admin
import logging

logger = logging.getLogger(__name__)


def safe_admin_display(default='N/A', log_error=True):
    """
    Decorator to make admin display methods crash-proof.
    
    Usage:
        @safe_admin_display(default='N/A')
        def my_display_method(self, obj):
            return obj.some_field
    
    If an exception occurs, returns the default value and optionally logs the error.
    """
    def decorator(func):
        def wrapper(self, obj):
            try:
                result = func(self, obj)
                return result if result is not None else default
            except Exception as e:
                if log_error:
                    logger.error(
                        f"Admin display error in {func.__name__} for {obj.__class__.__name__} "
                        f"(id={getattr(obj, 'id', 'unknown')}): {e}",
                        exc_info=False  # Don't need full traceback for display errors
                    )
                return format_html('<span style="color: #dc3545;">Error</span>')
        
        # Preserve function metadata
        wrapper.short_description = getattr(func, 'short_description', func.__name__)
        wrapper.admin_order_field = getattr(func, 'admin_order_field', None)
        wrapper.allow_tags = getattr(func, 'allow_tags', False)
        
        return wrapper
    return decorator


def safe_format_number(value, decimal_places=2, prefix='', suffix='', default='N/A'):
    """
    Safely format a numeric value for admin display.
    
    Args:
        value: The value to format (can be None, string, or number)
        decimal_places: Number of decimal places (default: 2)
        prefix: String to prepend (e.g., '$', '₹')
        suffix: String to append (e.g., '%', 'kg')
        default: Value to return if formatting fails
    
    Returns:
        Formatted string or default value
    """
    try:
        if value is None:
            return default
        
        num_value = float(value)
        formatted = f"{num_value:.{decimal_places}f}"
        return f"{prefix}{formatted}{suffix}"
    except (ValueError, TypeError):
        return default


def safe_format_percentage(value, decimal_places=1, default='N/A'):
    """
    Safely format a percentage value for admin display.
    
    Args:
        value: The percentage value (0-100)
        decimal_places: Number of decimal places (default: 1)
        default: Value to return if formatting fails
    
    Returns:
        Formatted percentage string or default value
    """
    return safe_format_number(value, decimal_places, suffix='%', default=default)


def safe_format_currency(value, currency_symbol='₹', decimal_places=2, default='N/A'):
    """
    Safely format a currency value for admin display.
    
    Args:
        value: The amount to format
        currency_symbol: Currency symbol (default: '₹')
        decimal_places: Number of decimal places (default: 2)
        default: Value to return if formatting fails
    
    Returns:
        Formatted currency string or default value
    """
    return safe_format_number(value, decimal_places, prefix=currency_symbol, default=default)


def safe_get_attr(obj, attr_path, default=None):
    """
    Safely get a nested attribute from an object.
    
    Args:
        obj: The object to get the attribute from
        attr_path: Dot-separated path to the attribute (e.g., 'user.email')
        default: Value to return if attribute doesn't exist or is None
    
    Returns:
        The attribute value or default
    """
    try:
        attrs = attr_path.split('.')
        value = obj
        for attr in attrs:
            value = getattr(value, attr, None)
            if value is None:
                return default
        return value
    except (AttributeError, TypeError):
        return default


# Soft Delete Admin Actions

def soft_delete_selected(modeladmin, request, queryset):
    """
    Admin action to soft delete selected records.
    
    Usage in ModelAdmin:
        actions = [soft_delete_selected]
    """
    count = 0
    for obj in queryset:
        if hasattr(obj, 'soft_delete'):
            obj.soft_delete(user=request.user)
            count += 1
    
    modeladmin.message_user(
        request,
        f"🗑️ {count} record(s) soft deleted. Use 'Show Deleted' filter to restore them.",
        level='success' if count > 0 else 'warning'
    )
soft_delete_selected.short_description = "🗑️ Soft delete selected items"


def restore_selected(modeladmin, request, queryset):
    """
    Admin action to restore soft-deleted records.
    
    Usage in ModelAdmin:
        actions = [restore_selected]
    """
    count = 0
    for obj in queryset.filter(is_deleted=True):
        if hasattr(obj, 'restore'):
            obj.restore()
            count += 1
    
    modeladmin.message_user(
        request,
        f"✅ {count} record(s) restored successfully.",
        level='success' if count > 0 else 'warning'
    )
restore_selected.short_description = "✅ Restore selected items"


class SoftDeleteAdminMixin:
    """
    Mixin for ModelAdmin to support soft delete functionality.
    
    Usage:
        class MyModelAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
            list_display = ['name', 'deletion_status', ...]
            list_filter = ['is_deleted', ...]
            actions = [soft_delete_selected, restore_selected]
    """
    
    def get_queryset(self, request):
        """
        Override to show all records (including deleted) in admin.
        Use list_filter to let admin choose which to see.
        """
        qs = super().get_queryset(request)
        # Show all records in admin (use filter to hide deleted if needed)
        return qs.model.all_objects.all() if hasattr(qs.model, 'all_objects') else qs
    
    @safe_admin_display()
    def deletion_status(self, obj):
        """Display deletion status with restore option"""
        if obj.is_deleted:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">🗑️ Deleted</span><br>'
                '<small style="color: #666;">{}</small>',
                obj.deletion_info if hasattr(obj, 'deletion_info') else ''
            )
        else:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">✅ Active</span>'
            )
    deletion_status.short_description = 'Status'

