"""
Management command to seed wallet and cashback test data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from payments.models import Wallet, CashbackLedger

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed wallet and cashback test data for testing end-to-end flows'

    def handle(self, *args, **options):
        # Get or create test user
        test_user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'testuser@goexplorer.com',
                'first_name': 'Test',
                'last_name': 'User',
            }
        )
        
        if created:
            test_user.set_password('testpass123')
            test_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created test user: {test_user.username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Test user already exists: {test_user.username}'))
        
        # Create or update wallet
        wallet, wallet_created = Wallet.objects.get_or_create(
            user=test_user,
            defaults={
                'balance': Decimal('5000.00'),
                'currency': 'INR',
                'is_active': True,
            }
        )
        
        if wallet_created:
            self.stdout.write(self.style.SUCCESS(f'Created wallet for {test_user.username} with balance ₹5000'))
        else:
            wallet.balance = Decimal('5000.00')
            wallet.save()
            self.stdout.write(self.style.WARNING(f'Updated wallet balance to ₹5000 for {test_user.username}'))
        
        # Create cashback entries
        # 1. Active cashback expiring in 1 year
        cashback_1year, cb1_created = CashbackLedger.objects.get_or_create(
            wallet=wallet,
            description='Welcome Bonus',
            defaults={
                'amount': Decimal('1000.00'),
                'expires_at': timezone.now() + timedelta(days=365),
                'is_used': False,
                'is_expired': False,
            }
        )
        if cb1_created:
            self.stdout.write(self.style.SUCCESS(f'Created active cashback: ₹1000 (expires in 1 year)'))
        else:
            self.stdout.write(self.style.WARNING('Welcome bonus cashback already exists'))
        
        # 2. Used cashback
        cashback_used, cb2_created = CashbackLedger.objects.get_or_create(
            wallet=wallet,
            description='First Booking Cashback (Used)',
            defaults={
                'amount': Decimal('500.00'),
                'expires_at': timezone.now() + timedelta(days=300),
                'is_used': True,
                'used_on': timezone.now() - timedelta(days=10),
                'used_amount': Decimal('500.00'),
                'is_expired': False,
            }
        )
        if cb2_created:
            self.stdout.write(self.style.SUCCESS(f'Created used cashback: ₹500'))
        else:
            self.stdout.write(self.style.WARNING('Used cashback already exists'))
        
        # 3. Expired cashback
        cashback_expired, cb3_created = CashbackLedger.objects.get_or_create(
            wallet=wallet,
            description='Old Promo Cashback (Expired)',
            defaults={
                'amount': Decimal('200.00'),
                'expires_at': timezone.now() - timedelta(days=10),
                'is_used': False,
                'is_expired': True,
                'expired_on': timezone.now() - timedelta(days=10),
            }
        )
        if cb3_created:
            self.stdout.write(self.style.SUCCESS(f'Created expired cashback: ₹200'))
        else:
            self.stdout.write(self.style.WARNING('Expired cashback already exists'))
        
        self.stdout.write(self.style.SUCCESS('\n=== Test Data Summary ==='))
        self.stdout.write(f'User: {test_user.username} / {test_user.email}')
        self.stdout.write(f'Password: testpass123')
        self.stdout.write(f'Wallet Balance: ₹{wallet.balance}')
        self.stdout.write(f'Active Cashback: ₹{cashback_1year.amount} (expires: {cashback_1year.expires_at.date()})')
        self.stdout.write(f'Used Cashback: ₹{cashback_used.amount}')
        self.stdout.write(f'Expired Cashback: ₹{cashback_expired.amount}')
        self.stdout.write(self.style.SUCCESS('\nTest data seeded successfully!'))
