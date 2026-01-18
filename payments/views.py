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
    Confirm a booking using wallet funds only.

    Requirements implemented:
    - Validate balance >= payable
    - Deduct wallet (and cashback) atomically
    - Create wallet transaction + payment record
    - Update booking status -> confirmed (idempotent)
    - Lock inventory via finalize_booking_after_payment
    - Idempotent: if already confirmed/paid, no double charge
    - If any step fails, rollback the entire transaction
    """
    from bookings.models import Booking
    from .models import Payment, Wallet, WalletTransaction, CashbackLedger
    from django.utils import timezone
    from django.db import transaction
    from django.urls import reverse

    booking_id = request.data.get('booking_id')
    try:
        amount_requested = Decimal(str(request.data.get('amount', 0)))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid amount'}, status=400)

    # Validate booking belongs to user
    try:
        booking = Booking.objects.get(booking_id=booking_id, user=request.user)
    except Booking.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Booking not found'}, status=404)

    # Idempotency and disallow paying cancelled/expired
    payable = booking.total_amount - booking.paid_amount
    if payable <= 0 or booking.status in ['confirmed', 'completed', 'refunded', 'cancelled', 'expired']:
        redirect_url = reverse('bookings:booking-confirm', kwargs={'booking_id': booking.booking_id})
        return JsonResponse({
            'status': 'success',
            'message': 'Booking already confirmed',
            'redirect_url': redirect_url,
            'booking_status': booking.status,
        })

    # Enforce that frontend-provided amount matches server-side payable
    amount = payable
    if amount_requested and amount_requested != payable:
        # Optional: allow equal within rounding
        if abs(amount_requested - payable) > Decimal('0.01'):
            return JsonResponse({'status': 'error', 'message': 'Amount mismatch'}, status=400)

    # Validate wallet
    wallet = Wallet.objects.filter(user=request.user, is_active=True).first()
    if not wallet:
        return JsonResponse({'status': 'error', 'message': 'Wallet not found'}, status=404)

    # Check balance + cashback availability (non-mutating)
    total_available = wallet.get_available_balance()
    if total_available < amount:
        return JsonResponse({
            'status': 'error',
            'message': f'Insufficient balance. Available: ₹{total_available}, Required: ₹{amount}'
        }, status=400)

    # Perform atomic debit + booking confirm
    try:
        with transaction.atomic():
            # Lock rows
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            booking = Booking.objects.select_for_update().get(pk=booking.pk)

            # Recompute payable inside lock to avoid race
            payable_locked = booking.total_amount - booking.paid_amount
            if payable_locked <= 0 or booking.status in ['confirmed', 'completed', 'refunded', 'cancelled', 'expired']:
                redirect_url = reverse('bookings:booking-confirm', kwargs={'booking_id': booking.booking_id})
                return JsonResponse({
                    'status': 'success',
                    'message': 'Booking already confirmed',
                    'redirect_url': redirect_url,
                    'booking_status': booking.status,
                })

            # Validate funds again with locked balances
            total_available_locked = wallet.get_available_balance()
            if total_available_locked < payable_locked:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Insufficient balance. Available: ₹{total_available_locked}, Required: ₹{payable_locked}'
                }, status=400)

            # Deduct from wallet balance first
            wallet_txn = None
            wallet_balance_before = wallet.balance
            wallet_deduction = min(wallet.balance, payable_locked)
            cashback_needed = payable_locked - wallet_deduction

            if wallet_deduction > 0:
                # Idempotency: Check if wallet transaction already exists
                existing_txn = WalletTransaction.objects.filter(
                    booking=booking,
                    transaction_type='debit',
                    reference_id=str(booking.booking_id),
                    status='success'
                ).first()
                
                if existing_txn:
                    # Already debited, use existing transaction
                    wallet_txn = existing_txn
                else:
                    previous_balance = wallet.balance
                    wallet.balance -= wallet_deduction
                    wallet.save(update_fields=['balance', 'updated_at'])
                    wallet_txn = WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='debit',
                        amount=wallet_deduction,
                        balance_before=previous_balance,
                        balance_after=wallet.balance,
                        reference_id=str(booking.booking_id),
                        description=f"Wallet payment for booking {booking.booking_id}",
                        booking=booking,
                        status='success',
                        payment_gateway='internal',
                    )

            # Use cashback ledger FIFO for remainder
            cashback_used = Decimal('0')
            if cashback_needed > 0:
                cashback_entries = CashbackLedger.objects.select_for_update().filter(
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

                if remaining > 0:
                    raise ValueError("Cashback balance changed during processing")

            # Create payment record (idempotent per booking via transaction_id)
            payment = Payment.objects.create(
                booking=booking,
                amount=payable_locked,
                payment_method='wallet',
                status='success',
                transaction_date=timezone.now(),
                transaction_id=f"WALLET-{booking.booking_id}",
                gateway_response={
                    'wallet_amount': float(wallet_deduction),
                    'cashback_amount': float(cashback_used)
                }
            )

            # Update booking
            now = timezone.now()
            booking.paid_amount += payable_locked
            booking.payment_reference = payment.transaction_id
            booking.status = 'confirmed'
            booking.confirmed_at = now
            booking.wallet_balance_before = wallet_balance_before
            booking.wallet_balance_after = wallet.balance
            booking.save(update_fields=[
                'paid_amount', 'payment_reference', 'status', 'confirmed_at',
                'wallet_balance_before', 'wallet_balance_after', 'updated_at'
            ])

            # Lock inventory permanently
            finalize_booking_after_payment(booking, payment_reference=payment.transaction_id)

            redirect_url = reverse('bookings:booking-confirm', kwargs={'booking_id': booking.booking_id})
            return JsonResponse({
                'status': 'success',
                'message': 'Payment successful - booking confirmed',
                'payment_id': str(payment.id),
                'booking_id': str(booking.booking_id),
                'booking_status': 'confirmed',
                'redirect_url': redirect_url,
            })

    except Exception as exc:
        # Rollback is automatic. Mark booking as payment_failed and release lock defensively.
        from hotels.channel_manager_service import release_inventory_on_failure
        booking.status = 'payment_failed'
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=['status', 'cancelled_at', 'updated_at'])
        release_inventory_on_failure(booking)

        # Attempt to record a refund for any wallet txn if created (best-effort)
        try:
            if 'wallet_txn' in locals() and wallet_txn:
                wallet_txn.create_refund(reason=f"Payment failed: {str(exc)}")
        except Exception:
            pass

        return JsonResponse({
            'status': 'error',
            'message': f'Payment processing failed: {str(exc)}',
            'booking_status': 'payment_failed'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def add_money(request):
    """Initiate wallet top-up via Cashfree payment gateway."""
    from django.utils import timezone
    from django.urls import reverse
    from django.db import transaction
    from .models import WalletTransaction, Wallet

    amount_raw = request.POST.get('amount', '0').strip()
    notes = request.POST.get('notes', '').strip() or 'Wallet top-up'

    try:
        amount = Decimal(amount_raw)
    except Exception:
        messages.error(request, "Please enter a valid amount.")
        return redirect('payments:wallet')

    if amount <= 0:
        messages.error(request, "Amount must be greater than zero.")
        return redirect('payments:wallet')

    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={'balance': Decimal('0.00')})

    # Generate unique order ID for wallet top-up
    order_id = f"WALLET-{request.user.id}-{int(timezone.now().timestamp())}"

    # Create a pending wallet transaction (idempotent by reference_id)
    with transaction.atomic():
        txn, created = WalletTransaction.objects.get_or_create(
            wallet=wallet,
            reference_id=order_id,
            defaults={
                'transaction_type': 'credit',
                'amount': amount,
                'balance_before': wallet.balance,
                'balance_after': wallet.balance,
                'description': notes,
                'status': 'pending',
                'payment_gateway': 'cashfree',
            }
        )
        if not created:
            txn.amount = amount
            txn.description = notes
            txn.status = 'pending'
            txn.payment_gateway = 'cashfree'
            txn.save(update_fields=['amount', 'description', 'status', 'payment_gateway', 'updated_at'])

    # Store pending wallet transaction in session (NOT credited yet)
    request.session['pending_wallet_topup'] = {
        'amount': float(amount),
        'order_id': order_id,
        'notes': notes,
        'created_at': str(timezone.now())
    }
    request.session.modified = True
    
    # Redirect to Cashfree payment checkout using URL reverse
    checkout_url = reverse('payments:cashfree-checkout') + f'?order_id={order_id}&amount={amount}'
    return redirect(checkout_url)


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
    from django.db import transaction
    order_id = request.GET.get('order_id')
    pending = request.session.get('pending_wallet_topup', {})

    if not pending or pending.get('order_id') != order_id:
        messages.error(request, 'Invalid payment session')
        return redirect('payments:wallet')

    amount = Decimal(str(pending['amount']))
    notes = pending.get('notes', 'Wallet top-up')

    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={'balance': Decimal('0.00')})

    # Idempotent credit inside atomic block
    with transaction.atomic():
        txn = WalletTransaction.objects.select_for_update().filter(
            wallet=wallet,
            reference_id=order_id,
            transaction_type='credit'
        ).first()

        if not txn:
            messages.error(request, 'Transaction not found')
            return redirect('payments:wallet')

        if txn.status == 'success':
            messages.info(request, 'Payment already processed')
            return redirect('payments:wallet')

        balance_before = wallet.balance
        wallet.balance += amount
        wallet.save(update_fields=['balance', 'updated_at'])

        txn.status = 'success'
        txn.balance_before = balance_before
        txn.balance_after = wallet.balance
        txn.description = f'{notes} (via Cashfree)'
        txn.payment_gateway = 'cashfree'
        txn.save(update_fields=['status', 'balance_before', 'balance_after', 'description', 'payment_gateway', 'updated_at'])

    # Clear pending transaction
    if 'pending_wallet_topup' in request.session:
        del request.session['pending_wallet_topup']
        request.session.modified = True

    messages.success(request, f'₹{amount} added to your wallet successfully.')
    return redirect('payments:wallet')


@csrf_exempt
@require_http_methods(["POST"])
def cashfree_webhook(request):
    """Webhook to credit wallet after Cashfree success (idempotent)."""
    from django.db import transaction
    from django.utils import timezone

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid payload'}, status=400)

    order_id = payload.get('order_id') or payload.get('cf_order_id')
    amount = payload.get('order_amount') or payload.get('amount')
    user_id = payload.get('customer_details', {}).get('user_id') or payload.get('user_id')

    if not order_id or not amount or not user_id:
        return JsonResponse({'status': 'error', 'message': 'Missing fields'}, status=400)

    try:
        amount_dec = Decimal(str(amount))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid amount'}, status=400)

    # Resolve wallet
    wallet = Wallet.objects.filter(user_id=user_id).first()
    if not wallet:
        return JsonResponse({'status': 'error', 'message': 'Wallet not found'}, status=404)

    with transaction.atomic():
        txn = WalletTransaction.objects.select_for_update().filter(
            wallet=wallet,
            reference_id=order_id,
            transaction_type='credit'
        ).first()

        if txn and txn.status == 'success':
            return JsonResponse({'status': 'ok', 'message': 'Already processed'})

        if not txn:
            txn = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='credit',
                amount=amount_dec,
                balance_before=wallet.balance,
                balance_after=wallet.balance,
                description='Wallet top-up (Cashfree webhook)',
                status='pending',
                payment_gateway='cashfree',
                reference_id=order_id,
                gateway_order_id=order_id,
            )

        balance_before = wallet.balance
        wallet.balance += amount_dec
        wallet.save(update_fields=['balance', 'updated_at'])

        txn.status = 'success'
        txn.balance_before = balance_before
        txn.balance_after = wallet.balance
        txn.payment_gateway = 'cashfree'
        txn.save(update_fields=['status', 'balance_before', 'balance_after', 'payment_gateway', 'updated_at'])

    return JsonResponse({'status': 'ok'})


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
