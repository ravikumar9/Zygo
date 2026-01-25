"""
FIX-4 STEP-4: Cancellation Action & Refund Execution
Provides refund preview and cancellation endpoints using locked snapshot fields
"""

from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal
import json
import logging
from bookings.models import Booking
from bookings.inventory_utils import restore_inventory
from payments.models import Wallet, WalletTransaction

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def refund_preview_api(request, booking_id):
    """
    API endpoint to preview refund amount and eligibility.
    Uses LOCKED snapshot fields ONLY - no live policy lookups.
    
    Returns:
    {
        "booking_id": "...",
        "paid_amount": 5000.00,
        "policy_type": "PARTIAL",
        "policy_refund_percentage": 50,
        "refund_amount": 2500.00,
        "free_cancel_until": "2026-01-25T18:00:00Z",
        "is_free_cancellation": false,
        "is_eligible_for_full_refund": true,
        "cancellation_warning": null,
        "formula": "paid_amount × policy_refund_percentage / 100"
    }
    """
    try:
        booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
        
        # Guard: Only confirmed or reserved bookings can be cancelled
        if booking.status not in ['confirmed', 'reserved', 'payment_pending']:
            return JsonResponse({
                'status': 'error',
                'message': f'Cannot cancel booking in {booking.get_status_display()} status',
                'cancellable': False
            }, status=400)
        
        # Get hotel booking details
        hotel_booking = getattr(booking, 'hotel_details', None)
        if not hotel_booking:
            return JsonResponse({
                'status': 'error',
                'message': 'Hotel booking details not found'
            }, status=404)
        
        # CRITICAL: Use snapshot fields ONLY
        paid_amount = booking.paid_amount
        policy_type = hotel_booking.policy_type
        policy_refund_percentage = hotel_booking.policy_refund_percentage or 0
        policy_free_cancel_until = hotel_booking.policy_free_cancel_until
        
        # Calculate refund using snapshot
        refund_amount = float(paid_amount) * float(policy_refund_percentage) / 100.0
        
        # Check eligibility
        now = timezone.now()
        is_free_cancellation = False
        is_eligible_for_full_refund = False
        cancellation_warning = None
        
        if policy_type == 'FREE':
            is_free_cancellation = True
            is_eligible_for_full_refund = True
        elif policy_type == 'PARTIAL' and policy_free_cancel_until:
            if now <= policy_free_cancel_until:
                is_free_cancellation = True
                is_eligible_for_full_refund = True
            else:
                cancellation_warning = f'Free cancellation period ended on {policy_free_cancel_until.strftime("%d %b %Y, %H:%M")}'
        elif policy_type == 'NON_REFUNDABLE':
            cancellation_warning = 'This booking is non-refundable. You will not receive any refund.'
        
        return JsonResponse({
            'status': 'success',
            'booking_id': str(booking.booking_id),
            'paid_amount': float(paid_amount),
            'policy_type': policy_type,
            'policy_refund_percentage': int(policy_refund_percentage),
            'refund_amount': round(refund_amount, 2),
            'free_cancel_until': policy_free_cancel_until.isoformat() if policy_free_cancel_until else None,
            'is_free_cancellation': is_free_cancellation,
            'is_eligible_for_full_refund': is_eligible_for_full_refund,
            'cancellation_warning': cancellation_warning,
            'formula': 'refund_amount = paid_amount × policy_refund_percentage / 100',
            'policy_text': hotel_booking.policy_text,
            'cancellable': True
        }, status=200)
        
    except Exception as e:
        logger.error("[REFUND_PREVIEW_ERROR] booking=%s error=%s", booking_id, str(e), exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to calculate refund preview'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def cancel_booking_with_refund(request, booking_id):
    """
    POST endpoint to cancel booking and process refund.
    Uses LOCKED snapshot fields ONLY.
    
    Returns:
    {
        "status": "success",
        "booking_id": "...",
        "refund_amount": 2500.00,
        "message": "Booking cancelled. Refund of ₹2500.00 processed."
    }
    """
    from bookings.models import HotelBooking
    
    try:
        booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
        
        # Idempotent guards
        if booking.status == 'cancelled':
            return JsonResponse({
                'status': 'info',
                'message': 'Booking is already cancelled.',
                'booking_id': str(booking.booking_id)
            }, status=200)
        
        if booking.status in ['expired', 'deleted', 'refunded', 'completed']:
            return JsonResponse({
                'status': 'error',
                'message': f'Cannot cancel booking in {booking.get_status_display()} status',
                'booking_id': str(booking.booking_id)
            }, status=400)
        
        if booking.status not in ['confirmed', 'reserved', 'payment_pending']:
            return JsonResponse({
                'status': 'error',
                'message': f'Cannot cancel booking in {booking.get_status_display()} status',
                'booking_id': str(booking.booking_id)
            }, status=400)
        
        # Get hotel booking
        hotel_booking = getattr(booking, 'hotel_details', None)
        if not hotel_booking:
            return JsonResponse({
                'status': 'error',
                'message': 'Hotel booking details not found'
            }, status=404)
        
        # Process cancellation atomically
        with transaction.atomic():
            # Lock booking row for update
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            
            # Double-check status after locking
            if booking.status == 'cancelled':
                return JsonResponse({
                    'status': 'info',
                    'message': 'Booking is already cancelled.',
                    'booking_id': str(booking.booking_id)
                }, status=200)
            
            if booking.status not in ['confirmed', 'reserved', 'payment_pending']:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Cannot cancel booking in {booking.get_status_display()} status',
                    'booking_id': str(booking.booking_id)
                }, status=400)
            
            # CRITICAL: Calculate refund using LOCKED SNAPSHOT FIELDS ONLY
            paid_amount = Decimal(str(booking.paid_amount))
            policy_refund_percentage = Decimal(str(hotel_booking.policy_refund_percentage or 0))
            refund_amount = paid_amount * policy_refund_percentage / Decimal('100')

            # Restore inventory for the cancelled stay
            try:
                restore_inventory(
                    room_type=hotel_booking.room_type,
                    check_in=hotel_booking.check_in,
                    check_out=hotel_booking.check_out,
                    num_rooms=hotel_booking.number_of_rooms or 1,
                )
            except Exception as inv_err:
                logger.warning("[CANCEL_RESTORE_INVENTORY_FAIL] booking=%s error=%s", booking.booking_id, str(inv_err))
            
            # Update booking state
            old_status = booking.status
            booking.status = 'cancelled'
            booking.cancelled_at = timezone.now()
            booking.refund_amount = refund_amount
            booking.save(update_fields=['status', 'cancelled_at', 'refund_amount', 'updated_at'])
            
            # Refund to wallet if amount > 0
            if refund_amount > 0:
                wallet, _ = Wallet.objects.select_for_update().get_or_create(
                    user=request.user,
                    defaults={'balance': Decimal('0.00')}
                )
                balance_before = wallet.balance
                wallet.balance += refund_amount
                wallet.save(update_fields=['balance', 'updated_at'])
                
                # Create wallet transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='refund',
                    amount=refund_amount,
                    balance_before=balance_before,
                    balance_after=wallet.balance,
                    description=f'Cancellation refund for booking {booking.booking_id}',
                    booking=booking,
                    status='success',
                    payment_gateway='internal'
                )
            
            # Log cancellation
            logger.info(
                "[BOOKING_CANCELLED_STEP4] booking=%s old_status=%s new_status=cancelled "
                "paid_amount=%.2f policy_refund_percent=%d refund_amount=%.2f policy_type=%s",
                booking.booking_id, old_status, float(paid_amount), int(policy_refund_percentage),
                float(refund_amount), hotel_booking.policy_type
            )
        
        return JsonResponse({
            'status': 'success',
            'booking_id': str(booking.booking_id),
            'old_status': old_status,
            'new_status': 'cancelled',
            'refund_amount': float(refund_amount),
            'message': f'Booking cancelled. Refund of ₹{float(refund_amount):.2f} processed to wallet.'
        }, status=200)
        
    except Exception as e:
        logger.error("[BOOKING_CANCELLATION_ERROR] booking=%s error=%s", booking_id, str(e), exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Cancellation failed. Please try again or contact support.'
        }, status=500)
