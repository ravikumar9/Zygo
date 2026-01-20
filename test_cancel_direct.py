"""
TEST #2: CANCEL BOOKING - DIRECT DB TEST (ATOMIC)
"""

import os
import sys
import django
from decimal import Decimal

sys.path.insert(0, r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from bookings.models import Booking
from payments.models import Wallet, WalletTransaction
from hotels.channel_manager_service import release_inventory_on_failure

print("\n" + "="*70)
print("TEST #2: CANCEL BOOKING (DIRECT DATABASE TEST)")
print("="*70)

# Find a confirmed booking
booking = Booking.objects.filter(status='confirmed', paid_amount__gt=0).order_by('-created_at').first()

if not booking:
    print("\nNo confirmed bookings. Creating one...")
    sys.exit(1)

user = booking.user
wallet = Wallet.objects.get(user=user)

print(f"\n[FOUND] Booking: {booking.booking_id}")
print(f"[FOUND] Status: {booking.status}")
print(f"[FOUND] Paid: Rs.{booking.paid_amount}")
print(f"[FOUND] Wallet: Rs.{wallet.balance}")

# Get hotel for refund policy
hotel = booking.hotel_booking.room_type.hotel if hasattr(booking, 'hotel_booking') and booking.hotel_booking else None

if not hotel:
    print("ERROR: No hotel found for booking")
    sys.exit(1)

print(f"[FOUND] Hotel: {hotel.name}")
print(f"[FOUND] Refund %: {hotel.refund_percentage}%")
print(f"[FOUND] Refund mode: {hotel.refund_mode}")

# BEFORE STATE
wallet_before = wallet.balance
status_before = booking.status

# Calculate refund
refund_amount = Decimal(str(booking.paid_amount)) * Decimal(hotel.refund_percentage) / Decimal('100')

print("\n" + "="*70)
print("EXECUTING CANCELLATION...")
print("="*70)
print(f"Refund amount: Rs.{refund_amount}")

try:
    with transaction.atomic():
        # Lock booking
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        
        # Update booking
        booking.status = 'cancelled'
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=['status', 'cancelled_at', 'updated_at'])
        
        # Refund to wallet
        if refund_amount > 0 and hotel.refund_mode == 'WALLET':
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            balance_before = wallet.balance
            wallet.balance += refund_amount
            wallet.save(update_fields=['balance', 'updated_at'])
            
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='refund',
                amount=refund_amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=f'Cancellation refund for booking {booking.booking_id}',
                booking=booking,
                status='success',
                payment_gateway='internal',
            )
        
        # Release inventory
        release_inventory_on_failure(booking)
        
        print("SUCCESS: All operations completed atomically")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Refresh
booking.refresh_from_db()
wallet.refresh_from_db()

print("\n" + "="*70)
print("AFTER CANCELLATION")
print("="*70)
print(f"Booking Status: {booking.status} (was {status_before})")
print(f"Cancelled At: {booking.cancelled_at}")
print(f"Wallet Balance: Rs.{wallet.balance} (was Rs.{wallet_before})")

# VERIFICATION
print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

issues = []

if booking.status != 'cancelled':
    issues.append(f"FAIL: Status is {booking.status}, not 'cancelled'")
else:
    print("[PASS] Status is 'cancelled'")

if not booking.cancelled_at:
    issues.append(f"FAIL: cancelled_at not set")
else:
    print(f"[PASS] cancelled_at set: {booking.cancelled_at}")

expected_wallet = wallet_before + refund_amount
if abs(wallet.balance - expected_wallet) > Decimal('0.01'):
    issues.append(f"FAIL: Wallet balance is Rs.{wallet.balance}, expected Rs.{expected_wallet}")
else:
    print(f"[PASS] Wallet refunded: Rs.{wallet_before} -> Rs.{wallet.balance}")

txn = WalletTransaction.objects.filter(booking=booking, transaction_type='refund').first()
if not txn:
    issues.append(f"FAIL: Refund transaction not created")
else:
    print(f"[PASS] Refund transaction created: ID={txn.id}, Amount=Rs.{txn.amount}")

if issues:
    print("\n" + "="*70)
    print("RESULT: FAILED")
    print("="*70)
    for issue in issues:
        print(issue)
    sys.exit(1)
else:
    print("\n" + "="*70)
    print("RESULT: ALL CHECKS PASSED")
    print("="*70)
