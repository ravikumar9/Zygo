"""Seed test data for promo codes and user wallets"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from bookings.promo_models import PromoCode
from users.wallet_models import UserWallet
from users.models import User


def seed_promo_codes():
    """Create test promo codes"""
    print("Creating promo codes...")
    
    # Valid promo codes
    promo_codes = [
        {
            'code': 'SUMMER20',
            'discount_type': 'PERCENTAGE',
            'discount_value': Decimal('20'),
            'max_discount': Decimal('1000'),
            'min_booking_amount': Decimal('2000'),
            'valid_from': timezone.now() - timedelta(days=30),
            'valid_until': timezone.now() + timedelta(days=90),
            'max_uses': 1000,
            'is_active': True,
            'description': '20% off on all bookings above ₹2000'
        },
        {
            'code': 'WELCOME100',
            'discount_type': 'FLAT',
            'discount_value': Decimal('100'),
            'max_discount': None,
            'min_booking_amount': Decimal('500'),
            'valid_from': timezone.now() - timedelta(days=10),
            'valid_until': timezone.now() + timedelta(days=60),
            'max_uses': 500,
            'is_active': True,
            'description': 'Flat ₹100 off on your first booking'
        },
        {
            'code': 'EXPIRED10',
            'discount_type': 'PERCENTAGE',
            'discount_value': Decimal('10'),
            'max_discount': Decimal('500'),
            'min_booking_amount': Decimal('1000'),
            'valid_from': timezone.now() - timedelta(days=60),
            'valid_until': timezone.now() - timedelta(days=1),  # Expired
            'max_uses': 100,
            'is_active': True,
            'description': 'Expired promo code'
        },
        {
            'code': 'INVALID',
            'discount_type': 'PERCENTAGE',
            'discount_value': Decimal('50'),
            'max_discount': Decimal('2000'),
            'min_booking_amount': Decimal('5000'),
            'valid_from': timezone.now(),
            'valid_until': timezone.now() + timedelta(days=30),
            'max_uses': 10,
            'uses_count': 10,  # Max uses reached
            'is_active': True,
            'description': 'Max uses reached'
        },
    ]
    
    for promo_data in promo_codes:
        promo, created = PromoCode.objects.get_or_create(
            code=promo_data['code'],
            defaults=promo_data
        )
        if created:
            print(f"✓ Created promo code: {promo.code}")
        else:
            print(f"- Promo code already exists: {promo.code}")


def seed_user_wallets():
    """Create wallets for test users"""
    print("\nCreating user wallets...")
    
    # Create test users if they don't exist
    test_users = [
        {'email': 'test@example.com', 'first_name': 'Test', 'last_name': 'User', 'balance': 5000},
        {'email': 'user1@example.com', 'first_name': 'User', 'last_name': 'One', 'balance': 10000},
        {'email': 'user2@example.com', 'first_name': 'User', 'last_name': 'Two', 'balance': 500},
        {'email': 'lowbalance@example.com', 'first_name': 'Low', 'last_name': 'Balance', 'balance': 50},
    ]
    
    for user_data in test_users:
        balance = user_data.pop('balance')
        user, created = User.objects.get_or_create(
            email=user_data['email'],
            defaults={
                'username': user_data['email'].split('@')[0],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'email_verified_at': timezone.now(),
            }
        )
        
        if created:
            user.set_password('password123')
            user.save()
            print(f"✓ Created user: {user.email}")
        
        # Create or update wallet
        wallet, wallet_created = UserWallet.objects.get_or_create(
            user=user,
            defaults={'balance': balance}
        )
        
        if wallet_created:
            print(f"✓ Created wallet for {user.email} with balance ₹{balance}")
        else:
            wallet.balance = balance
            wallet.save()
            print(f"- Updated wallet for {user.email} to ₹{balance}")


if __name__ == '__main__':
    print("=" * 60)
    print("SEEDING PROMO CODES AND USER WALLETS")
    print("=" * 60)
    
    seed_promo_codes()
    seed_user_wallets()
    
    print("\n" + "=" * 60)
    print("✓ DATA SEEDING COMPLETE")
    print("=" * 60)
