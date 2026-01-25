"""Wallet API endpoints"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .wallet_models import UserWallet


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_balance(request):
    """
    GET /api/users/wallet/balance/
    
    Response:
    {
        "balance": 2500.00,
        "formatted": "₹2,500"
    }
    """
    user = request.user
    try:
        wallet = UserWallet.objects.get(user=user)
        balance = float(wallet.balance)
    except UserWallet.DoesNotExist:
        # Create wallet if doesn't exist
        wallet = UserWallet.objects.create(user=user, balance=0)
        balance = 0.0
    
    return Response({
        'balance': balance,
        'formatted': f'₹{balance:,.0f}'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_wallet_payment(request):
    """
    POST /api/users/wallet/check-payment/
    
    Request body:
    {
        "amount": 5000
    }
    
    Response:
    {
        "sufficient": true,
        "balance": 10000,
        "amount_required": 5000
    }
    """
    try:
        amount = float(request.data.get('amount', 0))
        
        try:
            wallet = UserWallet.objects.get(user=request.user)
            balance = float(wallet.balance)
        except UserWallet.DoesNotExist:
            wallet = UserWallet.objects.create(user=request.user, balance=0)
            balance = 0.0
        
        sufficient = balance >= amount
        
        return Response({
            'sufficient': sufficient,
            'balance': balance,
            'amount_required': amount,
            'message': 'Sufficient balance' if sufficient else f'Need ₹{amount - balance:,.0f} more'
        }, status=status.HTTP_200_OK)
    except (ValueError, TypeError):
        return Response({
            'error': 'Invalid amount'
        }, status=status.HTTP_400_BAD_REQUEST)
