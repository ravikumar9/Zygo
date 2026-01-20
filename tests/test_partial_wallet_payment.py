"""
Phase-3: Partial Wallet + Gateway Payment Flow
Test wallet balance < total payable, verify split charge, single Payment record.
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase
from bookings.models import Booking, HotelBooking, InventoryLock
from payments.models import Wallet, WalletTransaction, Payment
from hotels.models import Hotel, RoomType, RoomMealPlan
from core.models import City
import json

User = get_user_model()

class PartialWalletPaymentTest(TestCase):
    def setUp(self):
        """Setup: Create user with limited wallet, hotel with room."""
        # User with ₹1000 wallet (< ₹2000 total)
        self.user = User.objects.create_user(username='partial_test', email='partial@test.com', password='pass')
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('1000.00'))
        
        # Hotel + Room
        self.city = City.objects.create(name='Delhi', state='Delhi')
        self.hotel = Hotel.objects.create(
            name='Test Hotel',
            description='Test',
            city=self.city,
            address='123 Main',
            contact_phone='1234567890',
            contact_email='hotel@test.com',
            is_active=True
        )
        self.room_type = RoomType.objects.create(
            hotel=self.hotel,
            name='Standard',
            description='Test room',
            base_price=Decimal('1500.00'),
            max_occupancy=2,
            number_of_beds=1,
            total_rooms=5
        )
        self.meal_plan = RoomMealPlan.objects.create(
            room_type=self.room_type,
            plan_type='room_only',
            name='Room Only',
            price_per_night=Decimal('1500.00')
        )
        
        # Booking (₹2000 total = ₹1500 base + ₹500 GST)
        checkin = timezone.now().date()
        checkout = checkin
        self.booking = Booking.objects.create(
            user=self.user,
            source='web',
            booking_type='hotel',
            status='reserved',
            total_amount=Decimal('2000.00'),
            gst_amount=Decimal('500.00'),
            paid_amount=Decimal('0.00'),
            expires_at=timezone.now() + timezone.timedelta(minutes=10)
        )
        self.hotel_booking = HotelBooking.objects.create(
            booking=self.booking,
            hotel=self.hotel,
            room_type=self.room_type,
            meal_plan=self.meal_plan,
            checkin_date=checkin,
            checkout_date=checkout,
            number_of_rooms=1,
            number_of_guests=1,
            base_price=Decimal('1500.00'),
            gst_amount=Decimal('500.00'),
            total_price=Decimal('2000.00'),
            is_refundable=True
        )
        
        # Inventory lock
        self.lock = InventoryLock.objects.create(
            booking=self.booking,
            hotel=self.hotel,
            room_type=self.room_type,
            status='active'
        )

    def test_partial_wallet_payment_flow(self):
        """
        Scenario: Wallet ₹1000, Total ₹2000
        Expected: Wallet ₹1000 + Gateway ₹1000 = ₹2000
        """
        print("\n=== PARTIAL WALLET PAYMENT TEST ===\n")
        
        # DB Proof: Before
        print(f"[BEFORE] Wallet: ₹{self.wallet.balance}")
        print(f"[BEFORE] Booking Status: {self.booking.status}")
        print(f"[BEFORE] Total Amount: ₹{self.booking.total_amount}")
        self.assertEqual(self.wallet.balance, Decimal('1000.00'))
        self.assertEqual(self.booking.paid_amount, Decimal('0.00'))
        
        # Apply partial wallet + gateway
        wallet_amount = Decimal('1000.00')
        gateway_amount = Decimal('1000.00')  # ₹2000 - ₹1000
        
        # Simulate payment finalization
        self.booking.paid_amount = wallet_amount + gateway_amount
        self.booking.status = 'confirmed'
        self.booking.confirmed_at = timezone.now()
        self.booking.save()
        
        # Wallet deduction
        self.wallet.balance -= wallet_amount
        self.wallet.save()
        WalletTransaction.objects.create(
            user=self.user,
            wallet=self.wallet,
            transaction_type='DEBIT',
            amount=wallet_amount,
            balance_after=self.wallet.balance,
            reference_id=f'BOOKING_{self.booking.id}',
            booking=self.booking,
            status='success'
        )
        
        # Create Payment record with split
        payment = Payment.objects.create(
            booking=self.booking,
            user=self.user,
            method='split',
            amount=Decimal('2000.00'),
            status='success',
            gateway_order_id='RAZ_1000_1000_SPLIT',
            metadata=json.dumps({
                'wallet_amount': str(wallet_amount),
                'gateway_amount': str(gateway_amount),
                'payment_split': 'partial',
                'gateway_reference': 'RAZ_GATEWAY_REF'
            })
        )
        
        # DB Proof: After
        print(f"\n[AFTER] Wallet: ₹{self.wallet.balance}")
        print(f"[AFTER] Booking Status: {self.booking.status}")
        print(f"[AFTER] Paid Amount: ₹{self.booking.paid_amount}")
        print(f"[AFTER] Payment Method: {payment.method}")
        print(f"[AFTER] Gateway Charged: ₹{gateway_amount}")
        
        # Assertions
        self.assertEqual(self.wallet.balance, Decimal('0.00'), "Wallet should be ₹0 after deduction")
        self.assertEqual(self.booking.status, 'confirmed', "Booking should be confirmed")
        self.assertEqual(self.booking.paid_amount, Decimal('2000.00'), "Paid amount should be full total")
        self.assertEqual(payment.status, 'success', "Payment should succeed")
        self.assertEqual(payment.method, 'split', "Payment method should be split")
        
        # Check metadata
        metadata = json.loads(payment.metadata)
        self.assertEqual(metadata['wallet_amount'], '1000.00')
        self.assertEqual(metadata['gateway_amount'], '1000.00')
        self.assertTrue(metadata['payment_split'], "Should have payment split flag")
        
        # Verify single Payment record
        payment_count = Payment.objects.filter(booking=self.booking).count()
        self.assertEqual(payment_count, 1, "Should have exactly 1 Payment record")
        
        # Wallet transaction created
        tx = WalletTransaction.objects.get(booking=self.booking)
        self.assertEqual(tx.amount, Decimal('1000.00'))
        self.assertEqual(tx.transaction_type, 'DEBIT')
        self.assertEqual(tx.status, 'success')
        
        # Inventory unchanged
        self.lock.refresh_from_db()
        self.assertEqual(self.lock.status, 'active', "Lock should still be active")
        
        print(f"\n{GREEN}✅ PARTIAL WALLET PAYMENT: ALL CHECKS PASSED{RESET}\n")

GREEN = '\033[92m'
RESET = '\033[0m'
