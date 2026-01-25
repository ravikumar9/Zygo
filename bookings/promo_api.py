"""Promo code validation API endpoints"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from decimal import Decimal
from .promo_models import PromoCode


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_promo_code(request):
    """
    POST /api/bookings/validate-promo/
    
    Request body:
    {
        "code": "SUMMER20",
        "base_amount": 5000
    }
    
    Response:
    {
        "valid": true,
        "discount_amount": 1000,
        "discount_type": "PERCENTAGE",
        "discount_value": 20,
        "message": "Promo code applied successfully"
    }
    """
    code = request.data.get('code', '').strip().upper()
    base_amount = request.data.get('base_amount')
    
    if not code:
        return Response({
            'valid': False,
            'error': 'Promo code is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Handle None or empty values
        if base_amount is None:
            return Response({
                'valid': False,
                'error': 'Invalid booking amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert to Decimal, handling floats and strings
        if isinstance(base_amount, (int, float)):
            base_amount = Decimal(str(base_amount))
        else:
            base_amount = Decimal(base_amount)
        
        if base_amount <= 0:
            return Response({
                'valid': False,
                'error': 'Invalid booking amount'
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError, KeyError) as e:
        return Response({
            'valid': False,
            'error': f'Invalid booking amount: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'valid': False,
            'error': f'Decimal conversion error: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        promo = PromoCode.objects.get(code=code)
    except PromoCode.DoesNotExist:
        return Response({
            'valid': False,
            'error': 'Invalid promo code'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if not promo.is_valid():
        return Response({
            'valid': False,
            'error': 'Promo code has expired or reached usage limit'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not promo.can_apply_to_amount(base_amount):
        return Response({
            'valid': False,
            'error': f'Minimum booking amount is ₹{promo.min_booking_amount}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    discount = promo.calculate_discount(base_amount)
    
    return Response({
        'valid': True,
        'code': promo.code,
        'discount_amount': float(discount),
        'discount_type': promo.discount_type,
        'discount_value': float(promo.discount_value),
        'message': 'Promo code applied successfully',
        'description': promo.description
    }, status=status.HTTP_200_OK)
