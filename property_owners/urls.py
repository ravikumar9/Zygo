from django.urls import path
from . import views
from . import owner_views, admin_views

app_name = 'property_owners'

urlpatterns = [
    # Legacy endpoints
    path('register/', views.register_property_owner, name='register'),
    path('dashboard/', views.property_owner_dashboard, name='dashboard'),
    path('property/create/', views.create_property_draft, name='create_property'),
    path('property/<int:property_id>/detail/', views.property_detail, name='property_detail'),
    path('property/<int:property_id>/check-completion/', views.property_check_completion, name='check_completion'),
    
    # New role-based owner endpoints
    path('owner/dashboard/', owner_views.OwnerDashboardView.as_view(), name='owner-dashboard'),
    path('owner/property/<int:pk>/', owner_views.PropertyDetailsView.as_view(), name='property-details'),
    path('owner/submit-update/<int:hotel_id>/', owner_views.submit_update_request, name='submit-update'),
    path('owner/upload-images/<int:room_type_id>/', owner_views.upload_room_images, name='upload-images'),
    path('owner/pricing/<int:room_type_id>/', owner_views.manage_seasonal_pricing, name='manage-pricing'),
    path('owner/update-requests/', owner_views.view_update_requests, name='view-requests'),
    
    # Admin approval endpoints
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin-dashboard'),
    path('admin/update-requests/', admin_views.AdminUpdateRequestsView.as_view(), name='admin-update-requests'),
    path('admin/approve/<int:request_id>/', admin_views.approve_update_request, name='approve-request'),
    path('admin/reject/<int:request_id>/', admin_views.reject_update_request, name='reject-request'),
    path('admin/approval-history/', admin_views.view_approval_history, name='approval-history'),
    # Admin workflow
    path('admin/pending/', views.admin_pending_properties, name='admin-pending'),
    path('admin/approve/<int:property_id>/', views.admin_approve_property, name='admin-approve'),
    path('admin/reject/<int:property_id>/', views.admin_reject_property, name='admin-reject'),
]
