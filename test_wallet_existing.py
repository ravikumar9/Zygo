"""
TEST #1: WALLET-ONLY PAYMENT (USING EXISTING BOOKING)
Finds existing 'reserved' booking, applies wallet payment, verifies state
"""

import os
import sys
import django
from decimal import Decimal

sys.path.insert(0, r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from bookings.models import Booking
from payments.models import Wallet, WalletTransaction, Payment

User = get_user_model()

print("\n" + "="*70)
print("TEST #1: WALLET-ONLY PAYMENT FLOW (REAL DATABASE TEST)")
print("="*70)

# Find an existing reserved booking
booking = Booking.objects.filter(status='reserved').order_by('-created_at').first()

if not booking:
    print("\n❌ NO RESERVED BOOKINGS FOUND")
    print("Please create a booking first through the UI or seed script")
    sys.exit(1)

user = booking.user

# Ensure user has wallet with sufficient balance
wallet, _ = Wallet.objects.get_or_create(user=user, defaults={'balance': Decimal('0.00')})

# Top up wallet if needed
required = booking.total_amount + Decimal('100.00')
if wallet.balance < required:
    wallet.balance = required
    wallet.save(update_fields=['balance'])
    print(f"[SETUP] Topped up wallet to ₹{wallet.balance}")

print(f"\n[FOUND] Booking: {booking.booking_id}")
print(f"[FOUND] User: {user.phone}")
print(f"[FOUND] Total: ₹{booking.total_amount}")

# BEFORE STATE
wallet_before = wallet.balance
status_before = booking.status
paid_before = booking.paid_amount

print("\n" + "="*70)
print("BEFORE PAYMENT")
print("="*70)
print(f"Wallet Balance: ₹{wallet_before}")
print(f"Booking Status: {status_before}")
print(f"Paid Amount: ₹{paid_before}")
print(f"Total Amount: ₹{booking.total_amount}")
print(f"Expires At: {booking.expires_at}")

# EXECUTE WALLET PAYMENT
print("\n" + "="*70)
print("EXECUTING WALLET-ONLY PAYMENT...")
print("="*70)

from bookings.payment_finalization import finalize_booking_payment
from bookings.pricing_calculator import calculate_pricing

# Calculate correct total (with GST)
pricing = calculate_pricing(
    booking=booking,
    promo_code=booking.promo_code,
    wallet_apply_amount=Decimal('0.00'),  # Don't apply yet, just calc total
    user=user
)

total_payable_with_gst = pricing['total_payable']
print(f"[PRICING] Base amount: ₹{pricing['base_amount']}")
print(f"[PRICING] GST amount: ₹{pricing['gst_amount']}")
print(f"[PRICING] Total payable (with GST): ₹{total_payable_with_gst}")

try:
    result = finalize_booking_payment(
        booking=booking,
        payment_mode='wallet',
        wallet_applied=total_payable_with_gst,  # ← Pay the FULL amount including GST
        gateway_amount=Decimal('0.00'),
        gateway_transaction_id=None,
        user=user
    )
    
    print(f"\n[RESULT] Success: {result.get('success')}")
    print(f"[RESULT] Message: {result.get('message')}")
    
except Exception as e:
    print(f"\n[ERROR] Payment failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# AFTER STATE
booking.refresh_from_db()
wallet.refresh_from_db()

wallet_after = wallet.balance
status_after = booking.status
paid_after = booking.paid_amount

print("\n" + "="*70)
print("AFTER PAYMENT")
print("="*70)
print(f"Wallet Balance: ₹{wallet_after} (was ₹{wallet_before})")
print(f"Booking Status: {status_after} (was {status_before})")
print(f"Paid Amount: ₹{paid_after} (was ₹{paid_before})")
print(f"Confirmed At: {booking.confirmed_at}")

# VERIFICATION
print("\n" + "="*70)
print("VERIFICATION CHECKS")
print("="*70)

issues = []
passes = []

# Check 1: Wallet deducted
expected_wallet = wallet_before - booking.total_amount
if abs(wallet_after - expected_wallet) > Decimal('0.01'):
    issues.append(f"❌ Wallet NOT deducted (expected ₹{expected_wallet}, got ₹{wallet_after})")
else:
    passes.append(f"✅ Wallet deducted: ₹{wallet_before} → ₹{wallet_after} (diff: ₹{wallet_before - wallet_after})")

# Check 2: Status confirmed
if status_after != 'confirmed':
    issues.append(f"❌ Status NOT confirmed (still: {status_after})")
else:
    passes.append(f"✅ Status confirmed: {status_before} → {status_after}")

# Check 3: Paid amount
if abs(paid_after - booking.total_amount) > Decimal('0.01'):
    issues.append(f"❌ Paid amount wrong (expected ₹{booking.total_amount}, got ₹{paid_after})")
else:
    passes.append(f"✅ Paid amount correct: ₹{paid_after}")

# Check 4: Confirmed timestamp
if not booking.confirmed_at:
    issues.append(f"❌ confirmed_at NOT set")
else:
    passes.append(f"✅ confirmed_at set: {booking.confirmed_at}")

# Check 5: Wallet transaction created
txn = WalletTransaction.objects.filter(booking=booking, transaction_type='debit').first()
if not txn:
    txn = WalletTransaction.objects.filter(booking=booking, transaction_type='DEBIT').first()  # Try uppercase
if not txn:
    issues.append(f"❌ WalletTransaction NOT created")
else:
    passes.append(f"✅ WalletTransaction created: ID={txn.id}, Type={txn.transaction_type}, Amount=₹{txn.amount}")

# Check 6: Payment record created
payment = Payment.objects.filter(booking=booking).first()
if not payment:
    issues.append(f"❌ Payment record NOT created")
else:
    passes.append(f"✅ Payment record created: ID={payment.id}, Method={payment.payment_method}")

# Print results
for p in passes:
    print(p)
for issue in issues:
    print(issue)

print("\n" + "="*70)
if issues:
    print("RESULT: ❌ FAILED (" + str(len(issues)) + " issues)")
    print("="*70)
    sys.exit(1)
else:
    print("RESULT: ✅ ALL 6 CHECKS PASSED")
    print("="*70)
    print("\n✅ WALLET-ONLY PAYMENT WORKS END-TO-END")
    print(f"  - Booking ID: {booking.booking_id}")
    print(f"  - Wallet deducted: ₹{wallet_before - wallet_after}")
    print(f"  - Status: {status_after}")
    print(f"  - Confirmed: {booking.confirmed_at}")
    print(f"  - Payment method: {payment.payment_method}")
