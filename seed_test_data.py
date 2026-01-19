"""
Test Data Seeding Script

This script is called on dev server startup to populate test data.
Run manually: python seed_test_data.py

Creates:
- Wallet with balance ₹2000
- Promo Codes (WELCOME500 global, USER1000 user-specific)
- Test bookings in various states
"""
import os
import sys
import django
from datetime import timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from bookings.models import Booking, HotelBooking
from core.models import PromoCode
from payments.models import Wallet
from hotels.models import Hotel, RoomType

User = get_user_model()


def seed_wallets():
    """Seed test user wallets with ₹2000 balance"""
    print("🔄 Seeding wallets...")
    
    try:
        user = User.objects.get(email='qa_both_verified@example.com')
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={'balance': Decimal('2000.00')}
        )
        if created:
            print(f"✅ Wallet created for {user.email}: ₹{wallet.balance}")
        else:
            if wallet.balance < Decimal('2000.00'):
                wallet.balance = Decimal('2000.00')
                wallet.save()
                print(f"✅ Wallet updated for {user.email}: ₹{wallet.balance}")
            else:
                print(f"ℹ️  Wallet already exists: ₹{wallet.balance}")
    except User.DoesNotExist:
        print("⚠️  Test user not found, skipping wallet seed")


def seed_promo_codes():
    """Seed global and user-specific promo codes"""
    print("🔄 Seeding promo codes...")
    
    now = timezone.now()
    
    # Global promo: WELCOME500 - ₹500 flat discount
    global_promo, created = PromoCode.objects.get_or_create(
        code='WELCOME500',
        defaults={
            'discount_type': 'flat',
            'discount_value': Decimal('500.00'),
            'valid_from': now - timedelta(days=1),
            'valid_until': now + timedelta(days=365),
            'max_total_uses': None,  # Unlimited
            'max_uses_per_user': 5,
            'min_booking_amount': Decimal('1000.00'),
            'is_active': True,
            'applicable_to': 'all',
        }
    )
    if created:
        print(f"✅ Promo created: WELCOME500 (₹500 flat, global)")
    else:
        print(f"ℹ️  Promo exists: WELCOME500")
    
    # User-specific promo: USER1000 - ₹1000 flat (Note: core.PromoCode doesn't have user_specific, use max_uses_per_user instead)
    user_promo, created = PromoCode.objects.get_or_create(
        code='USER1000',
        defaults={
            'discount_type': 'flat',
            'discount_value': Decimal('1000.00'),
            'valid_from': now - timedelta(days=1),
            'valid_until': now + timedelta(days=365),
            'max_total_uses': None,
            'max_uses_per_user': 3,
            'min_booking_amount': Decimal('5000.00'),
            'is_active': True,
            'applicable_to': 'all',
        }
    )
    if created:
        print(f"✅ Promo created: USER1000 (₹1000 flat)")
    else:
        print(f"ℹ️  Promo exists: USER1000")


def seed_bookings():
    """Seed test bookings in various states"""
    print("🔄 Seeding test bookings...")
    
    try:
        user = User.objects.get(email='qa_both_verified@example.com')
        hotel = Hotel.objects.first()
        room_type = RoomType.objects.first()
        
        if not hotel or not room_type:
            print("⚠️  Hotel or RoomType not found, skipping booking seed")
            return
        
        now = timezone.now()
        
        # Check if seed bookings already exist
        existing = Booking.objects.filter(
            user=user,
            customer_name__contains='SEED'
        ).count()
        
        if existing > 0:
            print(f"ℹ️  Test bookings already exist ({existing} found)")
            return
        
        # Reserved booking (payment pending)
        reserved_booking = Booking.objects.create(
            user=user,
            booking_type='hotel',
            status='reserved',
            total_amount=Decimal('8000.00'),
            paid_amount=Decimal('0.00'),
            customer_name=f"{user.email} [SEED]",
            customer_email=user.email,
            customer_phone='+919999999999',
            reserved_at=now,
            expires_at=now + timedelta(minutes=30),
        )
        HotelBooking.objects.create(
            booking=reserved_booking,
            hotel=hotel,
            room_type=room_type,
            check_in=(now + timedelta(days=1)).date(),
            check_out=(now + timedelta(days=2)).date(),
            num_rooms=1,
            num_guests=2,
        )
        print(f"✅ Reserved booking created: ₹{reserved_booking.total_amount}")
        
    except User.DoesNotExist:
        print("⚠️  Test user not found, skipping booking seed")
    except Exception as e:
        print(f"⚠️  Error seeding bookings: {e}")


def main():
    print("\n" + "="*60)
    print("🌱 TEST DATA SEEDING - ZERO-TOLERANCE TESTING")
    print("="*60 + "\n")
    
    seed_wallets()
    seed_promo_codes()
    seed_bookings()
    
    print("\n" + "="*60)
    print("✅ SEED COMPLETE - Ready for Testing")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
