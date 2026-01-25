"""
API URL routing for property approval and booking
"""

from django.urls import path
from property_owners.approval_api import (
    property_owner_register_property,
    property_owner_submit_for_approval,
    property_owner_list_submissions,
    admin_list_approval_requests,
    admin_approve_property,
    admin_reject_property,
    admin_revoke_approval,
    admin_property_details,
)
from bookings.booking_api import (
    create_hotel_booking,
    get_booking_details,
    list_available_rooms,
    get_pricing_breakdown,
    complete_booking_payment,
)

# Property Owner endpoints
property_owner_patterns = [
    path('me/properties/', property_owner_register_property, name='owner_register_property'),
    path('properties/<int:property_id>/submit-for-approval/', property_owner_submit_for_approval, name='owner_submit_approval'),
    path('me/submissions/', property_owner_list_submissions, name='owner_list_submissions'),
]

# Admin endpoints
admin_patterns = [
    path('property-approvals/', admin_list_approval_requests, name='admin_approvals_list'),
    path('property-approvals/<int:approval_request_id>/approve/', admin_approve_property, name='admin_approve'),
    path('property-approvals/<int:approval_request_id>/reject/', admin_reject_property, name='admin_reject'),
    path('property-approvals/<int:approval_request_id>/revoke/', admin_revoke_approval, name='admin_revoke'),
    path('properties/<int:property_id>/', admin_property_details, name='admin_property_detail'),
]

# Booking endpoints
booking_patterns = [
    path('bookings/hotel/', create_hotel_booking, name='create_hotel_booking'),
    path('bookings/<str:booking_id>/', get_booking_details, name='get_booking'),
    path('bookings/<str:booking_id>/pay/', complete_booking_payment, name='complete_booking_payment'),
    path('rooms/available/', list_available_rooms, name='list_available_rooms'),
    path('rooms/<int:room_type_id>/pricing/', get_pricing_breakdown, name='get_pricing'),
]

urlpatterns = property_owner_patterns + admin_patterns + booking_patterns
