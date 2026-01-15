from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import City, PromoCode, PromoCodeUsage, CorporateDiscount, CorporateAccount
from .admin_utils import safe_admin_display, safe_format_currency


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'state', 'country', 'code', 'is_popular']
    list_filter = ['is_popular', 'state', 'country']
    search_fields = ['name', 'state', 'code']
    list_editable = ['is_popular']


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = [
        'code', 
        'discount_display', 
        'applicable_to', 
        'validity_status', 
        'usage_display',
        'is_active'  # Must be in list_display for list_editable
    ]
    list_filter = [
        'is_active', 
        'discount_type', 
        'applicable_to',
        'valid_from',
        'valid_until'
    ]
    search_fields = ['code', 'description']
    list_editable = ['is_active']  # ONE-CLICK TOGGLE
    readonly_fields = ['total_uses', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Promo Code Details', {
            'fields': ('code', 'description')
        }),
        ('Discount Configuration', {
            'fields': (
                'discount_type', 
                'discount_value', 
                'max_discount_amount',
                'min_booking_amount'
            )
        }),
        ('Applicability', {
            'fields': ('applicable_to',)
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Usage Limits', {
            'fields': (
                'max_total_uses',
                'max_uses_per_user',
                'total_uses'
            )
        }),
        ('Control', {
            'fields': ('is_active',),
            'description': 'Toggle this to instantly enable/disable the promo code'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_codes', 'deactivate_codes', 'reset_usage']
    
    @safe_admin_display()
    def discount_display(self, obj):
        """Display formatted discount"""
        if obj.discount_type == 'flat':
            discount_text = f"₹{obj.discount_value}"
        else:
            discount_text = f"{obj.discount_value}%"
            if obj.max_discount_amount:
                discount_text += f" (max ₹{obj.max_discount_amount})"
        
        return format_html(
            '<span style="background: #0d6efd; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            discount_text
        )
    discount_display.short_description = 'Discount'
    
    @safe_admin_display()
    def validity_status(self, obj):
        """Display validity status with color coding"""
        is_valid, message = obj.is_valid()
        now = timezone.now()
        
        if not obj.is_active:
            color = '#6c757d'
            icon = '⏸️'
            status = 'Inactive'
        elif now < obj.valid_from:
            color = '#ffc107'
            icon = '⏳'
            status = 'Upcoming'
        elif now > obj.valid_until:
            color = '#dc3545'
            icon = '⏱️'
            status = 'Expired'
        elif obj.max_total_uses and obj.total_uses >= obj.max_total_uses:
            color = '#dc3545'
            icon = '🚫'
            status = 'Limit Reached'
        else:
            color = '#28a745'
            icon = '✅'
            status = 'Active'
        
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{} {}</span>',
            color, icon, status
        )
    validity_status.short_description = 'Status'
    
    @safe_admin_display()
    def usage_display(self, obj):
        """Display usage statistics"""
        if obj.max_total_uses:
            percentage = (obj.total_uses / obj.max_total_uses) * 100
            color = '#28a745' if percentage < 70 else '#ffc107' if percentage < 90 else '#dc3545'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} / {}</span>',
                color, obj.total_uses, obj.max_total_uses
            )
        else:
            return format_html(
                '<span style="color: #0d6efd; font-weight: bold;">{} uses</span>',
                obj.total_uses
            )
    usage_display.short_description = 'Usage'
    
    @safe_admin_display()
    def is_active_toggle(self, obj):
        """Visual indicator for active status"""
        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-size: 18px;">●</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-size: 18px;">●</span>'
            )
    is_active_toggle.short_description = 'Active'
    
    def activate_codes(self, request, queryset):
        """Bulk action: Activate promo codes"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"✅ {updated} promo code(s) activated")
    activate_codes.short_description = "✅ Activate selected promo codes"
    
    def deactivate_codes(self, request, queryset):
        """Bulk action: Deactivate promo codes"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"⏸️ {updated} promo code(s) deactivated")
    deactivate_codes.short_description = "⏸️ Deactivate selected promo codes"
    
    def reset_usage(self, request, queryset):
        """Bulk action: Reset usage counter"""
        updated = queryset.update(total_uses=0)
        self.message_user(request, f"🔄 Usage reset for {updated} promo code(s)")
    reset_usage.short_description = "🔄 Reset usage counter"


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = ['promo_code', 'user_email', 'discount_amount_display', 'booking_link', 'created_at']
    list_filter = ['promo_code', 'created_at']
    search_fields = ['user__email', 'promo_code__code', 'booking__booking_id']
    readonly_fields = ['promo_code', 'user', 'booking', 'discount_amount', 'created_at']
    
    def has_add_permission(self, request):
        """Prevent manual creation - auto-created on booking"""
        return False
    
    @safe_admin_display()
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    
    @safe_admin_display()
    def discount_amount_display(self, obj):
        return safe_format_currency(obj.discount_amount)
    discount_amount_display.short_description = 'Discount'
    
    @safe_admin_display()
    def booking_link(self, obj):
        if obj.booking:
            return format_html(
                '<a href="/admin/bookings/booking/{}/change/">{}</a>',
                obj.booking.id,
                str(obj.booking.booking_id)[:8].upper()
            )
        return '-'
    booking_link.short_description = 'Booking'


@admin.register(CorporateDiscount)
class CorporateDiscountAdmin(admin.ModelAdmin):
    list_display = [
        'company_name',
        'email_domain',
        'discount_display',
        'applicable_to',
        'is_active'  # Must be in list_display for list_editable
    ]
    list_filter = ['is_active', 'discount_type', 'applicable_to']
    search_fields = ['company_name', 'email_domain']
    list_editable = ['is_active']  # ONE-CLICK TOGGLE
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Company Details', {
            'fields': ('company_name', 'email_domain')
        }),
        ('Discount Configuration', {
            'fields': (
                'discount_type',
                'discount_value',
                'max_discount_amount'
            )
        }),
        ('Applicability', {
            'fields': ('applicable_to',)
        }),
        ('Control', {
            'fields': ('is_active',),
            'description': 'Toggle this to instantly enable/disable corporate discount'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_discounts', 'deactivate_discounts']
    
    @safe_admin_display()
    def discount_display(self, obj):
        """Display formatted discount"""
        if obj.discount_type == 'flat':
            discount_text = f"₹{obj.discount_value}"
        else:
            discount_text = f"{obj.discount_value}%"
            if obj.max_discount_amount:
                discount_text += f" (max ₹{obj.max_discount_amount})"
        
        return format_html(
            '<span style="background: #198754; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            discount_text
        )
    discount_display.short_description = 'Discount'
    
    @safe_admin_display()
    def is_active_toggle(self, obj):
        """Visual indicator for active status"""
        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-size: 18px;">●</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-size: 18px;">●</span>'
            )
    is_active_toggle.short_description = 'Active'
    
    def activate_discounts(self, request, queryset):
        """Bulk action: Activate corporate discounts"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"✅ {updated} corporate discount(s) activated")
    activate_discounts.short_description = "✅ Activate selected discounts"
    
    def deactivate_discounts(self, request, queryset):
        """Bulk action: Deactivate corporate discounts"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"⏸️ {updated} corporate discount(s) deactivated")
    deactivate_discounts.short_description = "⏸️ Deactivate selected discounts"


@admin.register(CorporateAccount)
class CorporateAccountAdmin(admin.ModelAdmin):
    list_display = [
        'company_name',
        'email_domain',
        'status_badge',
        'contact_person_name',
        'contact_email',
        'gst_number',
        'coupon_display',
        'created_at',
    ]
    list_filter = ['status', 'is_active', 'account_type', 'created_at']
    search_fields = ['company_name', 'email_domain', 'contact_person_name', 'contact_email']
    readonly_fields = ['approved_at', 'rejected_at', 'approved_by', 'created_at', 'updated_at', 'linked_users_count']
    
    fieldsets = (
        ('Organization Details', {
            'fields': ('company_name', 'email_domain', 'gst_number', 'account_type')
        }),
        ('Contact Person', {
            'fields': ('contact_person_name', 'contact_email', 'contact_phone', 'admin_user')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_at', 'rejected_at', 'approved_by', 'rejection_reason')
        }),
        ('Corporate Coupon', {
            'fields': ('corporate_coupon',)
        }),
        ('Control', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'linked_users_count'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_accounts', 'reject_accounts']
    
    @safe_admin_display()
    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            'pending_verification': ('#ffc107', '🟡 PENDING'),
            'approved': ('#28a745', '🟢 APPROVED'),
            'rejected': ('#dc3545', '🔴 REJECTED'),
        }
        color, badge_text = colors.get(obj.status, ('#6c757d', obj.get_status_display()))
        
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, badge_text
        )
    status_badge.short_description = 'Status'
    
    @safe_admin_display()
    def coupon_display(self, obj):
        """Display linked corporate coupon"""
        if obj.corporate_coupon:
            return format_html(
                '<code style="background: #28a745; color: white; padding: 3px 6px; border-radius: 3px;">{}</code>',
                obj.corporate_coupon.code
            )
        elif obj.status == 'approved':
            return format_html('<span style="color: #dc3545;">❌ Missing</span>')
        else:
            return format_html('<span style="color: #6c757d;">—</span>')
    coupon_display.short_description = 'Coupon'
    
    @safe_admin_display()
    def linked_users_count(self, obj):
        """Show number of users linked to this corporate account"""
        count = obj.get_linked_users().count()
        return format_html(
            '<span style="font-weight: bold; color: #0d6efd;">{} users</span>',
            count
        )
    linked_users_count.short_description = 'Linked Users'
    
    def approve_accounts(self, request, queryset):
        """Bulk action: Approve corporate accounts and auto-create coupons"""
        approved_count = 0
        for account in queryset.filter(status='pending_verification'):
            try:
                account.approve(admin_user=request.user)
                approved_count += 1
            except Exception as e:
                self.message_user(request, f"❌ Failed to approve {account.company_name}: {str(e)}", level='ERROR')
        
        if approved_count > 0:
            self.message_user(request, f"✅ {approved_count} corporate account(s) approved and coupons generated", level='SUCCESS')
    approve_accounts.short_description = "✅ Approve selected accounts (auto-creates coupons)"
    
    def reject_accounts(self, request, queryset):
        """Bulk action: Reject corporate accounts"""
        from django.contrib import messages as django_messages
        
        # For simplicity, use a default rejection reason for bulk action
        # In production, you might want a custom admin action with a form
        reason = "Bulk rejection by admin. Please contact support for details."
        
        rejected_count = 0
        for account in queryset.filter(status='pending_verification'):
            try:
                account.reject(admin_user=request.user, reason=reason)
                rejected_count += 1
            except Exception as e:
                self.message_user(request, f"❌ Failed to reject {account.company_name}: {str(e)}", level='ERROR')
        
        if rejected_count > 0:
            self.message_user(request, f"⏸️ {rejected_count} corporate account(s) rejected", level='WARNING')
    reject_accounts.short_description = "⏸️ Reject selected accounts"
