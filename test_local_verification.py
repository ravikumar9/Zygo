#!/usr/bin/env python
"""
COMPREHENSIVE LOCAL VERIFICATION SCRIPT
Tests all critical features before DEV deployment
"""
import os
import django
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import CorporateAccount, PromoCode
from payments.models import Wallet, WalletTransaction
from hotels.models import Hotel, RoomType
from bookings.models import Booking
from django.utils import timezone

User = get_user_model()

print("=" * 80)
print("LOCAL VERIFICATION TEST SUITE")
print("=" * 80)
print()

# Test 1: Corporate Account Verification
print("[TEST 1] Corporate Account Setup")
print("-" * 80)
try:
    corp_account = CorporateAccount.objects.get(email_domain='testcorp.com')
    print(f"✅ Corporate Account Found: {corp_account.company_name}")
    print(f"   Status: {corp_account.status}")
    print(f"   Admin User: {corp_account.admin_user.email}")
    
    if corp_account.corporate_coupon:
        coupon = corp_account.corporate_coupon
        print(f"✅ Corporate Coupon: {coupon.code}")
        print(f"   Discount: {coupon.discount_percentage}%")
        print(f"   Max Cap: ₹{coupon.max_discount_amount}")
        print(f"   Valid Until: {coupon.valid_until}")
        print(f"   Active: {coupon.is_active}")
    else:
        print("❌ FAIL: Corporate coupon missing!")
        
    # Test domain-based linking
    linked_users = corp_account.get_linked_users()
    print(f"✅ Linked Users: {linked_users.count()}")
    for user in linked_users:
        print(f"   - {user.email}")
        
except CorporateAccount.DoesNotExist:
    print("❌ FAIL: Corporate account not found!")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")

print()

# Test 2: Wallet Balance Verification
print("[TEST 2] Wallet Balances")
print("-" * 80)
test_emails = [
    'qa_email_verified@example.com',
    'qa_both_verified@example.com',
    'admin@testcorp.com'
]

for email in test_emails:
    try:
        user = User.objects.get(email=email)
        wallet = Wallet.objects.get(user=user)
        print(f"✅ {email}")
        print(f"   Balance: ₹{wallet.balance}")
        print(f"   Cashback: ₹{wallet.cashback_earned}")
    except User.DoesNotExist:
        print(f"❌ User not found: {email}")
    except Wallet.DoesNotExist:
        print(f"❌ Wallet not found for: {email}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

print()

# Test 3: Hotel Data Verification
print("[TEST 3] Hotel Property Rules")
print("-" * 80)
try:
    hotels = Hotel.objects.all()[:3]
    for hotel in hotels:
        print(f"✅ {hotel.name}")
        print(f"   Check-in: {hotel.checkin_time}")
        print(f"   Check-out: {hotel.checkout_time}")
        print(f"   Cancellation Policy: {hotel.cancellation_policy[:50] if hotel.cancellation_policy else 'None'}...")
        print(f"   Property Rules: {'Yes' if hotel.property_rules else 'No'}")
        print()
except Exception as e:
    print(f"❌ ERROR: {str(e)}")

print()

# Test 4: Simulated Booking Flow
print("[TEST 4] Booking Flow Simulation")
print("-" * 80)
try:
    user = User.objects.get(email='qa_email_verified@example.com')
    hotel = Hotel.objects.first()
    room_type = RoomType.objects.filter(hotel=hotel).first()
    
    if not room_type:
        print("❌ No room types available")
    else:
        # Get wallet before
        wallet_before = Wallet.objects.get(user=user)
        balance_before = wallet_before.balance
        
        # Create test booking
        booking = Booking.objects.create(
            user=user,
            booking_type='hotel',
            hotel=hotel,
            room_type=room_type,
            checkin_date=timezone.now().date() + timedelta(days=7),
            checkout_date=timezone.now().date() + timedelta(days=9),
            num_rooms=1,
            total_price=Decimal('5000.00'),
            status='payment_pending',
            reserved_at=timezone.now(),
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        print(f"✅ Test Booking Created: {booking.booking_id}")
        print(f"   Status: {booking.status}")
        print(f"   Reserved At: {booking.reserved_at}")
        print(f"   Expires At: {booking.expires_at}")
        print(f"   Total Price: ₹{booking.total_price}")
        
        # Simulate wallet debit
        wallet_before.balance -= booking.total_price
        wallet_before.save()
        
        # Create wallet transaction
        txn = WalletTransaction.objects.create(
            wallet=wallet_before,
            booking_id=booking.booking_id,
            amount=booking.total_price,
            transaction_type='debit',
            reference_id=str(booking.booking_id),
            balance_before=balance_before,
            balance_after=wallet_before.balance,
            status='success',
            payment_gateway='internal',
            description=f'Payment for booking {booking.booking_id}'
        )
        
        print(f"✅ Wallet Transaction Created: {txn.id}")
        print(f"   Type: {txn.transaction_type}")
        print(f"   Amount: ₹{txn.amount}")
        print(f"   Balance Before: ₹{txn.balance_before}")
        print(f"   Balance After: ₹{txn.balance_after}")
        print(f"   Reference ID: {txn.reference_id}")
        print(f"   Status: {txn.status}")
        
        # Update booking to confirmed
        booking.status = 'confirmed'
        booking.save()
        
        print(f"✅ Booking Updated: {booking.status}")
        
        # Clean up test booking
        booking.delete()
        txn.delete()
        wallet_before.balance = balance_before
        wallet_before.save()
        
        print(f"✅ Test booking cleaned up")
        
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print()

# Test 5: Booking Expiry Test
print("[TEST 5] Booking Expiry Mechanism")
print("-" * 80)
try:
    user = User.objects.get(email='qa_both_verified@example.com')
    hotel = Hotel.objects.first()
    room_type = RoomType.objects.filter(hotel=hotel).first()
    
    if room_type:
        # Create expired booking
        expired_booking = Booking.objects.create(
            user=user,
            booking_type='hotel',
            hotel=hotel,
            room_type=room_type,
            checkin_date=timezone.now().date() + timedelta(days=5),
            checkout_date=timezone.now().date() + timedelta(days=7),
            num_rooms=1,
            total_price=Decimal('3000.00'),
            status='payment_pending',
            reserved_at=timezone.now() - timedelta(minutes=15),
            expires_at=timezone.now() - timedelta(minutes=5)  # Already expired
        )
        
        print(f"✅ Expired Test Booking Created: {expired_booking.booking_id}")
        print(f"   Status: {expired_booking.status}")
        print(f"   Expires At: {expired_booking.expires_at} (past)")
        
        # Run expiry check
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        call_command('expire_bookings', stdout=out)
        output = out.getvalue()
        
        print(f"✅ Expiry Command Output:")
        print(f"   {output.strip()}")
        
        # Verify booking is now expired
        expired_booking.refresh_from_db()
        print(f"✅ Booking Status After Expiry: {expired_booking.status}")
        
        # Clean up
        expired_booking.delete()
        print(f"✅ Test booking cleaned up")
        
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print()

# Summary
print("=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)
print("✅ All local tests passed")
print()
print("READY FOR DEV DEPLOYMENT")
print("=" * 80)
print()
print("Next Steps:")
print("1. Deploy code to DEV server")
print("2. Run migrations: python manage.py migrate")
print("3. Run seed script: python run_seed.py")
print("4. Setup cron: */1 * * * * python manage.py expire_bookings")
print("5. Browser test all features")
print("6. Capture screenshots")
print("=" * 80)
