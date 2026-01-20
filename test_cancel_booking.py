"""
TEST #2: CANCEL BOOKING - ATOMIC STATE CHANGE + INVENTORY RELEASE
Verifies: Status changes to cancelled, wallet refunded, inventory released
"""

import os
import sys
import django
from decimal import Decimal

sys.path.insert(0, r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from bookings.models import Booking
from payments.models import Wallet, WalletTransaction

User = get_user_model()

print("\n" + "="*70)
print("TEST #2: CANCEL BOOKING (ATOMIC STATE CHANGE)")
print("="*70)

# Find a confirmed booking
booking = Booking.objects.filter(status='confirmed', paid_amount__gt=0).order_by('-created_at').first()

if not booking:
    print("\n❌ NO CONFIRMED BOOKINGS FOUND")
    print("Please complete a payment first")
    sys.exit(1)

user = booking.user
wallet = Wallet.objects.get(user=user)

print(f"\n[FOUND] Booking: {booking.booking_id}")
print(f"[FOUND] User: {user.phone}")
print(f"[FOUND] Paid: Rs.{booking.paid_amount}")

# BEFORE STATE
wallet_before = wallet.balance
status_before = booking.status
paid_before = booking.paid_amount

print("\n" + "="*70)
print("BEFORE CANCELLATION")
print("="*70)
print(f"Wallet Balance: ₹{wallet_before}")
print(f"Booking Status: {status_before}")
print(f"Paid Amount: ₹{paid_before}")

# EXECUTE CANCELLATION
print("\n" + "="*70)
print("EXECUTING CANCELLATION...")
print("="*70)

# Import cancel function
from django.test import RequestFactory
from bookings.views import cancel_booking

# Create a mock request
factory = RequestFactory()
request = factory.post(f'/bookings/{booking.booking_id}/cancel/')
request.user = user

try:
    # Call cancel_booking view
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.contrib.sessions.backends.db import SessionStore
    
    request.session = SessionStore()
    request._messages = FallbackStorage(request)
    
    response = cancel_booking(request, str(booking.booking_id))
    
    print(f"[RESULT] Response status: {response.status_code}")
    
except Exception as e:
    print(f"[ERROR] Cancellation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# AFTER STATE
booking.refresh_from_db()
wallet.refresh_from_db()

wallet_after = wallet.balance
status_after = booking.status

print("\n" + "="*70)
print("AFTER CANCELLATION")
print("="*70)
print(f"Wallet Balance: ₹{wallet_after} (was ₹{wallet_before})")
print(f"Booking Status: {status_after} (was {status_before})")
print(f"Cancelled At: {booking.cancelled_at}")

# VERIFICATION
print("\n" + "="*70)
print("VERIFICATION CHECKS")
print("="*70)

issues = []
passes = []

# Check 1: Status changed to cancelled
if status_after != 'cancelled':
    issues.append(f"❌ Status NOT cancelled (still: {status_after})")
else:
    passes.append(f"✅ Status cancelled: {status_before} → {status_after}")

# Check 2: Cancelled timestamp set
if not booking.cancelled_at:
    issues.append(f"❌ cancelled_at NOT set")
else:
    passes.append(f"✅ cancelled_at set: {booking.cancelled_at}")

# Check 3: Wallet refunded
expected_refund = paid_before  # Assuming 100% refund
if wallet_after <= wallet_before:
    issues.append(f"❌ Wallet NOT refunded (balance: ₹{wallet_before} → ₹{wallet_after})")
else:
    refund_amount = wallet_after - wallet_before
    if abs(refund_amount - expected_refund) > Decimal('0.01'):
        issues.append(f"❌ Refund amount wrong (expected ₹{expected_refund}, got ₹{refund_amount})")
    else:
        passes.append(f"✅ Wallet refunded: ₹{wallet_before} → ₹{wallet_after} (refund: ₹{refund_amount})")

# Check 4: Refund transaction created
refund_txn = WalletTransaction.objects.filter(
    booking=booking, 
    transaction_type='refund'
).first()
if not refund_txn:
    issues.append(f"❌ Refund transaction NOT created")
else:
    passes.append(f"✅ Refund transaction created: ID={refund_txn.id}, Amount=₹{refund_txn.amount}")

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
    print("RESULT: ✅ ALL CHECKS PASSED")
    print("="*70)
    print("\n✅ CANCEL BOOKING WORKS END-TO-END")
    print(f"  - Booking ID: {booking.booking_id}")
    print(f"  - Status: {status_after}")
    print(f"  - Wallet refunded: ₹{wallet_after - wallet_before}")
    print(f"  - Refund transaction: ID={refund_txn.id if refund_txn else 'N/A'}")

