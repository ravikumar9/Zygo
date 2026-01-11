from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile
from .models_otp import UserOTP


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'phone', 'email_verified', 'phone_verified', 'is_staff']
    list_filter = ['email_verified', 'phone_verified', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'phone', 'first_name', 'last_name']
    inlines = [UserProfileInline]
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone', 'date_of_birth', 'profile_image', 'email_verified', 'phone_verified',
                      'email_verified_at', 'phone_verified_at')
        }),
    )
    
    readonly_fields = ['email_verified_at', 'phone_verified_at']


@admin.register(UserOTP)
class UserOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp_type', 'contact', 'created_at', 'expires_at', 'is_verified', 'attempts']
    list_filter = ['otp_type', 'is_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'contact', 'otp_code']
    readonly_fields = ['otp_code', 'created_at', 'expires_at', 'verified_at', 'attempts']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False  # OTPs should only be created via service
