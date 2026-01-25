"""
URL configuration for goexplorer project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    # Playwright-friendly owner routes
    path('owner/', include(('property_owners.e2e_urls', 'owner_e2e'), namespace='owner-e2e')),
    path('admin/property-approvals/', __import__('property_owners.e2e_views').e2e_views.admin_property_approvals, name='admin-property-approvals'),
    path('admin/property-approvals/<int:property_id>/', __import__('property_owners.e2e_views').e2e_views.admin_property_approval_detail, name='admin-property-approval-detail'),
    path('admin/', admin.site.urls),
    path('dashboard/', include('dashboard.urls')),
    path('', include('core.urls')),
    # Corporate dashboard routes
    path('corporate/', include('core.urls_corporate')),
    # Property owner self-service (Phase-2)
    path('properties/', include('property_owners.urls')),
    # Web page routes with unique namespaces
    # Web routes (use each app's native namespace)
    path('hotels/', include(('hotels.urls', 'hotels'), namespace='hotels')),
    path('buses/', include(('buses.urls', 'buses'), namespace='buses')),
    path('packages/', include(('packages.urls', 'packages'), namespace='packages')),
    path('bookings/', include(('bookings.urls', 'bookings'), namespace='bookings')),
    path('payments/', include(('payments.urls', 'payments'), namespace='payments')),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('login/', __import__('users').views.login_view, name='login'),
    path('logout/', __import__('users').views.logout_view, name='logout'),
    # API endpoints with api- prefix and unique namespaces
    path('api/admin/', include('hotels.admin_urls')),  # Admin API for live updates
    path('api/hotels/', include(('hotels.urls', 'hotels'), namespace='hotels-api')),
    path('api/buses/', include(('buses.urls', 'buses'), namespace='buses-api')),
    path('api/packages/', include(('packages.urls', 'packages'), namespace='packages-api')),
    path('api/bookings/', include(('bookings.urls', 'bookings'), namespace='bookings-api')),
    path('api/payments/', include(('payments.urls', 'payments'), namespace='payments-api')),
    path('api/users/', include(('users.api_urls', 'users_api'), namespace='users-api')),
    # Finance API (Phase-3)
    path('api/finance/', include(('finance.api_urls', 'finance_api'), namespace='finance-api')),
    # Finance routes (Phase-3)
    path('finance/', include(('finance.urls', 'finance'), namespace='finance')),
]

# Serve media files (enable in dev or when SERVE_MEDIA_FILES is true)
if getattr(settings, "SERVE_MEDIA_FILES", settings.DEBUG):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "GoExplorer Admin"
admin.site.site_title = "GoExplorer Admin Portal"
admin.site.index_title = "Welcome to GoExplorer Administration"
