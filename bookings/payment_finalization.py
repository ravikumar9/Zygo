"""
Unified Booking Payment Finalization
=====================================

SINGLE SOURCE OF TRUTH for all payment flows:
- Wallet-only payment
- Wallet + Gateway payment
- Gateway-only payment
- Admin manual confirmation
- Retry scenarios

All flows must use finalize_booking_payment() atomically.
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def finalize_booking_payment(
    booking,
    payment_mode,  # 'wallet' | 'gateway' | 'admin'
    wallet_applied=Decimal('0.00'),
    gateway_amount=Decimal('0.00'),
    gateway_transaction_id=None,
    user=None
):
    """
    UNIFIED payment finalization logic - SINGLE ENTRY POINT for all payment flows.
    
    ALL payment flows (wallet, gateway, admin) MUST use this function.
    No duplicate logic anywhere else in the codebase.
    
    Args:
        booking: Booking instance
        payment_mode: 'wallet' | 'gateway' | 'admin'
        wallet_applied: Amount deducted from wallet (if applicable)
        gateway_amount: Amount charged to gateway (if applicable)
        gateway_transaction_id: Razorpay/Cashfree transaction ID
        user: User making the payment (for logging)
        
    Returns:
        {
            'status': 'success' | 'error',
            'message': str,
            'booking_id': str,
            'new_status': str
        }
    
    Raises: Exception on DB-level failure (caller handles)
    """
    from bookings.pricing_calculator import calculate_pricing
    from payments.models import Wallet, WalletTransaction
    from hotels.channel_manager_service import release_inventory_on_failure
    
    if not user:
        user = booking.user
    
    # ============================================
    # STEP 1: VALIDATE PRE-CONDITIONS
    # ============================================
    
    # Guard: Booking must be in payment-pending state
    if booking.status not in ['reserved', 'payment_pending']:
        logger.warning(
            "[PAYMENT_FINALIZE_ERROR] booking=%s status=%s - cannot finalize from this status",
            booking.booking_id, booking.status
        )
        return {
            'status': 'error',
            'message': f'Booking is in {booking.get_status_display()} state. Cannot process payment.',
            'booking_id': str(booking.booking_id),
            'new_status': booking.status
        }
    
    # Guard: Check reservation timeout
    if booking.check_reservation_timeout():
        logger.warning("[PAYMENT_FINALIZE_EXPIRED] booking=%s - reservation expired", booking.booking_id)
        # Automatically expire it
        booking.status = 'expired'
        booking.save(update_fields=['status'])
        return {
            'status': 'error',
            'message': 'Reservation expired. Please create a new booking.',
            'booking_id': str(booking.booking_id),
            'new_status': 'expired'
        }

    # ============================================
    # STEP 1B: DATA INTEGRITY VALIDATION (HOTEL)
    # ============================================
    if booking.booking_type == 'hotel':
        hotel_booking = getattr(booking, 'hotel_details', None) or getattr(booking, 'hotel_booking', None)
        room_type = getattr(hotel_booking, 'room_type', None) if hotel_booking else None
        hotel = getattr(room_type, 'hotel', None) if room_type else None

        if not hotel_booking or not room_type or not hotel:
            logger.error(
                "[PAYMENT_FINALIZE_INTEGRITY_ERROR] booking=%s hotel_booking_present=%s room_type_present=%s hotel_present=%s",
                booking.booking_id,
                bool(hotel_booking),
                bool(room_type),
                bool(hotel)
            )
            return {
                'status': 'error',
                'message': 'Invalid hotel booking data. Cannot process payment.',
                'booking_id': str(booking.booking_id),
                'new_status': booking.status
            }
    
    # ============================================
    # STEP 2: RECALCULATE PRICING (FRESH)
    # ============================================
    try:
        pricing = calculate_pricing(
            booking=booking,
            promo_code=booking.promo_code,
            wallet_apply_amount=wallet_applied,
            user=user
        )
    except Exception as e:
        logger.error(
            "[PAYMENT_FINALIZE_PRICING_ERROR] booking=%s error=%s",
            booking.booking_id, str(e), exc_info=True
        )
        return {
            'status': 'error',
            'message': 'Pricing calculation failed. Please try again.',
            'booking_id': str(booking.booking_id),
            'new_status': booking.status
        }
    
    # ============================================
    # STEP 3: VALIDATE AMOUNTS
    # ============================================
    
    total_paid = wallet_applied + gateway_amount
    expected_total = pricing['total_payable']
    
    # Allow ±1 paisa tolerance for rounding
    if abs(total_paid - expected_total) > Decimal('0.01'):
        logger.error(
            "[PAYMENT_FINALIZE_AMOUNT_MISMATCH] booking=%s expected=%.2f actual=%.2f wallet=%.2f gateway=%.2f",
            booking.booking_id, expected_total, total_paid, wallet_applied, gateway_amount
        )
        return {
            'status': 'error',
            'message': f'Payment amount mismatch. Expected ₹{expected_total}, got ₹{total_paid}',
            'booking_id': str(booking.booking_id),
            'new_status': booking.status
        }
    
    # ============================================
    # STEP 4: ATOMIC TRANSACTION - FINALIZE PAYMENT
    # ============================================
    
    try:
        with transaction.atomic():
            # Lock booking row for update
            booking = booking.__class__.objects.select_for_update().get(pk=booking.pk)
            
            # Re-check after lock (guard against race condition)
            if booking.status not in ['reserved', 'payment_pending']:
                logger.warning(
                    "[PAYMENT_FINALIZE_RACE] booking=%s status changed to %s during lock",
                    booking.booking_id, booking.status
                )
                return {
                    'status': 'error',
                    'message': 'Booking state changed. Please refresh and try again.',
                    'booking_id': str(booking.booking_id),
                    'new_status': booking.status
                }
            
            # ============================================================
            # WALLET DEDUCTION (if applicable)
            # ============================================================
            if wallet_applied > Decimal('0.00'):
                try:
                    wallet = Wallet.objects.select_for_update().get(user=user, is_active=True)
                    wallet_balance_before = wallet.balance
                    
                    if wallet.balance < wallet_applied:
                        logger.error(
                            "[PAYMENT_FINALIZE_INSUFFICIENT_WALLET] booking=%s required=%.2f available=%.2f",
                            booking.booking_id, wallet_applied, wallet.balance
                        )
                        return {
                            'status': 'error',
                            'message': f'Insufficient wallet balance',
                            'booking_id': str(booking.booking_id),
                            'new_status': booking.status
                        }
                    
                    # Deduct wallet
                    wallet.balance -= wallet_applied
                    wallet.save(update_fields=['balance', 'updated_at'])
                    
                    # Record transaction
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='DEBIT',
                        amount=wallet_applied,
                        description=f'Payment for booking {booking.booking_id}',
                        booking=booking,
                        status='SUCCESS'
                    )
                    
                    # Store for audit
                    booking.wallet_balance_before = wallet_balance_before
                    booking.wallet_balance_after = wallet.balance
                    
                    logger.info(
                        "[PAYMENT_FINALIZE_WALLET_DEDUCTED] [WALLET_DEDUCTED] booking=%s user=%s amount=%.2f wallet_before=%.2f wallet_after=%.2f",
                        booking.booking_id, user.email, wallet_applied, wallet_balance_before, wallet.balance
                    )
                    
                except Wallet.DoesNotExist:
                    logger.error("[PAYMENT_FINALIZE_NO_WALLET] booking=%s user=%s", booking.booking_id, user.email)
                    return {
                        'status': 'error',
                        'message': 'Wallet not found',
                        'booking_id': str(booking.booking_id),
                        'new_status': booking.status
                    }
            
            # ============================================================
            # UPDATE BOOKING - FINALIZATION
            # ============================================================
            
            booking.status = 'confirmed'
            booking.confirmed_at = timezone.now()
            booking.total_amount = pricing['total_payable']  # Store final amount
            booking.paid_amount = total_paid
            booking.payment_reference = gateway_transaction_id or f"wallet_{booking.booking_id}"
            
            booking.save(update_fields=[
                'status',
                'confirmed_at',
                'total_amount',
                'paid_amount',
                'payment_reference',
                'wallet_balance_before',
                'wallet_balance_after',
                'updated_at'
            ])
            
            # ============================================================
            # CREATE PAYMENT RECORD
            # ============================================================
            from payments.models import Payment
            
            Payment.objects.create(
                booking=booking,
                amount=total_paid,
                payment_method=payment_mode,
                status='success',
                transaction_id=booking.payment_reference,
                transaction_date=timezone.now(),
                gateway_response={
                    'wallet_amount': float(wallet_applied),
                    'gateway_amount': float(gateway_amount),
                    'mode': payment_mode
                }
            )
            
            logger.info(
                "[PAYMENT_FINALIZE_SUCCESS] booking=%s mode=%s user=%s status=confirmed amount=%.2f wallet=%.2f gateway=%.2f",
                booking.booking_id, payment_mode, user.email, pricing['total_payable'], wallet_applied, gateway_amount
            )
            
    except Exception as e:
        logger.error(
            "[PAYMENT_FINALIZE_ATOMIC_FAILURE] booking=%s error=%s",
            booking.booking_id, str(e), exc_info=True
        )
        
        # Release inventory on payment failure
        try:
            release_inventory_on_failure(booking)
        except Exception as inv_err:
            logger.error(
                "[PAYMENT_FINALIZE_INVENTORY_RELEASE_ERROR] booking=%s error=%s",
                booking.booking_id, str(inv_err)
            )
        
        return {
            'status': 'error',
            'message': 'Payment processing failed. Please contact support.',
            'booking_id': str(booking.booking_id),
            'new_status': booking.status
        }
    
    # ============================================================
    # STEP 5: SUCCESS - SEND NOTIFICATIONS (ASYNC)
    # ============================================================
    # TODO: Trigger async tasks
    # send_booking_confirmation_sms.delay(booking.booking_id)
    # send_booking_confirmation_email.delay(booking.booking_id)
    # send_invoice.delay(booking.booking_id)
    
    return {
        'status': 'success',
        'message': 'Booking confirmed successfully!',
        'booking_id': str(booking.booking_id),
        'new_status': 'confirmed',
        'final_amount': float(pricing['total_payable']),
        'wallet_deducted': float(wallet_applied),
        'gateway_charged': float(gateway_amount)
    }
