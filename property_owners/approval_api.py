"""
Property Owner Registration & Admin Approval API
Goibibo-grade REST endpoints
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date

from property_owners.models import Property, PropertyOwner
from property_owners.property_approval_models import (
    PropertyApprovalRequest, PropertyApprovalChecklist, PropertyApprovalAuditLog
)
from hotels.models import RoomType, RoomMealPlan, MealPlan, RoomImage
from rest_framework.serializers import (
    ModelSerializer, Serializer, CharField, DecimalField, 
    ListSerializer, IntegerField, BooleanField, DateField
)


# ======================== SERIALIZERS ========================

class PropertyOwnerSerializer(ModelSerializer):
    class Meta:
        model = PropertyOwner
        fields = [
            'id', 'business_name', 'property_type', 'owner_name', 'owner_phone',
            'owner_email', 'city', 'address', 'pincode', 'gst_number', 'pan_number',
            'is_active', 'average_rating', 'total_reviews'
        ]


class PropertySubmissionSerializer(ModelSerializer):
    """For owner submitting property for approval"""
    
    class Meta:
        model = Property
        fields = [
            'id', 'name', 'description', 'property_type', 'city', 'address',
            'state', 'pincode', 'latitude', 'longitude', 'contact_phone', 'contact_email',
            'checkin_time', 'checkout_time', 'property_rules', 'cancellation_policy',
            'cancellation_type', 'cancellation_days', 'refund_percentage',
            'has_wifi', 'has_parking', 'has_pool', 'has_gym', 'has_restaurant', 'has_spa', 'has_ac',
            'amenities', 'base_price', 'currency', 'gst_percentage', 'max_guests',
            'num_bedrooms', 'num_bathrooms', 'status', 'submitted_at'
        ]
        read_only_fields = ['id', 'status', 'submitted_at']


class RoomImageSerializer(ModelSerializer):
    class Meta:
        model = RoomImage
        fields = ['id', 'image', 'is_primary', 'display_order']


class MealPlanDetailsSerializer(ModelSerializer):
    class Meta:
        model = MealPlan
        fields = ['id', 'name', 'plan_type', 'inclusions', 'description', 'is_refundable']


class RoomMealPlanSerializer(ModelSerializer):
    meal_plan = MealPlanDetailsSerializer(read_only=True)
    
    class Meta:
        model = RoomMealPlan
        fields = ['id', 'meal_plan', 'price_delta', 'is_default', 'is_active', 'display_order']


class RoomTypeSerializer(ModelSerializer):
    images = RoomImageSerializer(many=True, read_only=True)
    meal_plans = RoomMealPlanSerializer(many=True, read_only=True)
    
    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'room_type', 'description', 'max_adults', 'max_children',
            'max_occupancy', 'bed_type', 'number_of_beds', 'room_size', 'base_price',
            'supports_hourly', 'hourly_price_6h', 'hourly_price_12h', 'hourly_price_24h',
            'is_refundable', 'total_rooms', 'is_available', 'status', 'images', 'meal_plans'
        ]


class PropertyApprovalRequestSerializer(ModelSerializer):
    property = PropertySubmissionSerializer(read_only=True)
    
    class Meta:
        model = PropertyApprovalRequest
        fields = [
            'id', 'property', 'status', 'submitted_at', 'submitted_by',
            'reviewed_at', 'reviewed_by', 'decision', 'approval_reason',
            'rejection_reason', 'admin_notes', 'approved_until'
        ]
        read_only_fields = ['id', 'submitted_at', 'submitted_by', 'reviewed_at', 'reviewed_by']


# ======================== VIEWS ========================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@atomic
def property_owner_register_property(request):
    """
    Owner registers a new property
    POST /api/property-owners/me/properties/
    
    Only authenticated property owners can register.
    """
    try:
        owner = request.user.property_owner_profile
    except PropertyOwner.DoesNotExist:
        return Response(
            {'error': 'Not a registered property owner'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = PropertySubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Create property in DRAFT
    property_obj = serializer.save(owner=owner, status='DRAFT')
    
    return Response(
        PropertySubmissionSerializer(property_obj).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@atomic
def property_owner_submit_for_approval(request, property_id):
    """
    Owner submits property for admin approval
    POST /api/property-owners/properties/{id}/submit-for-approval/
    
    Prerequisites:
    - Property in DRAFT status
    - All required fields complete
    - At least 1 room type with 3+ images
    - At least 1 meal plan per room
    """
    property_obj = get_object_or_404(Property, id=property_id, owner__user=request.user)
    
    if property_obj.status != 'DRAFT':
        return Response(
            {'error': f'Property must be in DRAFT status (currently {property_obj.status})'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate all room types are ready
    rooms_not_ready = property_obj.room_types.exclude(status='READY').exists()
    if rooms_not_ready:
        return Response(
            {'error': 'All room types must be READY before submission. Check room details, images, and meal plans.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create approval request
    try:
        submission_data = {
            'name': property_obj.name,
            'city': property_obj.city.name,
            'address': property_obj.address,
            'num_rooms': property_obj.room_types.count(),
            'base_price': str(property_obj.base_price) if property_obj.base_price else '0',
        }
        
        approval_request = PropertyApprovalRequest.objects.create(
            property=property_obj,
            status='SUBMITTED',
            submitted_by=request.user,
            submission_data=submission_data
        )
        
        # Create approval checklist
        checklist = PropertyApprovalChecklist.objects.create(approval_request=approval_request)
        checklist.initialize_checklist()
        
        # Create audit log
        PropertyApprovalAuditLog.objects.create(
            approval_request=approval_request,
            action='SUBMITTED',
            performed_by=request.user,
            action_details={'submission_time': timezone.now().isoformat()}
        )
        
        # Update property status
        property_obj.status = 'PENDING'
        property_obj.submitted_at = timezone.now()
        property_obj.save(update_fields=['status', 'submitted_at'])
        
        return Response(
            PropertyApprovalRequestSerializer(approval_request).data,
            status=status.HTTP_201_CREATED
        )
    
    except Exception as e:
        return Response(
            {'error': f'Failed to submit for approval: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def property_owner_list_submissions(request):
    """
    List all approval requests for owner's properties
    GET /api/property-owners/me/submissions/
    """
    requests = PropertyApprovalRequest.objects.filter(
        property__owner__user=request.user
    ).select_related('property', 'submitted_by', 'reviewed_by')
    
    serializer = PropertyApprovalRequestSerializer(requests, many=True)
    return Response(serializer.data)


# ======================== ADMIN APPROVAL ENDPOINTS ========================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_list_approval_requests(request):
    """
    Admin lists all pending approval requests
    GET /api/admin/property-approvals/
    """
    status_filter = request.query_params.get('status', 'SUBMITTED')
    
    requests = PropertyApprovalRequest.objects.filter(
        status=status_filter
    ).select_related('property', 'submitted_by').order_by('-submitted_at')
    
    page = request.query_params.get('page', 1)
    page_size = 20
    
    start = (int(page) - 1) * page_size
    end = start + page_size
    
    total = requests.count()
    requests_paginated = requests[start:end]
    
    return Response({
        'total': total,
        'page': page,
        'page_size': page_size,
        'results': PropertyApprovalRequestSerializer(requests_paginated, many=True).data
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
@atomic
def admin_approve_property(request, approval_request_id):
    """
    Admin approves a property
    POST /api/admin/property-approvals/{id}/approve/
    
    Request body:
    {
      "approval_reason": "Property meets all requirements",
      "approved_until": "2026-12-31"  # optional
    }
    """
    approval_req = get_object_or_404(PropertyApprovalRequest, id=approval_request_id)
    
    if approval_req.status in ['APPROVED', 'REVOKED']:
        return Response(
            {'error': f'Cannot approve {approval_req.status} request'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    approval_reason = request.data.get('approval_reason', '')
    approved_until = request.data.get('approved_until')
    
    try:
        approval_req.approve(
            admin_user=request.user,
            approval_reason=approval_reason,
            approved_until=approved_until
        )
        
        # Create audit log
        PropertyApprovalAuditLog.objects.create(
            approval_request=approval_req,
            action='APPROVED',
            performed_by=request.user,
            action_details={'reason': approval_reason}
        )
        
        return Response(
            PropertyApprovalRequestSerializer(approval_req).data,
            status=status.HTTP_200_OK
        )
    
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
@atomic
def admin_reject_property(request, approval_request_id):
    """
    Admin rejects a property
    POST /api/admin/property-approvals/{id}/reject/
    
    Request body:
    {
      "rejection_reason": "Images are not high quality enough"
    }
    """
    approval_req = get_object_or_404(PropertyApprovalRequest, id=approval_request_id)
    rejection_reason = request.data.get('rejection_reason', '')
    
    if not rejection_reason.strip():
        return Response(
            {'error': 'Rejection reason is mandatory'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        approval_req.reject(
            admin_user=request.user,
            rejection_reason=rejection_reason
        )
        
        # Create audit log
        PropertyApprovalAuditLog.objects.create(
            approval_request=approval_req,
            action='REJECTED',
            performed_by=request.user,
            action_details={'reason': rejection_reason}
        )
        
        return Response(
            PropertyApprovalRequestSerializer(approval_req).data,
            status=status.HTTP_200_OK
        )
    
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
@atomic
def admin_revoke_approval(request, approval_request_id):
    """
    Admin revokes previously approved property
    POST /api/admin/property-approvals/{id}/revoke/
    
    Request body:
    {
      "revocation_reason": "Violation of terms"
    }
    """
    approval_req = get_object_or_404(PropertyApprovalRequest, id=approval_request_id)
    revocation_reason = request.data.get('revocation_reason', '')
    
    try:
        approval_req.revoke_approval(
            admin_user=request.user,
            revocation_reason=revocation_reason
        )
        
        # Create audit log
        PropertyApprovalAuditLog.objects.create(
            approval_request=approval_req,
            action='REVOKED',
            performed_by=request.user,
            action_details={'reason': revocation_reason}
        )
        
        return Response(
            PropertyApprovalRequestSerializer(approval_req).data,
            status=status.HTTP_200_OK
        )
    
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_property_details(request, property_id):
    """
    Admin view full property details for approval review
    GET /api/admin/properties/{id}/
    """
    property_obj = get_object_or_404(Property, id=property_id)
    
    data = {
        'property': PropertySubmissionSerializer(property_obj).data,
        'rooms': RoomTypeSerializer(property_obj.room_types.all(), many=True).data,
        'approval_requests': PropertyApprovalRequestSerializer(
            property_obj.approval_requests.all(),
            many=True
        ).data,
    }
    
    return Response(data)
