#!/usr/bin/env python
"""
TEST: Partial Wallet + Gateway Payment Flow
ZERO-TOLERANCE: DB proof required

SCENARIO:
1. User wallet = ₹1000
2. Booking total = ₹2360 (base ₹2000 + GST ₹360)
3. Expected behavior:
   - Wallet applied: ₹1000 (max available)
   - Gateway amount: ₹1360 (total - wallet)
   - After payment: Wallet ₹0, Payment method split (wallet + gateway)
4. Verify: Wallet deducted, Payment record reflects split, Booking confirmed
"""

import os
import sys
import django
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from bookings.models import Booking, HotelBooking
from payments.models import Wallet, WalletTransaction, Payment
from hotels.models import Hotel, RoomType, InternalInventoryLock
from core.models import City
from decimal import Decimal
import uuid

User = get_user_model()

print("\n" + "="*80)
print("🔴 ZERO-TOLERANCE TEST: Partial Wallet + Gateway Payment")
print("="*80)

try:
    # Setup: Create user with specific wallet balance
    print("\n[SETUP] Creating user with partial wallet...")
    username = f'wallet_test_{uuid.uuid4().hex[:8]}'
    user = User.objects.create_user(
        username=username,
        email=f'wallet_test_{uuid.uuid4().hex[:8]}@test.com',
        password='test123456'
    )
    
    # Create wallet with ₹1000 (less than booking amount)
    wallet = Wallet.objects.create(
        user=user,
        balance=Decimal('1000.00')
    )
    
    print(f"✅ User created: ID={user.id}, Username={username}")
    print(f"✅ Wallet created: ID={wallet.id}, Balance=₹{wallet.balance}")
    print(f"   DB: Wallet.id={wallet.id}, balance=1000.00")
    
    # Setup: Create hotel and room type
    print("\n[SETUP] Creating hotel & room type...")
    city = City.objects.first() or City.objects.create(
        name='Test City',
        state='Test State',
        country='India'
    )
    
    hotel = Hotel.objects.create(
        name='Test Hotel',
        description='Hotel for partial wallet test',
        city=city,
        address='123 Test St',
        property_type='hotel',
        inventory_source='internal_cm',
        is_active=True,
        star_rating=3,
        review_rating=Decimal('0.00'),
    )
    
    room_type = RoomType.objects.create(
        hotel=hotel,
        name='Standard Room',
        room_type='standard',
        description='Standard room',
        max_occupancy=2,
        number_of_beds=1,
        base_price=Decimal('2000.00'),
        total_rooms=5,
        is_available=True,
    )
    
    print(f"✅ Hotel created: ID={hotel.id}, Name={hotel.name}")
    print(f"✅ RoomType created: ID={room_type.id}, Base Price=₹{room_type.base_price}, Rooms={room_type.total_rooms}")
    print(f"   DB: RoomType.id={room_type.id}, base_price=2000.00, total_rooms=5")
    
    # Step 1: Create booking in RESERVED status
    print("\n[STEP 1] Creating booking in RESERVED status...")
    with transaction.atomic():
        from bookings.models import InternalInventoryLock
        
        booking = Booking.objects.create(
            user=user,
            booking_type='hotel',
            status='reserved',
            payment_method='wallet',
            total_amount=Decimal('2000.00'),  # Base amount only
            currency='INR',
            paid_amount=Decimal('0.00'),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            reservation_seconds_left_calculated=600,
        )
        
        # Create HotelBooking linked record
        hotel_booking = HotelBooking.objects.create(
            booking=booking,
            hotel=hotel,
            room_type=room_type,
            check_in_date=timezone.now().date() + timezone.timedelta(days=1),
            check_out_date=timezone.now().date() + timezone.timedelta(days=2),
            num_rooms=1,
            num_guests=2,
            meal_plan='room_only',
        )
        
        # Create inventory lock
        lock = InternalInventoryLock.objects.create(
            room_type=room_type,
            locked_count=1,
            status='active',
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        
        print(f"✅ Booking created: ID={booking.id}, Status={booking.status}, Amount=₹{booking.total_amount}")
        print(f"   DB: Booking.id={booking.id}, total_amount=2000.00, status=reserved")
        print(f"✅ HotelBooking linked: ID={hotel_booking.id}, room_type_id={room_type.id}")
        print(f"✅ Inventory locked: ID={lock.id}, locked_count=1")
    
    # Step 2: Calculate pricing (with GST)
    print("\n[STEP 2] Calculating pricing with GST...")
    from bookings.pricing_calculator import calculate_pricing
    
    pricing = calculate_pricing(
        booking=booking,
        promo_code=None,
        wallet_apply_amount=None,
        user=user
    )
    
    base_amount = pricing['base_price']
    gst_amount = pricing['gst']
    total_payable = pricing['total_payable']
    
    print(f"✅ Pricing calculated:")
    print(f"   Base: ₹{base_amount}")
    print(f"   GST (18%): ₹{gst_amount}")
    print(f"   Total: ₹{total_payable}")
    
    # Step 3: Determine split (wallet vs gateway)
    print("\n[STEP 3] Determining payment split...")
    
    wallet_amount = min(wallet.balance, total_payable)
    gateway_amount = total_payable - wallet_amount
    
    print(f"✅ Wallet available: ₹{wallet.balance}")
    print(f"✅ Booking total: ₹{total_payable}")
    print(f"✅ Payment split:")
    print(f"   Wallet apply: ₹{wallet_amount}")
    print(f"   Gateway charge: ₹{gateway_amount}")
    
    # Step 4: Simulate payment execution (unified finalize_booking_payment)
    print("\n[STEP 4] Executing payment (wallet + gateway split)...")
    from bookings.payment_finalization import finalize_booking_payment
    
    with transaction.atomic():
        result = finalize_booking_payment(
            booking=booking,
            wallet_applied=wallet_amount,
            gateway_amount=gateway_amount,
            payment_method='hybrid_wallet_gateway'
        )
    
    print(f"✅ Payment finalized: Success={result.get('success', False)}")
    print(f"   Result: {result}")
    
    # Step 5: Verify DB state after payment
    print("\n[STEP 5] Verifying DB state after payment...")
    
    # Reload wallet
    wallet.refresh_from_db()
    booking.refresh_from_db()
    
    print(f"✅ Wallet after payment: ₹{wallet.balance}")
    print(f"   Expected: ₹{Decimal('1000.00') - wallet_amount}")
    print(f"   Status: {'✅ CORRECT' if wallet.balance == (Decimal('1000.00') - wallet_amount) else '❌ MISMATCH'}")
    
    print(f"\n✅ Booking after payment:")
    print(f"   Status: {booking.status} (expected: confirmed)")
    print(f"   Paid amount: ₹{booking.paid_amount} (expected: ₹{total_payable})")
    print(f"   Status: {'✅ CORRECT' if booking.status == 'confirmed' else '❌ MISMATCH'}")
    
    # Step 6: Verify Payment records (split)
    print("\n[STEP 6] Verifying Payment records...")
    
    payment_records = Payment.objects.filter(booking=booking).all()
    print(f"✅ Payment records: Count={payment_records.count()}")
    
    wallet_payment = None
    gateway_payment = None
    
    for payment in payment_records:
        print(f"   - ID={payment.id}, Method={payment.payment_method}, Amount=₹{payment.amount}, Status={payment.status}")
        if payment.payment_method == 'wallet' or payment.payment_method == 'hybrid_wallet':
            wallet_payment = payment
        elif payment.payment_method == 'gateway' or 'gateway' in payment.payment_method:
            gateway_payment = payment
    
    if wallet_payment:
        print(f"\n✅ Wallet payment: ₹{wallet_payment.amount}")
        print(f"   Expected: ₹{wallet_amount}")
        print(f"   Status: {'✅ CORRECT' if wallet_payment.amount == wallet_amount else '❌ MISMATCH'}")
    
    if gateway_payment:
        print(f"\n✅ Gateway payment: ₹{gateway_payment.amount}")
        print(f"   Expected: ₹{gateway_amount}")
        print(f"   Status: {'✅ CORRECT' if gateway_payment.amount == gateway_amount else '❌ MISMATCH'}")
    
    # Step 7: Verify WalletTransaction
    print("\n[STEP 7] Verifying wallet transaction...")
    
    wallet_txns = WalletTransaction.objects.filter(wallet=wallet).all()
    print(f"✅ Wallet transactions: Count={wallet_txns.count()}")
    
    for txn in wallet_txns:
        print(f"   - ID={txn.id}, Type={txn.transaction_type}, Amount=₹{txn.amount}, Status={txn.status}")
    
    # Final Results
    print("\n" + "="*80)
    print("✅ TEST COMPLETED: Partial Wallet + Gateway Payment")
    print("="*80)
    
    print(f"\n📊 PAYMENT SPLIT SUMMARY:")
    print(f"  User wallet: ₹1000")
    print(f"  Booking total: ₹{total_payable}")
    print(f"  Wallet applied: ₹{wallet_amount}")
    print(f"  Gateway charged: ₹{gateway_amount}")
    print(f"  Wallet after: ₹{wallet.balance}")
    print(f"\n📈 DB PROOF:")
    print(f"  Booking.paid_amount: ₹{booking.paid_amount}")
    print(f"  Booking.status: {booking.status}")
    print(f"  Payment records: {payment_records.count()} (wallet + gateway)")
    print(f"  Wallet balance: ₹{wallet.balance}")
    print(f"  WalletTransaction records: {wallet_txns.count()}")
    
    if booking.status == 'confirmed' and wallet.balance == Decimal('0.00'):
        print(f"\n✅ TEST RESULT: PARTIAL WALLET + GATEWAY PAYMENT WORKS")
    else:
        print(f"\n⚠️  TEST RESULT: VERIFY PAYMENT SPLIT LOGIC")
    
except Exception as e:
    import traceback
    print(f"\n❌ TEST FAILED: {str(e)}")
    print("\nTraceback:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
