"""
Hotel Booking API - CORRECTED per locked spec
Room + Meal Plan selection with dynamic pricing
Service fee: 5% capped ₹500 (NO percentages shown)
Inventory alerts
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.serializers import ModelSerializer, Serializer, DecimalField, IntegerField, CharField, BooleanField
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from datetime import date, datetime, timedelta

from hotels.models import Hotel, RoomType, MealPlan, RoomMealPlan
from bookings.models import Booking
from bookings.inventory_utils import reserve_inventory
from core.models import PromoCode
from payments.models import Payment, Wallet, WalletTransaction


# ======================== PRICING SERVICE ========================

class PricingService:
    """
    LOCKED SPEC: Service fee 5% capped ₹500
    - Room only base price
    - Meal plan delta (Room + Breakfast, Room + Breakfast + Lunch/Dinner, Room + All Meals)
    - Service charge: 5% of subtotal, MAX ₹500
    - NO GST slabs
    - NO percentages shown in UI
    - Fees visible ONLY behind ℹ icon (in booking details response)
    """
    
    SERVICE_FEE_PERCENT = Decimal('5.00')
    SERVICE_FEE_CAP = Decimal('500.00')
    
    @staticmethod
    def calculate_service_fee(subtotal):
        """Calculate service fee: 5% capped at ₹500"""
        fee = (subtotal * PricingService.SERVICE_FEE_PERCENT) / Decimal('100')
        return min(fee, PricingService.SERVICE_FEE_CAP).quantize(Decimal('0.01'))
    
    @staticmethod
    def calculate_booking_price(room_type, meal_plan, num_nights, num_rooms=1):
        """
        Calculate complete pricing for booking
        
        LOCKED SPEC:
        - room_price_per_night: shown to user
        - meal_plan_delta: shown to user
        - subtotal_per_night: shown to user
        - service_fee: HIDDEN (only in ℹ details)
        - total_amount: shown to user (room + meal + service fee)
        - inventory_warning: shown if <5 rooms
        
        Returns dict with all values
        """
        
        # Room pricing
        room_price = Decimal(str(room_type.base_price))
        
        # Meal plan delta
        meal_delta = Decimal('0.00')
        if meal_plan:
            meal_delta = Decimal(str(meal_plan.price_delta))
        
        # Per-night total
        subtotal_per_night = room_price + meal_delta
        total_before_fee = subtotal_per_night * num_nights * num_rooms
        
        # Service fee (5% capped ₹500)
        service_fee = PricingService.calculate_service_fee(total_before_fee)
        
        # Total
        total_amount = total_before_fee + service_fee
        
        # Inventory warning
        inventory_warning = None
        available = room_type.inventory_count
        if available < 5:
            inventory_warning = f'Only {available} rooms left at this price'
        
        return {
            'room_price_per_night': room_price,
            'meal_plan_delta': meal_delta,
            'subtotal_per_night': subtotal_per_night,
            'total_nights': num_nights,
            'num_rooms': num_rooms,
            'total_before_fee': total_before_fee,
            'service_fee': service_fee,
            'total_amount': total_amount.quantize(Decimal('0.01')),
            'inventory_warning': inventory_warning,
            'service_fee_percent': '5%',  # For ℹ icon only
            'service_fee_cap': '₹500',    # For ℹ icon only
        }


# ======================== SERIALIZERS ========================

class PricingBreakdownSerializer(Serializer):
    """
    Sticky price shown to user
    LOCKED: NO percentages, NO GST, NO slab shown
    Fees only in ℹ details
    """
    room_price_per_night = DecimalField(max_digits=10, decimal_places=2)
    meal_plan_delta = DecimalField(max_digits=10, decimal_places=2)
    subtotal_per_night = DecimalField(max_digits=10, decimal_places=2)
    total_nights = IntegerField()
    num_rooms = IntegerField()
    total_before_fee = DecimalField(max_digits=10, decimal_places=2)
    # NOTE: service_fee NOT included in public serializer
    total_amount = DecimalField(max_digits=10, decimal_places=2)
    inventory_warning = None


class PricingDetailsSerializer(Serializer):
    """
    Fees breakdown - ONLY visible behind ℹ icon
    """
    total_before_fee = DecimalField(max_digits=10, decimal_places=2)
    service_fee = DecimalField(max_digits=10, decimal_places=2)
    service_fee_percent = CharField()  # "5%"
    service_fee_cap = CharField()      # "₹500"
    total_amount = DecimalField(max_digits=10, decimal_places=2)


class BookingRequestSerializer(Serializer):
    """Create booking request"""
    room_type_id = IntegerField()
    meal_plan_id = IntegerField(required=False, allow_null=True)
    check_in_date = CharField()  # YYYY-MM-DD
    check_out_date = CharField()  # YYYY-MM-DD
    num_rooms = IntegerField(default=1)
    customer_name = CharField(max_length=100)
    customer_email = CharField(max_length=100)
    customer_phone = CharField(max_length=20)
    special_requests = CharField(required=False, allow_blank=True)
    use_wallet = BooleanField(default=False)
    wallet_amount = DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    payment_method = CharField(required=False, allow_blank=True)  # 'upi', 'card', 'wallet'


class BookingConfirmationSerializer(Serializer):
    """Booking confirmation response"""
    booking_id = CharField()
    status = CharField()  # 'reserved'
    check_in_date = CharField()
    check_out_date = CharField()
    room_type = CharField()
    meal_plan = CharField()
    pricing = PricingBreakdownSerializer()
    # NO expires_at - no hold timer per locked spec



# ======================== VIEWS ========================

@api_view(['POST'])
@permission_classes([AllowAny])
@atomic
def create_hotel_booking(request):
    """
    Create hotel booking (step 1: reservation)
    POST /api/bookings/hotel/
    
    LOCKED SPEC:
    - NO 30-minute hold timer
    - Wallet checkbox support (partial payment)
    - Returns booking with pricing (service fee hidden)
    """
    serializer = BookingRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Get room type
    try:
        room_type = RoomType.objects.get(id=data['room_type_id'])
    except RoomType.DoesNotExist:
        return Response({'error': 'Room type not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get meal plan (optional)
    meal_plan = None
    if 'meal_plan_id' in data and data['meal_plan_id']:
        try:
            meal_plan = RoomMealPlan.objects.get(id=data['meal_plan_id'], room_type=room_type)
            meal_plan_obj = meal_plan.meal_plan
        except RoomMealPlan.DoesNotExist:
            return Response({'error': 'Meal plan not valid for this room'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        # Use room-only meal plan
        meal_plan_obj = None
    
    # Parse dates
    try:
        check_in = datetime.strptime(data['check_in_date'], '%Y-%m-%d').date()
        check_out = datetime.strptime(data['check_out_date'], '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format (use YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
    
    if check_out <= check_in:
        return Response({'error': 'Check-out must be after check-in'}, status=status.HTTP_400_BAD_REQUEST)
    
    num_nights = (check_out - check_in).days
    num_rooms = data.get('num_rooms', 1)
    
    # Calculate pricing
    pricing = PricingService.calculate_booking_price(
        room_type, meal_plan_obj, num_nights, num_rooms
    )
    
    # Check and reserve inventory for each night in the stay
    try:
        reserve_inventory(room_type, check_in, check_out, num_rooms)
    except ValueError as inv_err:
        return Response({'error': str(inv_err)}, status=status.HTTP_400_BAD_REQUEST)
    
    # Wallet handling (if specified)
    wallet_used = Decimal('0.00')
    remaining_to_pay = pricing['total_amount']
    payment_method = data.get('payment_method', 'card')
    
    if data.get('use_wallet') and data.get('wallet_amount'):
        wallet_used = Decimal(str(data['wallet_amount']))
        if wallet_used > pricing['total_amount']:
            wallet_used = pricing['total_amount']
        remaining_to_pay = pricing['total_amount'] - wallet_used
    
    # Create booking (NO expires_at for hold timer per locked spec)
    booking = Booking.objects.create(
        booking_type='hotel',
        status='reserved',
        reserved_at=timezone.now(),
        # NO expires_at - no timer per locked spec
        customer_name=data['customer_name'],
        customer_email=data['customer_email'],
        customer_phone=data['customer_phone'],
        total_amount=pricing['total_amount'],
        special_requests=data.get('special_requests', ''),
        user=request.user if request.user.is_authenticated else None,
    )
    
    # Store pricing snapshot (service fee included for backend reference)
    booking.pricing_data = pricing
    booking.save()
    
    # Store hotel booking details
    from bookings.models import HotelBooking
    HotelBooking.objects.create(
        booking=booking,
        room_type=room_type,
        meal_plan=meal_plan.meal_plan if meal_plan else None,
        check_in=check_in,
        check_out=check_out,
        number_of_rooms=num_rooms,
        total_nights=num_nights,
        room_snapshot={
            'room_type': room_type.name,
            'base_price': str(room_type.base_price),
            'meal_plan': meal_plan_obj.name if meal_plan_obj else 'Room Only',
        },
        price_snapshot={
            'room_price_per_night': str(pricing['room_price_per_night']),
            'meal_plan_delta': str(pricing['meal_plan_delta']),
            'subtotal_per_night': str(pricing['subtotal_per_night']),
            'total_before_fee': str(pricing['total_before_fee']),
            'service_fee': str(pricing['service_fee']),
            'total_amount': str(pricing['total_amount']),
        },
    )
    
    # Return response WITHOUT service_fee shown to user
    response_pricing = {
        'room_price_per_night': str(pricing['room_price_per_night']),
        'meal_plan_delta': str(pricing['meal_plan_delta']),
        'subtotal_per_night': str(pricing['subtotal_per_night']),
        'total_nights': pricing['total_nights'],
        'num_rooms': pricing['num_rooms'],
        'total_amount': str(pricing['total_amount']),
        'inventory_warning': pricing['inventory_warning'],
    }
    
    return Response({
        'booking_id': str(booking.booking_id),
        'status': 'reserved',
        'check_in_date': check_in.isoformat(),
        'check_out_date': check_out.isoformat(),
        'room_type': room_type.name,
        'meal_plan': meal_plan_obj.name if meal_plan_obj else 'Room Only',
        'num_rooms': num_rooms,
        'pricing': response_pricing,
        # NO expires_at
        'wallet_used': str(wallet_used),
        'remaining_to_pay': str(remaining_to_pay),
        'payment_method': payment_method,
        'message': 'Booking created. Complete payment to confirm.'
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_booking_details(request, booking_id):
    """
    Get booking details & pricing breakdown
    GET /api/bookings/{booking_id}/
    
    Returns: pricing with service fee visible (for confirmation)
    """
    try:
        booking = Booking.objects.get(booking_id=booking_id)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    pricing_data = booking.pricing_data if hasattr(booking, 'pricing_data') else {}
    
    return Response({
        'booking_id': str(booking.booking_id),
        'status': booking.status,
        'total_amount': str(booking.total_amount),
        'pricing_breakdown': {
            'room_price_per_night': pricing_data.get('room_price_per_night'),
            'meal_plan_delta': pricing_data.get('meal_plan_delta'),
            'subtotal_per_night': pricing_data.get('subtotal_per_night'),
            'total_before_fee': pricing_data.get('total_before_fee'),
            'service_fee': pricing_data.get('service_fee'),
            'service_fee_info': f"5% of subtotal, capped at ₹500",
            'total_amount': pricing_data.get('total_amount'),
        },
        'customer_name': booking.customer_name,
        'customer_email': booking.customer_email,
        'customer_phone': booking.customer_phone,
        'reserved_at': booking.reserved_at.isoformat() if booking.reserved_at else None,
    })


@api_view(['GET'])
def list_available_rooms(request):
    """
    List available rooms for booking
    GET /api/rooms/available/?check_in=2026-02-15&check_out=2026-02-17
    
    Only shows APPROVED properties' rooms
    """
    try:
        check_in = datetime.strptime(request.query_params.get('check_in', ''), '%Y-%m-%d').date()
        check_out = datetime.strptime(request.query_params.get('check_out', ''), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return Response({'error': 'check_in and check_out required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
    
    if check_out <= check_in:
        return Response({'error': 'check_out must be after check_in'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Only approved properties
    rooms = RoomType.objects.filter(
        hotel__owner_property__status='APPROVED',
        hotel__owner_property__is_active=True,
        is_available=True
    ).select_related('hotel', 'meal_plans')
    
    results = []
    for room in rooms:
        meal_plans = room.meal_plans.filter(is_active=True).values(
            'id', 'meal_plan__name', 'price_delta'
        )
        
        results.append({
            'room_id': room.id,
            'room_name': room.name,
            'room_type': room.get_room_type_display(),
            'hotel': {
                'id': room.hotel.id,
                'name': room.hotel.name,
                'city': room.hotel.city.name,
                'rating': room.hotel.review_rating,
            },
            'base_price': str(room.base_price),
            'available_count': room.inventory_count,
            'meal_plans': list(meal_plans),
            'max_occupancy': room.max_occupancy,
            'room_size_sqft': room.room_size,
        })
    
    return Response(results)


@api_view(['GET'])
def get_pricing_breakdown(request, room_type_id):
    """
    Get pricing breakdown for a room type
    GET /api/rooms/{room_type_id}/pricing/?check_in=2026-02-15&check_out=2026-02-17&meal_plan_id=1&num_rooms=1
    
    LOCKED SPEC:
    - Shows room + meal + total
    - Service fee hidden (visible only in ℹ icon details)
    - Inventory alert if <5 rooms
    """
    try:
        room_type = RoomType.objects.get(id=room_type_id)
    except RoomType.DoesNotExist:
        return Response({'error': 'Room not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Parse params
    try:
        check_in = datetime.strptime(request.query_params.get('check_in', ''), '%Y-%m-%d').date()
        check_out = datetime.strptime(request.query_params.get('check_out', ''), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return Response({'error': 'check_in and check_out required'}, status=status.HTTP_400_BAD_REQUEST)
    
    num_nights = (check_out - check_in).days
    num_rooms = int(request.query_params.get('num_rooms', 1))
    
    # Get meal plan (optional)
    meal_plan_obj = None
    if 'meal_plan_id' in request.query_params:
        try:
            meal_plan_rmp = RoomMealPlan.objects.get(
                id=request.query_params['meal_plan_id'],
                room_type=room_type
            )
            meal_plan_obj = meal_plan_rmp.meal_plan
        except RoomMealPlan.DoesNotExist:
            return Response({'error': 'Meal plan not found'}, status=status.HTTP_404_NOT_FOUND)
    
    pricing = PricingService.calculate_booking_price(room_type, meal_plan_obj, num_nights, num_rooms)
    
    return Response({
        'room_type_id': room_type_id,
        'room_name': room_type.name,
        'check_in': check_in.isoformat(),
        'check_out': check_out.isoformat(),
        'num_nights': num_nights,
        'num_rooms': num_rooms,
        'pricing_summary': {
            'room_price_per_night': str(pricing['room_price_per_night']),
            'meal_plan_delta': str(pricing['meal_plan_delta']),
            'subtotal_per_night': str(pricing['subtotal_per_night']),
            'total_amount': str(pricing['total_amount']),
        },
        'pricing_details': {
            'total_before_fee': str(pricing['total_before_fee']),
            'service_fee': str(pricing['service_fee']),
            'service_fee_info': f"5% of subtotal, capped ₹500",
            'total_with_fee': str(pricing['total_amount']),
        },
        'inventory_warning': pricing['inventory_warning'],
    }, status=status.HTTP_200_OK)
    
    return Response(pricing)


@api_view(['POST'])
@permission_classes([AllowAny])
@atomic
def complete_booking_payment(request, booking_id):
    """
    Complete payment for a reserved booking.

    Supports optional wallet deduction (authenticated users) plus gateway/card/UPI
    for the remainder. Always marks booking confirmed on full payment.
    """
    try:
        booking = Booking.objects.select_for_update().get(booking_id=booking_id)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

    if booking.status == 'confirmed':
        return Response({
            'booking_id': str(booking.booking_id),
            'status': booking.status,
            'message': 'Booking already confirmed'
        }, status=status.HTTP_200_OK)

    total_due = (booking.total_amount - booking.paid_amount).quantize(Decimal('0.01'))
    if total_due <= 0:
        booking.status = 'confirmed'
        booking.confirmed_at = timezone.now()
        booking.save(update_fields=['status', 'confirmed_at', 'updated_at'])
        return Response({
            'booking_id': str(booking.booking_id),
            'status': booking.status,
            'message': 'No outstanding amount. Booking confirmed.'
        }, status=status.HTTP_200_OK)

    # Inputs
    wallet_requested = Decimal(str(request.data.get('wallet_amount', '0') or '0')).quantize(Decimal('0.01'))
    gateway_requested = request.data.get('gateway_amount')
    payment_method = request.data.get('payment_method', 'upi')

    wallet_used = Decimal('0.00')
    wallet_balance_before = None

    # Wallet deduction (only for authenticated users)
    if wallet_requested > 0:
        if not request.user or not request.user.is_authenticated:
            return Response({'error': 'Login required to use wallet balance'}, status=status.HTTP_401_UNAUTHORIZED)
        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=request.user,
            defaults={'balance': Decimal('0.00')}
        )
        wallet_balance_before = wallet.balance
        wallet_used = min(wallet_requested, wallet.balance, total_due)
        if wallet_used > 0:
            wallet.balance -= wallet_used
            wallet.save(update_fields=['balance', 'updated_at'])
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='debit',
                amount=wallet_used,
                balance_before=wallet_balance_before,
                balance_after=wallet.balance,
                description=f'Wallet payment for booking {booking.booking_id}',
                booking=booking,
                status='success',
                payment_gateway='internal',
            )

    remaining_due = (total_due - wallet_used).quantize(Decimal('0.01'))

    # Gateway portion
    if gateway_requested is not None:
        try:
            gateway_amount = Decimal(str(gateway_requested)).quantize(Decimal('0.01'))
        except Exception:
            return Response({'error': 'Invalid gateway_amount'}, status=status.HTTP_400_BAD_REQUEST)
        if gateway_amount < remaining_due:
            return Response({'error': 'Gateway amount insufficient to complete payment'}, status=status.HTTP_400_BAD_REQUEST)
        gateway_amount = remaining_due
    else:
        gateway_amount = remaining_due

    paid_total = wallet_used + gateway_amount

    # Record payment
    payment = Payment.objects.create(
        booking=booking,
        amount=paid_total,
        payment_method=payment_method if gateway_amount > 0 else 'wallet',
        status='success',
        transaction_date=timezone.now(),
        transaction_id=f'PAY-{booking.booking_id}',
        gateway_response={
            'wallet_amount': float(wallet_used),
            'gateway_amount': float(gateway_amount),
            'payment_split': 'partial' if wallet_used > 0 and gateway_amount > 0 else 'single',
        }
    )

    booking.paid_amount = (booking.paid_amount + paid_total).quantize(Decimal('0.01'))
    booking.status = 'confirmed'
    booking.confirmed_at = timezone.now()
    booking.payment_reference = payment.transaction_id
    booking.wallet_balance_before = wallet_balance_before
    booking.wallet_balance_after = wallet_balance_before - wallet_used if wallet_balance_before is not None else None
    booking.save(update_fields=[
        'paid_amount', 'status', 'confirmed_at', 'payment_reference',
        'wallet_balance_before', 'wallet_balance_after', 'updated_at'
    ])

    return Response({
        'booking_id': str(booking.booking_id),
        'status': 'confirmed',
        'wallet_used': str(wallet_used),
        'gateway_amount': str(gateway_amount),
        'total_paid': str(paid_total),
        'remaining_due': str(max(booking.total_amount - booking.paid_amount, Decimal('0.00'))),
        'message': 'Payment completed and booking confirmed.'
    }, status=status.HTTP_200_OK)
