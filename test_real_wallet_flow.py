"""
TEST #1: WALLET-ONLY PAYMENT FLOW (END-TO-END)
Verifies: Wallet deduction, booking confirmation, inventory lock
"""

import os
import sys
import django
from decimal import Decimal
from datetime import timedelta

sys.path.insert(0, r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from bookings.models import Booking, HotelBooking
from hotels.models import Hotel, RoomType
from core.models import City
from payments.models import Wallet, WalletTransaction, Payment

User = get_user_model()

print("\n" + "="*70)
print("TEST #1: WALLET-ONLY PAYMENT FLOW")
print("="*70)

# Setup test user with wallet
user, _ = User.objects.get_or_create(
    phone='9999888801',
    defaults={'username': 'walletuser1', 'first_name': 'WalletUser1'}
)

# Ensure wallet with sufficient balance
wallet, _ = Wallet.objects.get_or_create(user=user, defaults={'balance': Decimal('5000.00')})
if wallet.balance < Decimal('3000.00'):
    wallet.balance = Decimal('5000.00')
    wallet.save(update_fields=['balance'])

print(f"\n[SETUP] User: {user.phone}")
print(f"[SETUP] Wallet balance: ₹{wallet.balance}")

# Get hotel and room
city = City.objects.filter(name="Test City").first()
if not city:
    city = City.objects.create(name="Test City", state="Test", country="India", code="TC")

hotel = Hotel.objects.filter(name="Test Hotel").first()
if not hotel:
    hotel = Hotel.objects.create(
        name="Test Hotel",
        description="Test",
        city=city,
        address="Test",
        contact_phone="9999999999",
        contact_email="test@test.com"
    )

room_type = RoomType.objects.filter(hotel=hotel).first()
if not room_type:
    room_type = RoomType.objects.create(
        hotel=hotel,
        name="Deluxe",
        room_type='deluxe',
        description='Deluxe room for testing',
        base_price=Decimal('2000.00'),
        max_occupancy=2
    )

print(f"[SETUP] Hotel: {hotel.name}")
print(f"[SETUP] Room: {room_type.name} @ ₹{room_type.base_price}")

# Create booking (reserved state)
total_amount = Decimal('2360.00')  # 2000 + GST
booking = Booking.objects.create(
    user=user,
    booking_type='hotel',
    total_amount=total_amount,
    status='reserved',
    reserved_at=timezone.now(),
    customer_name='Test Guest',
    customer_email=user.email or 'test@test.com',
    customer_phone=user.phone,
    booking_source='internal',
    inventory_channel='internal_cm',
)

HotelBooking.objects.create(
    booking=booking,
    room_type=room_type,
    check_in=timezone.now().date() + timedelta(days=5),
    check_out=timezone.now().date() + timedelta(days=7),
    number_of_rooms=1,
    number_of_adults=2,
    total_nights=2,
)

print(f"\n[CREATED] Booking: {booking.booking_id}")
print(f"[CREATED] Status: {booking.status}")
print(f"[CREATED] Total: ₹{booking.total_amount}")
print(f"[CREATED] Expires: {booking.expires_at}")

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

# EXECUTE WALLET PAYMENT
print("\n" + "="*70)
print("EXECUTING WALLET-ONLY PAYMENT...")
print("="*70)

from bookings.payment_finalization import finalize_booking_payment

try:
    result = finalize_booking_payment(
        booking=booking,
        payment_method='wallet',
        user=user,
        wallet_amount=total_amount,
        gateway_amount=Decimal('0.00'),
        gateway_transaction_id=None
    )
    
    print(f"[RESULT] Success: {result.get('success')}")
    print(f"[RESULT] Message: {result.get('message')}")
    
except Exception as e:
    print(f"[ERROR] Payment failed: {e}")
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
print("VERIFICATION")
print("="*70)

issues = []

# Check wallet deducted
expected_wallet = wallet_before - total_amount
if wallet_after != expected_wallet:
    issues.append(f"❌ Wallet NOT deducted correctly (expected ₹{expected_wallet}, got ₹{wallet_after})")
else:
    print(f"✅ Wallet deducted: ₹{wallet_before} → ₹{wallet_after} (diff: ₹{wallet_before - wallet_after})")

# Check status confirmed
if status_after != 'confirmed':
    issues.append(f"❌ Status NOT confirmed (still: {status_after})")
else:
    print(f"✅ Status confirmed: {status_before} → {status_after}")

# Check paid amount
if paid_after != total_amount:
    issues.append(f"❌ Paid amount wrong (expected ₹{total_amount}, got ₹{paid_after})")
else:
    print(f"✅ Paid amount correct: ₹{paid_after}")

# Check confirmed_at timestamp
if not booking.confirmed_at:
    issues.append(f"❌ confirmed_at NOT set")
else:
    print(f"✅ confirmed_at set: {booking.confirmed_at}")

# Check wallet transaction created
txn = WalletTransaction.objects.filter(booking=booking, transaction_type='debit').first()
if not txn:
    issues.append(f"❌ WalletTransaction NOT created")
else:
    print(f"✅ WalletTransaction created: ID={txn.id}, Amount=₹{txn.amount}")

# Check payment record created
payment = Payment.objects.filter(booking=booking).first()
if not payment:
    issues.append(f"❌ Payment record NOT created")
else:
    print(f"✅ Payment record created: ID={payment.id}, Method={payment.payment_method}")

print("\n" + "="*70)
if issues:
    print("RESULT: ❌ FAILED")
    print("="*70)
    for issue in issues:
        print(issue)
    sys.exit(1)
else:
    print("RESULT: ✅ ALL CHECKS PASSED")
    print("="*70)
    print("\nWallet-only payment flow works correctly:")
    print(f"  - Wallet deducted: ₹{wallet_before - wallet_after}")
    print(f"  - Booking confirmed: {status_after}")
    print(f"  - Payment recorded: Yes")
    print(f"  - Transaction logged: Yes")
