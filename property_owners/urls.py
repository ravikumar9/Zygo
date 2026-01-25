from django.urls import path
from . import views
from . import owner_views, admin_views
from . import property_owner_registration_api, admin_approval_verification_api, update_api

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
    path('owner/onboarding/', owner_views.owner_onboarding, name='owner-onboarding'),
    path('owner/property/<int:pk>/', owner_views.PropertyDetailsView.as_view(), name='property-details'),
    path('owner/submit-update/<int:hotel_id>/', owner_views.submit_update_request, name='submit-update'),
    path('owner/upload-images/<int:room_type_id>/', owner_views.upload_room_images, name='upload-images'),
    path('owner/pricing/<int:room_type_id>/', owner_views.manage_seasonal_pricing, name='manage-pricing'),
    path('owner/update-requests/', owner_views.view_update_requests, name='view-requests'),
    
    # Owner onboarding room management
    path('owner/hotel/<int:hotel_id>/rooms/', owner_views.hotel_room_list, name='room-list'),
    path('owner/hotel/<int:hotel_id>/rooms/add/', owner_views.room_type_create, name='room-create'),
    path('owner/hotel/<int:hotel_id>/room/<int:room_id>/edit/', owner_views.room_type_edit, name='room-edit'),
    path('owner/hotel/<int:hotel_id>/room/<int:room_id>/images/', owner_views.room_images_manage, name='room-images'),
    path('owner/hotel/<int:hotel_id>/room/<int:room_id>/delete/', owner_views.room_type_delete, name='room-delete'),

    # Sprint-1: Room Availability Calendar
    path('owner/room/<int:room_id>/calendar/', owner_views.room_calendar, name='room-calendar'),
    path('owner/room/<int:room_id>/block/', owner_views.block_dates, name='block-dates'),
    path('owner/room/<int:room_id>/bulk-block/', owner_views.bulk_block_dates, name='bulk-block-dates'),
    path('owner/block/<int:block_id>/unblock/', owner_views.unblock_dates, name='unblock-dates'),
    
    # Sprint-1: Payout Requests
    path('owner/payout/request/', owner_views.request_payout, name='payout-request'),
    path('owner/payout/history/', owner_views.payout_history, name='payout-history'),
    
    # Admin approval endpoints
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin-dashboard'),
    path('admin/update-requests/', admin_views.AdminUpdateRequestsView.as_view(), name='admin-update-requests'),
    path('admin/approve/<int:request_id>/', admin_views.approve_update_request, name='approve-request'),
    path('admin/reject/<int:request_id>/', admin_views.reject_update_request, name='reject-request'),
    path('admin/approval-history/', admin_views.view_approval_history, name='approval-history'),
    
    # Sprint-1: Admin Payout Approval
    path('admin/payouts/', admin_views.admin_payout_requests, name='admin-payouts'),
    path('admin/payout/<int:payout_id>/approve/', admin_views.approve_payout, name='approve-payout'),
    path('admin/payout/<int:payout_id>/reject/', admin_views.reject_payout, name='reject-payout'),
    
    # Admin workflow
    path('admin/pending/', views.admin_pending_properties, name='admin-pending'),
    path('admin/approve/<int:property_id>/', views.admin_approve_property, name='admin-approve'),
    path('admin/reject/<int:property_id>/', views.admin_reject_property, name='admin-reject'),
    
    # Live edit for approved rooms (pricing, discount, inventory)
    path('property/<int:property_id>/room/<int:room_id>/edit-live/', views.edit_room_after_approval, name='edit-room-live'),
    
    # ====== PHASE 1: COMPLETE PROPERTY OWNER REGISTRATION FLOW (NEW) ======
    
    # Owner Registration & Property Management APIs
    path('api/property-owners/register/', 
         property_owner_registration_api.register_property, 
         name='register_property'),
    
    # Room Management APIs
    path('api/property-owners/properties/<int:property_id>/rooms/', 
         property_owner_registration_api.add_room_type, 
         name='add_room_type'),
    
    path('api/property-owners/properties/<int:property_id>/rooms/<int:room_id>/images/', 
         property_owner_registration_api.upload_room_images, 
         name='upload_room_images'),

    path('api/property-owners/properties/<int:property_id>/images/', 
         property_owner_registration_api.upload_property_images, 
         name='upload_property_images'),
    
    # Property Submission & Status APIs
    path('api/property-owners/properties/<int:property_id>/submit-approval/', 
         property_owner_registration_api.submit_property_for_approval, 
         name='submit_property_approval'),
    
    path('api/property-owners/my-properties/', 
         property_owner_registration_api.list_owner_properties, 
         name='list_owner_properties'),
    
    path('api/property-owners/properties/<int:property_id>/', 
         property_owner_registration_api.get_property_details, 
         name='get_property_details'),

    # Owner update requests (post-approval edits)
    path('api/property-owners/properties/<int:property_id>/updates/',
         update_api.create_update_request,
         name='create_update_request'),
    
    # Admin Approval APIs
    path('api/admin/property-approvals/pending/', 
         property_owner_registration_api.admin_list_pending_approvals, 
         name='admin_list_pending'),
    
    path('api/admin/properties/<int:property_id>/approve/', 
         property_owner_registration_api.admin_approve_property, 
         name='admin_approve_property'),
    
    path('api/admin/properties/<int:property_id>/reject/', 
         property_owner_registration_api.admin_reject_property, 
         name='admin_reject_property'),
    
    # Admin Verification APIs (with checklist)
    path('api/admin/properties/', 
         admin_approval_verification_api.admin_list_all_properties, 
         name='admin_list_all_properties'),
    
    path('api/admin/properties/<int:property_id>/verify/', 
         admin_approval_verification_api.admin_verify_property_submission, 
         name='admin_verify_property'),

    # Admin update approval APIs
    path('api/admin/update-requests/',
         update_api.admin_list_update_requests,
         name='admin_list_update_requests'),
    path('api/admin/update-requests/<int:request_id>/approve/',
         update_api.admin_approve_update_request,
         name='admin_approve_update_request'),
    path('api/admin/update-requests/<int:request_id>/reject/',
         update_api.admin_reject_update_request,
         name='admin_reject_update_request'),
    
    # UI Routes
    path('owner/registration/', views.property_registration_form, name='registration_form'),
    path('admin/approval-dashboard/', views.admin_approval_dashboard, name='approval_dashboard'),
]
