from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
import razorpay
import hmac
import hashlib
import json
from decimal import Decimal

from hotels.channel_manager_service import finalize_booking_after_payment, release_inventory_on_failure
from .models import Wallet, WalletTransaction


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
    """
    Process payment using wallet balance and cashback.
    
    Uses atomic transaction to ensure wallet debit and booking confirmation
    either both succeed or both fail. If anything fails, entire transaction
    rolls back and wallet balance is restored.
    
    ISSUE #4 FIX: Use request.data instead of request.body to prevent
    "cannot access body after reading from request's data stream" error
    """
    from bookings.models import Booking
    from .models import Payment, Wallet, WalletTransaction, CashbackLedger
    from django.utils import timezone
    from django.db import transaction
    
    try:
        # ISSUE #4 FIX: Use request.data (DRF-parsed) instead of request.body (raw stream)
        # This prevents "cannot access body after reading from request's data stream" error
        booking_id = request.data.get('booking_id')
        amount = Decimal(str(request.data.get('amount', 0)))
        
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
        
        # ATOMIC TRANSACTION: Either both wallet and booking update, or neither
        try:
            with transaction.atomic():
                # Lock rows to prevent race conditions
                wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
                booking = Booking.objects.select_for_update().get(pk=booking.pk)
                
                # Calculate how much to deduct from wallet balance vs cashback
                wallet_deduction = min(wallet.balance, amount)
                cashback_needed = amount - wallet_deduction
                
                # Step 1: Deduct from wallet balance
                wallet_txn = None
                wallet_balance_before = wallet.balance
                if wallet_deduction > 0:
                    previous_balance = wallet.balance
                    wallet.balance -= wallet_deduction
                    wallet.save(update_fields=['balance', 'updated_at'])
                    
                    # Record transaction
                    wallet_txn = WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='debit',
                        amount=wallet_deduction,
                        balance_before=previous_balance,
                        balance_after=wallet.balance,
                        reference_id=str(booking.booking_id),
                        description=f"Wallet payment for booking {booking_id}",
                        booking=booking,
                        status='success',
                        payment_gateway='internal',
                    )
                
                # Step 2: Use cashback if needed
                cashback_used = Decimal('0')
                if cashback_needed > 0:
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
                        cashback_used += use_amount
                        remaining -= use_amount
                
                # Step 3: Create payment record
                payment = Payment.objects.create(
                    booking=booking,
                    amount=amount,
                    payment_method='wallet',
                    status='success',
                    transaction_date=timezone.now(),
                    transaction_id=f"WALLET-{booking_id}",
                    gateway_response={
                        'wallet_amount': float(wallet_deduction),
                        'cashback_amount': float(cashback_used)
                    }
                )
                
                # Step 4: Update booking with wallet traceability (THIS MUST SUCCEED OR ROLLBACK ENTIRE TX)
                now = timezone.now()
                booking.paid_amount += amount
                booking.payment_reference = payment.transaction_id
                booking.status = 'confirmed'  # ← CRITICAL: Move from RESERVED to CONFIRMED
                booking.confirmed_at = now
                booking.wallet_balance_before = wallet_balance_before
                booking.wallet_balance_after = wallet.balance
                booking.save(update_fields=[
                    'paid_amount', 'payment_reference', 'status', 'confirmed_at', 
                    'wallet_balance_before', 'wallet_balance_after', 'updated_at'
                ])
                
                # Step 5: Finalize booking (lock inventory)
                from hotels.channel_manager_service import finalize_booking_after_payment
                finalize_booking_after_payment(booking, payment_reference=payment.transaction_id)
                
                # SUCCESS: All steps completed, transaction commits
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment successful - booking confirmed',
                    'payment_id': str(payment.id),
                    'booking_id': str(booking.booking_id),
                    'booking_status': 'confirmed'
                })
        
        except Exception as payment_error:
            # AUTOMATIC ROLLBACK: All DB changes reverted
            # wallet.balance is restored
            # booking.status stays RESERVED
            # Transaction is rolled back
            
            booking.status = 'payment_failed'
            booking.cancelled_at = timezone.now()
            booking.save(update_fields=['status', 'cancelled_at', 'updated_at'])
            
            # Create refund record for audit trail (OUTSIDE atomic block)
            # This shows admin what failed and was rolled back
            if wallet_txn:
                wallet_txn.create_refund(reason=f"Payment failed: {str(payment_error)}")
            
            return JsonResponse({
                'status': 'error',
                'message': f'Payment processing failed: {str(payment_error)}',
                'booking_status': 'payment_failed'
            }, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    except Exception as exc:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(exc)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def add_money(request):
    """Initiate wallet top-up via Cashfree payment gateway."""
    from django.utils import timezone
    amount_raw = request.POST.get('amount', '0').strip()
    notes = request.POST.get('notes', '').strip()

    try:
        amount = Decimal(amount_raw)
    except Exception:
        messages.error(request, "Please enter a valid amount.")
        return redirect('payments:wallet')

    if amount <= 0:
        messages.error(request, "Amount must be greater than zero.")
        return redirect('payments:wallet')

    # Generate unique order ID for wallet top-up
    order_id = f"WALLET-{request.user.id}-{int(timezone.now().timestamp())}"
    
    # Store pending wallet transaction in session (NOT credited yet)
    request.session['pending_wallet_topup'] = {
        'amount': float(amount),
        'order_id': order_id,
        'notes': notes,
        'created_at': str(timezone.now())
    }
    request.session.modified = True
    
    # Redirect to Cashfree payment checkout
    return redirect(f'/payments/cashfree-checkout/?order_id={order_id}&amount={amount}')


@login_required
def cashfree_checkout(request):
    """Cashfree checkout page for DEV/Sandbox."""
    from django.utils import timezone
    order_id = request.GET.get('order_id')
    amount = request.GET.get('amount', '0')
    
    pending = request.session.get('pending_wallet_topup', {})
    if not pending or pending.get('order_id') != order_id:
        messages.error(request, 'Invalid payment session')
        return redirect('payments:wallet')
    
    return render(request, 'payments/cashfree_checkout.html', {
        'order_id': order_id,
        'amount': amount,
        'user': request.user,
    })


@login_required
def cashfree_success(request):
    """Handle Cashfree payment success callback."""
    from django.utils import timezone
    order_id = request.GET.get('order_id')
    pending = request.session.get('pending_wallet_topup', {})
    
    if not pending or pending.get('order_id') != order_id:
        messages.error(request, 'Invalid payment session')
        return redirect('payments:wallet')
    
    amount = Decimal(str(pending['amount']))
    notes = pending.get('notes', 'Wallet top-up')
    
    # Credit wallet ONLY after payment success
    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={'balance': Decimal('0.00')})
    wallet.add_balance(amount, description=notes)
    
    # Log transaction
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type='credit',
        amount=amount,
        description=f'{notes} (via Cashfree)',
        status='success',
        reference_id=order_id,
    )
    
    # Clear pending transaction
    if 'pending_wallet_topup' in request.session:
        del request.session['pending_wallet_topup']
        request.session.modified = True
    
    messages.success(request, f'₹{amount} added to your wallet successfully.')
    return redirect('payments:wallet')


class WalletView(TemplateView):
    """Wallet page - shows balance and transaction history"""
    template_name = 'payments/wallet.html'
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')

        # Clear login/auth messages before displaying wallet page
        from django.contrib.messages import get_messages
        storage = get_messages(request)
        storage.used = True

        # Get or create wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={'balance': Decimal('0.00')})

        # Recent wallet transactions
        transactions = wallet.transactions.select_related('booking').order_by('-created_at')[:20]

        context = {
            'wallet': wallet,
            'transactions': transactions,
            'balance': float(wallet.balance),
            'total_cashback': float(wallet.cashback_earned),
        }

        return render(request, self.template_name, context)
