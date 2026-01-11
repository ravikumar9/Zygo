from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import razorpay
import hmac
import hashlib
import json
from decimal import Decimal

from hotels.channel_manager_service import finalize_booking_after_payment, release_inventory_on_failure


class CreatePaymentOrderView(APIView):
    """Create Razorpay order"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from bookings.models import Booking
        from .models import Payment
        
        booking_id = request.data.get('booking_id')
        amount = request.data.get('amount')
        
        try:
            booking = Booking.objects.get(booking_id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Create Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Create order
        order_data = {
            'amount': int(float(amount) * 100),  # Amount in paise
            'currency': 'INR',
            'receipt': str(booking.booking_id),
            'notes': {
                'booking_id': str(booking.booking_id),
                'user_id': str(request.user.id)
            }
        }
        
        order = client.order.create(data=order_data)
        
        # Create payment record
        payment = Payment.objects.create(
            booking=booking,
            amount=amount,
            payment_method='razorpay',
            gateway_order_id=order['id']
        )
        
        return Response({
            'order_id': order['id'],
            'amount': amount,
            'currency': 'INR',
            'key': settings.RAZORPAY_KEY_ID
        })


class VerifyPaymentView(APIView):
    """Verify Razorpay payment"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .models import Payment
        
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        
        # Verify signature
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        try:
            payment = Payment.objects.get(gateway_order_id=razorpay_order_id)
            
            if generated_signature == razorpay_signature:
                payment.status = 'success'
                payment.gateway_payment_id = razorpay_payment_id
                payment.gateway_signature = razorpay_signature
                payment.save()
                
                # Update booking
                booking = payment.booking
                booking.paid_amount += payment.amount
                booking.payment_reference = razorpay_payment_id
                booking.save(update_fields=['paid_amount', 'payment_reference', 'updated_at'])

                if booking.paid_amount >= booking.total_amount:
                    finalize_booking_after_payment(booking, payment_reference=razorpay_payment_id)
                
                return Response({'status': 'success', 'message': 'Payment verified successfully'})
            else:
                payment.status = 'failed'
                payment.save()
                release_inventory_on_failure(payment.booking)
                return Response({'status': 'failed', 'message': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)


class RazorpayWebhookView(APIView):
    """Handle Razorpay webhooks"""
    permission_classes = []
    
    def post(self, request):
        # Handle webhook events
        event = request.data.get('event')
        
        # Process different event types
        if event == 'payment.captured':
            # Handle payment captured
            pass
        elif event == 'payment.failed':
            booking_id = request.data.get('payload', {}).get('payment', {}).get('entity', {}).get('notes', {}).get('booking_id')
            if booking_id:
                try:
                    from bookings.models import Booking
                    booking = Booking.objects.filter(booking_id=booking_id).first()
                    if booking:
                        release_inventory_on_failure(booking)
                except Exception:
                    pass
        elif event == 'refund.created':
            # Handle refund
            pass
        
        return Response({'status': 'ok'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_wallet_payment(request):
    """Process payment using wallet balance and cashback"""
    from bookings.models import Booking
    from .models import Payment, Wallet, CashbackLedger
    from django.utils import timezone
    from django.db import transaction
    
    try:
        data = json.loads(request.body)
        booking_id = data.get('booking_id')
        amount = Decimal(str(data.get('amount', 0)))
        
        # Validate booking
        try:
            booking = Booking.objects.get(booking_id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Booking not found'}, status=404)
        
        # Get wallet
        try:
            wallet = Wallet.objects.get(user=request.user, is_active=True)
        except Wallet.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Wallet not found'}, status=404)
        
        # Check available balance
        total_available = wallet.get_available_balance()
        if total_available < amount:
            return JsonResponse({
                'status': 'error',
                'message': f'Insufficient balance. Available: ₹{total_available}, Required: ₹{amount}'
            }, status=400)
        
        # Process payment with transaction atomicity
        with transaction.atomic():
            # Calculate how much to deduct from wallet balance vs cashback
            wallet_deduction = min(wallet.balance, amount)
            cashback_needed = amount - wallet_deduction
            
            # Deduct from wallet balance
            if wallet_deduction > 0:
                wallet.deduct_balance(wallet_deduction, f"Payment for booking {booking_id}")
            
            # Use cashback if needed
            if cashback_needed > 0:
                # Get available cashback entries (FIFO - oldest first)
                cashback_entries = CashbackLedger.objects.filter(
                    wallet=wallet,
                    is_used=False,
                    is_expired=False,
                    expires_at__gt=timezone.now()
                ).order_by('expires_at')
                
                remaining = cashback_needed
                for cb_entry in cashback_entries:
                    if remaining <= 0:
                        break
                    use_amount = min(cb_entry.amount, remaining)
                    cb_entry.mark_as_used(use_amount)
                    remaining -= use_amount
            
            # Create payment record
            payment = Payment.objects.create(
                booking=booking,
                amount=amount,
                payment_method='wallet',
                status='success',
                transaction_date=timezone.now(),
                transaction_id=f"WALLET-{booking_id}",
                notes=f"Wallet: ₹{wallet_deduction}, Cashback: ₹{cashback_needed}"
            )
            
            # Update booking
            booking.paid_amount += amount
            booking.payment_reference = payment.transaction_id
            booking.save(update_fields=['paid_amount', 'payment_reference', 'updated_at'])
            
            # Finalize booking if fully paid
            if booking.paid_amount >= booking.total_amount:
                finalize_booking_after_payment(booking, payment_reference=payment.transaction_id)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Payment successful',
                'payment_id': str(payment.id)
            })
    
    except Exception as exc:
        return JsonResponse({
            'status': 'error',
            'message': str(exc)
        }, status=500)
