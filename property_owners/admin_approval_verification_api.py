"""
ADMIN APPROVAL VERIFICATION API

Endpoints for admin to review and verify property submissions with
detailed checklist validation and approval workflow.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.transaction import atomic

from property_owners.models import Property, PropertyRoomType
from property_owners.property_approval_models import (
    PropertyApprovalRequest, PropertyApprovalChecklist,
    PropertyApprovalAuditLog
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_verify_property_submission(request, property_id):
    """
    Admin views detailed verification checklist for a property
    
    GET /api/admin/properties/{property_id}/verify/
    
    Returns:
    {
        "property": {...},
        "checklist": {
            "core_info": {"complete": true, "items": [...]},
            "contact_info": {...},
            "policies": {...},
            "amenities": {...},
            "room_types": {...},
            "images": {...},
            "meal_plans": {...},
            "overall_ready": true
        },
        "approval_history": [...]
    }
    """
    if not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        prop = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Build verification checklist
    checklist = {
        'core_info': verify_core_info(prop),
        'location': verify_location(prop),
        'contact_info': verify_contact_info(prop),
        'policies': verify_policies(prop),
        'amenities': verify_amenities(prop),
        'room_types': verify_room_types(prop),
        'images': verify_images(prop),
        'meal_plans': verify_meal_plans(prop),
        'discounts': verify_discounts(prop),
    }
    
    # Overall readiness
    all_complete = all(
        item['complete'] for item in checklist.values()
    )
    
    return Response(
        {
            'property': {
                'id': prop.id,
                'name': prop.name,
                'status': prop.status,
                'owner': prop.owner.user.email,
                'submitted_at': prop.submitted_at,
            },
            'checklist': {
                **checklist,
                'overall_ready': all_complete,
                'completion_percentage': calculate_completion(checklist),
            },
            'approval_history': get_approval_history(prop),
        },
        status=status.HTTP_200_OK
    )


def verify_core_info(prop):
    """Verify core property information"""
    checks = {
        'name': bool(prop.name and prop.name.strip()),
        'description': bool(prop.description and len(prop.description) >= 50),
        'property_type': bool(prop.property_type),
        'max_guests': prop.max_guests > 0,
        'bedrooms': prop.num_bedrooms > 0,
        'bathrooms': prop.num_bathrooms > 0,
    }
    return {
        'complete': all(checks.values()),
        'items': [
            {'name': 'Property Name', 'status': 'pass' if checks['name'] else 'fail'},
            {'name': 'Description (50+ chars)', 'status': 'pass' if checks['description'] else 'fail'},
            {'name': 'Property Type', 'status': 'pass' if checks['property_type'] else 'fail'},
            {'name': 'Max Guests', 'status': 'pass' if checks['max_guests'] else 'fail'},
            {'name': 'Bedrooms', 'status': 'pass' if checks['bedrooms'] else 'fail'},
            {'name': 'Bathrooms', 'status': 'pass' if checks['bathrooms'] else 'fail'},
        ]
    }


def verify_location(prop):
    """Verify location details"""
    checks = {
        'city': bool(prop.city),
        'address': bool(prop.address and len(prop.address) >= 10),
        'pincode': bool(prop.pincode),
    }
    return {
        'complete': all(checks.values()),
        'items': [
            {'name': 'City Selected', 'status': 'pass' if checks['city'] else 'fail'},
            {'name': 'Address (10+ chars)', 'status': 'pass' if checks['address'] else 'fail'},
            {'name': 'Pincode', 'status': 'pass' if checks['pincode'] else 'fail'},
        ]
    }


def verify_contact_info(prop):
    """Verify contact details"""
    checks = {
        'phone': bool(prop.contact_phone and len(prop.contact_phone) >= 10),
        'email': bool(prop.contact_email),
    }
    return {
        'complete': all(checks.values()),
        'items': [
            {'name': 'Phone (10+ digits)', 'status': 'pass' if checks['phone'] else 'fail'},
            {'name': 'Email', 'status': 'pass' if checks['email'] else 'fail'},
        ]
    }


def verify_policies(prop):
    """Verify property policies"""
    checks = {
        'checkin': bool(prop.checkin_time),
        'checkout': bool(prop.checkout_time),
        'rules': bool(prop.property_rules and len(prop.property_rules) >= 20),
        'cancellation_policy': bool(prop.cancellation_policy),
        'cancellation_type': bool(prop.cancellation_type),
    }
    return {
        'complete': all(checks.values()),
        'items': [
            {'name': 'Check-in Time', 'status': 'pass' if checks['checkin'] else 'fail'},
            {'name': 'Check-out Time', 'status': 'pass' if checks['checkout'] else 'fail'},
            {'name': 'Property Rules (20+ chars)', 'status': 'pass' if checks['rules'] else 'fail'},
            {'name': 'Cancellation Policy', 'status': 'pass' if checks['cancellation_policy'] else 'fail'},
            {'name': 'Cancellation Type', 'status': 'pass' if checks['cancellation_type'] else 'fail'},
        ]
    }


def verify_amenities(prop):
    """Verify amenities (at least 3 selected)"""
    amenity_count = sum([
        prop.has_wifi,
        prop.has_parking,
        prop.has_pool,
        prop.has_gym,
        prop.has_restaurant,
        prop.has_spa,
        prop.has_ac,
    ])
    has_min_amenities = amenity_count >= 3
    
    return {
        'complete': has_min_amenities,
        'items': [
            {'name': f'Amenities Selected (3+)', 'status': 'pass' if has_min_amenities else 'fail', 'detail': f'{amenity_count} selected'},
            {'name': 'WiFi', 'status': 'yes' if prop.has_wifi else 'no'},
            {'name': 'Parking', 'status': 'yes' if prop.has_parking else 'no'},
            {'name': 'Pool', 'status': 'yes' if prop.has_pool else 'no'},
            {'name': 'Gym', 'status': 'yes' if prop.has_gym else 'no'},
            {'name': 'Restaurant', 'status': 'yes' if prop.has_restaurant else 'no'},
            {'name': 'Spa', 'status': 'yes' if prop.has_spa else 'no'},
            {'name': 'AC', 'status': 'yes' if prop.has_ac else 'no'},
        ]
    }


def verify_room_types(prop):
    """Verify at least 1 room type with required fields"""
    rooms = PropertyRoomType.objects.filter(property=prop)
    has_rooms = rooms.count() > 0
    
    room_items = []
    all_complete = True
    
    for room in rooms:
        room_ok = (
            bool(room.name) and
            room.max_occupancy > 0 and
            room.number_of_beds > 0 and
            room.room_size > 0 and
            room.base_price > 0 and
            room.total_rooms > 0
        )
        room_items.append({
            'name': room.name,
            'status': 'pass' if room_ok else 'fail',
            'detail': f'Max Occupancy: {room.max_occupancy}, Beds: {room.number_of_beds}, Size: {room.room_size}m², Price: ₹{room.base_price}'
        })
        if not room_ok:
            all_complete = False
    
    return {
        'complete': has_rooms and all_complete,
        'items': [
            {'name': f'Room Types (1+)', 'status': 'pass' if has_rooms else 'fail', 'detail': f'{rooms.count()} rooms'},
            *room_items
        ]
    }


def verify_images(prop):
    """Verify images for each room (minimum 3 per room)"""
    rooms = PropertyRoomType.objects.filter(property=prop)
    
    image_items = []
    all_complete = True
    
    for room in rooms:
        image_count = room.images.count()
        has_min = image_count >= 3
        image_items.append({
            'name': f'{room.name} Images',
            'status': 'pass' if has_min else 'fail',
            'detail': f'{image_count} images' + (' ✓' if has_min else ' (need 3+)')
        })
        if not has_min:
            all_complete = False
    
    return {
        'complete': all_complete and len(image_items) > 0,
        'items': image_items if image_items else [
            {'name': 'Room Images', 'status': 'fail', 'detail': 'No rooms created'}
        ]
    }


def verify_meal_plans(prop):
    """Verify meal plans for each room"""
    rooms = PropertyRoomType.objects.filter(property=prop)
    
    meal_items = []
    all_complete = True
    
    for room in rooms:
        has_meals = room.meal_plans and len(room.meal_plans) > 0
        meal_items.append({
            'name': f'{room.name} Meal Plans',
            'status': 'pass' if has_meals else 'fail',
            'detail': f'{len(room.meal_plans) if has_meals else 0} plans configured'
        })
        if not has_meals:
            all_complete = False
    
    return {
        'complete': all_complete and len(meal_items) > 0,
        'items': meal_items if meal_items else [
            {'name': 'Meal Plans', 'status': 'fail', 'detail': 'No rooms created'}
        ]
    }


def verify_discounts(prop):
    """Verify discount configuration (optional but validate if present)"""
    rooms = PropertyRoomType.objects.filter(property=prop)
    
    discount_items = []
    for room in rooms:
        if room.discount_type != 'none':
            is_valid = (
                room.discount_value > 0 and
                room.discount_type in ['percentage', 'fixed']
            )
            discount_items.append({
                'name': f'{room.name} Discount',
                'status': 'pass' if is_valid else 'fail',
                'detail': f'{room.discount_type.title()}: {room.discount_value}'
            })
    
    return {
        'complete': True,  # Optional field
        'items': discount_items if discount_items else [
            {'name': 'Discounts', 'status': 'info', 'detail': 'No discounts configured (optional)'}
        ]
    }


def calculate_completion(checklist):
    """Calculate overall completion percentage"""
    total_items = 0
    completed_items = 0
    
    for section in checklist.values():
        for item in section.get('items', []):
            status_val = item.get('status', '')
            if status_val in ['pass', 'yes']:
                completed_items += 1
            total_items += 1
    
    if total_items == 0:
        return 0
    
    return int((completed_items / total_items) * 100)


def get_approval_history(prop):
    """Get approval audit trail"""
    approvals = PropertyApprovalAuditLog.objects.filter(
        property=prop
    ).order_by('-created_at')
    
    return [
        {
            'date': approval.created_at.isoformat(),
            'action': approval.action,
            'by': approval.approved_by.email if approval.approved_by else 'System',
            'notes': approval.notes,
        }
        for approval in approvals
    ]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_list_all_properties(request):
    """
    Admin views all properties with their current status
    
    GET /api/admin/properties/
    
    Query params:
    - status: DRAFT, PENDING, APPROVED, REJECTED (filter by status)
    """
    if not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    query = Property.objects.all()
    
    # Filter by status if provided
    status_filter = request.query_params.get('status', '').upper()
    if status_filter in ['DRAFT', 'PENDING', 'APPROVED', 'REJECTED']:
        query = query.filter(status=status_filter)
    
    properties = query.order_by('-submitted_at')
    
    return Response(
        {
            'total': query.count(),
            'results': [
                {
                    'id': prop.id,
                    'name': prop.name,
                    'owner': prop.owner.user.email,
                    'status': prop.status,
                    'submitted_at': prop.submitted_at,
                    'approved_at': prop.approved_at,
                    'rooms': PropertyRoomType.objects.filter(property=prop).count(),
                    'completion': prop.completion_percentage,
                }
                for prop in properties
            ]
        },
        status=status.HTTP_200_OK
    )
