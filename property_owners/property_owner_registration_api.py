"""
PROPERTY OWNER REGISTRATION FLOW - COMPLETE IMPLEMENTATION

This module handles the complete property owner submission flow:
1. Owner registers property (DRAFT)
2. Owner adds rooms, images, pricing, discounts, amenities, meal plans
3. Owner submits for approval (PENDING)
4. Admin reviews and approves/rejects (APPROVED/REJECTED)
5. User sees APPROVED properties only

MANDATORY FIELDS FOR SUBMISSION:
✅ Property: name, description, city, address, contact, rules, cancellation policy
✅ Room Types: base_price, max_occupancy, number_of_beds, room_size
✅ Room Images: minimum 3 per room
✅ Meal Plans: at least 1 per room
✅ Amenities: at least 3 selections
✅ Discounts: optional (property-level or room-level)
"""

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.transaction import atomic
from django.utils import timezone
from decimal import Decimal
import json

from property_owners.models import (
    Property, PropertyOwner, PropertyRoomType, PropertyRoomImage,
    PropertyImage, PropertyAmenity
)


# ======================== SERIALIZERS ========================

class PropertyRoomImageSerializer(serializers.ModelSerializer):
    """Images for a room (gallery)"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyRoomImage
        fields = ['id', 'image', 'image_url', 'is_primary', 'display_order', 'caption']
    
    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class PropertyRoomTypeSubmissionSerializer(serializers.ModelSerializer):
    """Room type with discounts, amenities, meal plans"""
    images = PropertyRoomImageSerializer(many=True, read_only=True)
    current_price = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyRoomType
        fields = [
            'id', 'name', 'room_type', 'description',
            'max_occupancy', 'number_of_beds', 'room_size',
            'base_price',
            # DISCOUNTS
            'discount_type', 'discount_value', 'discount_valid_from',
            'discount_valid_to', 'discount_is_active',
            # INVENTORY
            'total_rooms',
            # AMENITIES (as JSON)
            'amenities',
            # MEAL PLANS (as JSON)
            'meal_plans',
            # STATUS
            'is_active', 'current_price', 'images'
        ]
    
    def get_current_price(self, obj):
        return str(obj.get_effective_price())


class PropertyImageSerializer(serializers.ModelSerializer):
    """Property-level images (for property gallery before rooms)"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'image_url', 'caption', 'is_primary']
    
    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class PropertySubmissionSerializer(serializers.ModelSerializer):
    """
    COMPLETE property submission for owner → admin workflow
    Includes all fields: core, pricing, discounts, images, rules, amenities, meal plans
    """
    
    # Nested serializers
    room_types = PropertyRoomTypeSubmissionSerializer(many=True, read_only=True)
    images = PropertyImageSerializer(many=True, read_only=True)
    
    # Checklist status
    required_fields_status = serializers.SerializerMethodField()
    completion_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = [
            # CORE PROPERTY DETAILS
            'id', 'name', 'description', 'property_type',
            
            # LOCATION
            'city', 'address', 'state', 'pincode', 'latitude', 'longitude',
            
            # CONTACT
            'contact_phone', 'contact_email',
            
            # POLICIES (MANDATORY)
            'checkin_time', 'checkout_time', 'property_rules',
            'cancellation_policy', 'cancellation_type', 'cancellation_days',
            'refund_percentage',
            
            # AMENITIES (MANDATORY)
            'has_wifi', 'has_parking', 'has_pool', 'has_gym',
            'has_restaurant', 'has_spa', 'has_ac', 'amenities',
            
            # PRICING (MANDATORY)
            'base_price', 'currency', 'gst_percentage',
            
            # CAPACITY
            'max_guests', 'num_bedrooms', 'num_bathrooms',
            
            # NESTED
            'room_types', 'images',
            
            # STATUS
            'status', 'submitted_at', 'approved_at', 'rejection_reason',
            'is_active',
            
            # METADATA
            'required_fields_status', 'completion_status',
        ]
    
    def get_required_fields_status(self, obj):
        """Get validation status for all required fields"""
        checks, is_complete = obj.has_required_fields()
        return {
            'is_complete': is_complete,
            'details': checks,
        }
    
    def get_completion_status(self, obj):
        """Completion percentage for UI progress bar"""
        return {
            'percentage': obj.completion_percentage,
            'status': 'ready_to_submit' if obj.completion_percentage >= 80 else 'incomplete',
        }


class RoomTypeInputSerializer(serializers.Serializer):
    """Input for creating/updating room type"""
    name = serializers.CharField(max_length=100)
    room_type = serializers.CharField(max_length=20)
    description = serializers.CharField()
    max_occupancy = serializers.IntegerField(min_value=1)
    number_of_beds = serializers.IntegerField(min_value=1)
    room_size = serializers.IntegerField(min_value=100)
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_rooms = serializers.IntegerField(min_value=1)
    
    # DISCOUNTS (OPTIONAL)
    discount_type = serializers.CharField(required=False, default='none')
    discount_value = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    discount_valid_from = serializers.DateField(required=False, allow_null=True)
    discount_valid_to = serializers.DateField(required=False, allow_null=True)
    discount_is_active = serializers.BooleanField(required=False, default=False)
    
    # AMENITIES (as list, OPTIONAL)
    amenities = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=[]
    )
    
    # MEAL PLANS (as list of dicts, MANDATORY)
    meal_plans = serializers.ListField(
        child=serializers.DictField(),
        required=True,
    )


class PropertyOwnerRegistrationSerializer(serializers.Serializer):
    """Input for owner property registration"""
    
    # PROPERTY CORE (MANDATORY)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField()
    property_type = serializers.IntegerField()  # PropertyType.id
    
    # LOCATION (MANDATORY)
    city = serializers.IntegerField()  # City.id
    address = serializers.CharField()
    state = serializers.CharField(max_length=100, required=False)
    pincode = serializers.CharField(max_length=10)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    
    # CONTACT (MANDATORY)
    contact_phone = serializers.CharField(max_length=20)
    contact_email = serializers.EmailField()
    
    # POLICIES (MANDATORY)
    checkin_time = serializers.TimeField()
    checkout_time = serializers.TimeField()
    property_rules = serializers.CharField()
    cancellation_policy = serializers.CharField()
    cancellation_type = serializers.CharField(max_length=50)
    cancellation_days = serializers.IntegerField(required=False, allow_null=True)
    refund_percentage = serializers.IntegerField(default=100)
    
    # AMENITIES (MANDATORY - at least 3)
    has_wifi = serializers.BooleanField()
    has_parking = serializers.BooleanField()
    has_pool = serializers.BooleanField()
    has_gym = serializers.BooleanField()
    has_restaurant = serializers.BooleanField()
    has_spa = serializers.BooleanField()
    has_ac = serializers.BooleanField()
    amenities = serializers.CharField(required=False, allow_blank=True)  # Free text
    
    # CAPACITY
    max_guests = serializers.IntegerField()
    num_bedrooms = serializers.IntegerField()
    num_bathrooms = serializers.IntegerField()
    
    # PRICING (OPTIONAL - can be set per room)
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    gst_percentage = serializers.IntegerField(default=18)


# ======================== VIEWS ========================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@atomic
def register_property(request):
    """
    Owner registers new property (DRAFT status)
    
    POST /api/property-owners/register/
    {
        "name": "Ocean View Villa",
        "description": "Beautiful beachfront property",
        ...
    }
    
    Returns: Property object with DRAFT status
    """
    serializer = PropertyOwnerRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Get or create property owner profile
    try:
        owner_profile = PropertyOwner.objects.get(user=request.user)
    except PropertyOwner.DoesNotExist:
        return Response(
            {'error': 'Owner profile not found. Complete owner verification first.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    data = serializer.validated_data
    
    # Create property in DRAFT status
    property_obj = Property.objects.create(
        owner=owner_profile,
        name=data['name'],
        description=data['description'],
        property_type_id=data['property_type'],
        city_id=data['city'],
        address=data['address'],
        state=data.get('state', ''),
        pincode=data['pincode'],
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        contact_phone=data['contact_phone'],
        contact_email=data['contact_email'],
        checkin_time=data['checkin_time'],
        checkout_time=data['checkout_time'],
        property_rules=data['property_rules'],
        cancellation_policy=data['cancellation_policy'],
        cancellation_type=data['cancellation_type'],
        cancellation_days=data.get('cancellation_days'),
        refund_percentage=data['refund_percentage'],
        has_wifi=data['has_wifi'],
        has_parking=data['has_parking'],
        has_pool=data['has_pool'],
        has_gym=data['has_gym'],
        has_restaurant=data['has_restaurant'],
        has_spa=data['has_spa'],
        has_ac=data['has_ac'],
        amenities=data.get('amenities', ''),
        max_guests=data['max_guests'],
        num_bedrooms=data['num_bedrooms'],
        num_bathrooms=data['num_bathrooms'],
        base_price=data.get('base_price'),
        gst_percentage=data['gst_percentage'],
        status='DRAFT',
    )
    
    return Response(
        PropertySubmissionSerializer(property_obj).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@atomic
def add_room_type(request, property_id):
    """
    Owner adds room type to property
    
    POST /api/property-owners/properties/{property_id}/rooms/
    {
        "name": "Deluxe Suite",
        "base_price": 5000,
        "max_occupancy": 2,
        "number_of_beds": 1,
        "room_size": 250,
        "total_rooms": 3,
        "discount_type": "percentage",
        "discount_value": 10,
        "amenities": ["Balcony", "TV", "Minibar"],
        "meal_plans": [
            {"type": "room_only", "price": 5000},
            {"type": "breakfast", "price": 5500}
        ]
    }
    """
    try:
        prop = Property.objects.get(id=property_id, owner__user=request.user)
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Only owners can modify DRAFT/REJECTED properties
    if prop.status not in ['DRAFT', 'REJECTED']:
        return Response(
            {'error': f'Cannot modify property in {prop.get_status_display()} status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = RoomTypeInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Validate meal plans
    if not data.get('meal_plans') or len(data['meal_plans']) == 0:
        return Response(
            {'error': 'At least one meal plan required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create room type
    room = PropertyRoomType.objects.create(
        property=prop,
        name=data['name'],
        room_type=data['room_type'],
        description=data['description'],
        max_occupancy=data['max_occupancy'],
        number_of_beds=data['number_of_beds'],
        room_size=data['room_size'],
        base_price=Decimal(str(data['base_price'])),
        total_rooms=data['total_rooms'],
        discount_type=data.get('discount_type', 'none'),
        discount_value=Decimal(str(data.get('discount_value', 0))),
        discount_valid_from=data.get('discount_valid_from'),
        discount_valid_to=data.get('discount_valid_to'),
        discount_is_active=data.get('discount_is_active', False),
        amenities=data.get('amenities', []),
        meal_plans=data['meal_plans'],
    )
    
    return Response(
        PropertyRoomTypeSubmissionSerializer(room).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@atomic
def upload_room_images(request, property_id, room_id):
    """
    Owner uploads images for a room (minimum 3 required)
    
    POST /api/property-owners/properties/{property_id}/rooms/{room_id}/images/
    Content-Type: multipart/form-data
    {
        "images": [file1, file2, file3, ...]
    }
    """
    try:
        prop = Property.objects.get(id=property_id, owner__user=request.user)
        room = PropertyRoomType.objects.get(id=room_id, property=prop)
    except (Property.DoesNotExist, PropertyRoomType.DoesNotExist):
        return Response(
            {'error': 'Property or room not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if prop.status not in ['DRAFT', 'REJECTED']:
        return Response(
            {'error': 'Cannot modify property in this status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    files = request.FILES.getlist('images')
    if not files:
        return Response(
            {'error': 'No images provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    created_images = []
    for idx, file in enumerate(files):
        img = PropertyRoomImage.objects.create(
            room_type=room,
            image=file,
            is_primary=(idx == 0),  # First image as primary
            display_order=idx,
        )
        created_images.append(img)
    
    return Response(
        {
            'count': len(created_images),
            'images': PropertyRoomImageSerializer(created_images, many=True).data,
            'message': f'{len(created_images)} images uploaded'
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@atomic
def upload_property_images(request, property_id):
    """
    Owner uploads images for the property (used for gallery and primary image)
    
    POST /api/property-owners/properties/{property_id}/images/
    Content-Type: multipart/form-data
    {
        "images": [file1, file2, file3, ...]
    }
    """
    try:
        prop = Property.objects.get(id=property_id, owner__user=request.user)
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if prop.status not in ['DRAFT', 'REJECTED']:
        return Response(
            {'error': 'Cannot modify property in this status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    files = request.FILES.getlist('images')
    if not files:
        return Response(
            {'error': 'No images provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    created_images = []
    for idx, file in enumerate(files):
        pimg = PropertyImage.objects.create(
            property=prop,
            image=file,
            caption='',
            is_primary=(idx == 0),  # First image as primary
        )
        created_images.append(pimg)
    
    return Response(
        {
            'count': len(created_images),
            'images': PropertyImageSerializer(created_images, many=True).data,
            'message': f'{len(created_images)} property images uploaded'
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_property_for_approval(request, property_id):
    """
    Owner submits property for admin approval
    
    POST /api/property-owners/properties/{property_id}/submit-approval/
    
    Validates all required fields before allowing submission
    """
    try:
        prop = Property.objects.get(id=property_id, owner__user=request.user)
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if prop.status != 'DRAFT':
        return Response(
            {'error': f'Property is {prop.get_status_display()}, cannot resubmit'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate all required fields
    checks, is_complete = prop.has_required_fields()
    if not is_complete:
        return Response(
            {
                'error': 'Cannot submit - missing required fields',
                'missing_fields': checks,
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Submit for approval
    prop.submit_for_approval()
    
    return Response(
        {
            'message': 'Property submitted for admin approval',
            'property': PropertySubmissionSerializer(prop).data,
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_owner_properties(request):
    """
    Owner views all their properties (all statuses)
    
    GET /api/property-owners/my-properties/
    
    Shows DRAFT, PENDING, APPROVED, REJECTED
    """
    try:
        owner_profile = PropertyOwner.objects.get(user=request.user)
    except PropertyOwner.DoesNotExist:
        return Response(
            {'error': 'Owner profile not found'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    properties = Property.objects.filter(owner=owner_profile)
    
    return Response(
        PropertySubmissionSerializer(properties, many=True).data,
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_property_details(request, property_id):
    """
    Owner views property details (for editing/updating)
    
    GET /api/property-owners/properties/{property_id}/
    """
    try:
        prop = Property.objects.get(id=property_id, owner__user=request.user)
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return Response(
        PropertySubmissionSerializer(prop).data,
        status=status.HTTP_200_OK
    )


# ======================== ADMIN APPROVAL VIEWS ========================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_list_pending_approvals(request):
    """
    Admin views all properties pending approval
    
    GET /api/admin/property-approvals/pending/
    """
    if not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    pending = Property.objects.filter(status='PENDING')
    
    return Response(
        PropertySubmissionSerializer(pending, many=True).data,
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@atomic
def admin_approve_property(request, property_id):
    """
    Admin approves property (status: PENDING → APPROVED)
    
    POST /api/admin/properties/{property_id}/approve/
    {
        "approval_note": "Property meets all standards"
    }
    """
    if not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        prop = Property.objects.get(id=property_id, status='PENDING')
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found or not pending'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Approve and sync to Hotel model
    prop.approve(request.user)
    
    return Response(
        {
            'message': 'Property approved successfully',
            'property': PropertySubmissionSerializer(prop).data,
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_reject_property(request, property_id):
    """
    Admin rejects property (status: PENDING → REJECTED)
    
    POST /api/admin/properties/{property_id}/reject/
    {
        "rejection_reason": "Missing required images"
    }
    """
    if not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        prop = Property.objects.get(id=property_id, status='PENDING')
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found or not pending'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    reason = request.data.get('rejection_reason', '')
    if not reason.strip():
        return Response(
            {'error': 'Rejection reason required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    prop.reject(reason)
    
    return Response(
        {
            'message': 'Property rejected',
            'property': PropertySubmissionSerializer(prop).data,
        },
        status=status.HTTP_200_OK
    )
