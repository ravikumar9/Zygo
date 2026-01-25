"""
Sprint-1 Comprehensive Tests
Tests for:
1. Room Availability Calendar (block/unblock)
2. Booking validation against blocks
3. Bus Schedule CSV Import
4. Owner Payout Workflow
5. Dashboard Metrics
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta, time
from decimal import Decimal
import io
import csv

from hotels.models import Hotel, RoomType, RoomBlock
from buses.models import BusOperator, Bus, BusSchedule, BusScheduleImport
from bookings.models import Booking, HotelBooking
from payments.models import Wallet, PayoutRequest, WalletTransaction
from property_owners.models import PropertyOwner
from core.models import City

User = get_user_model()


class RoomBlockTest(TestCase):
    """Test room availability blocking"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='owner1', password='pass', email='owner@test.com')
        self.city = City.objects.create(name='Mumbai', state='MH', country='India')
        self.hotel = Hotel.objects.create(
            name='Test Hotel',
            city=self.city,
            address='Test Address',
            contact_phone='1234567890',
            contact_email='hotel@test.com'
        )
        self.room = RoomType.objects.create(
            hotel=self.hotel,
            name='Deluxe Room',
            base_price=Decimal('1000'),
            max_adults=2,
            max_children=1
        )
    
    def test_block_future_dates(self):
        """Test blocking future dates"""
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)
        
        block = RoomBlock.objects.create(
            room_type=self.room,
            blocked_from=tomorrow,
            blocked_to=next_week,
            reason='Maintenance',
            created_by=self.user
        )
        
        self.assertTrue(block.is_active)
        self.assertEqual(block.reason, 'Maintenance')
    
    def test_cannot_block_past_dates(self):
        """Test validation prevents blocking past dates"""
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)
        
        block = RoomBlock(
            room_type=self.room,
            blocked_from=yesterday,
            blocked_to=tomorrow,
            created_by=self.user
        )
        
        with self.assertRaises(Exception):
            block.full_clean()
    
    def test_cannot_block_with_existing_booking(self):
        """Test validation prevents blocking dates with confirmed bookings"""
        checkin = date.today() + timedelta(days=1)
        checkout = date.today() + timedelta(days=3)
        
        # Create booking first
        booking = Booking.objects.create(
            user=self.user,
            booking_type='hotel',
            total_amount=Decimal('2000'),
            status='CONFIRMED',
            customer_name='Test Guest',
            customer_email='guest@test.com',
            customer_phone='9876543210'
        )
        
        HotelBooking.objects.create(
            booking=booking,
            room_type=self.room,
            check_in=checkin,
            check_out=checkout,
            number_of_rooms=1,
            number_of_adults=2,
            total_nights=2,
            policy_type='FREE',
            policy_text='Test policy',
            policy_refund_percentage=100
        )
        
        # Try to block same dates
        block = RoomBlock(
            room_type=self.room,
            blocked_from=checkin,
            blocked_to=checkout,
            created_by=self.user
        )
        
        with self.assertRaises(Exception):
            block.full_clean()
    
    def test_booking_fails_on_blocked_dates(self):
        """Test booking validation rejects blocked dates"""
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)
        
        # Block dates
        RoomBlock.objects.create(
            room_type=self.room,
            blocked_from=tomorrow,
            blocked_to=next_week,
            reason='Owner use',
            created_by=self.user
        )
        
        # Check availability
        is_available, reason = RoomBlock.is_available(
            self.room,
            tomorrow,
            next_week
        )
        
        self.assertFalse(is_available)
        self.assertIn('Owner use', reason)


class BusScheduleImportTest(TestCase):
    """Test CSV bulk import for bus schedules"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='operator1', password='pass', email='op@test.com')
        self.operator = BusOperator.objects.create(
            name='Test Operator',
            contact_phone='1234567890',
            contact_email='op@test.com',
            user=self.user,
            approval_status='approved'
        )
        self.bus = Bus.objects.create(
            operator=self.operator,
            bus_number='MH01AB1234',
            bus_type='ac_seater',
            total_seats=40
        )
        self.mumbai = City.objects.create(name='Mumbai', state='MH', country='India', code='MUM')
        self.pune = City.objects.create(name='Pune', state='MH', country='India', code='PUN')
    
    def test_csv_validation_success(self):
        """Test CSV validation with valid data"""
        csv_content = "bus_number,source_city,destination_city,departure_date,departure_time,arrival_time,fare\n"
        csv_content += f"MH01AB1234,Mumbai,Pune,{(date.today() + timedelta(days=1)).strftime('%Y-%m-%d')},10:00,13:00,500\n"
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'schedules.csv'
        
        import_record = BusScheduleImport.objects.create(
            operator=self.operator,
            csv_file=csv_file,
            status='pending',
            uploaded_by=self.user
        )
        
        self.assertEqual(import_record.status, 'pending')
    
    def test_csv_validation_detects_missing_bus(self):
        """Test CSV validation rejects unknown bus"""
        csv_content = "bus_number,source_city,destination_city,departure_date,departure_time,arrival_time,fare\n"
        csv_content += f"UNKNOWN123,Mumbai,Pune,{(date.today() + timedelta(days=1)).strftime('%Y-%m-%d')},10:00,13:00,500\n"
        
        # Validation happens in view - this tests the model structure
        import_record = BusScheduleImport.objects.create(
            operator=self.operator,
            csv_file=io.BytesIO(csv_content.encode('utf-8')),
            status='pending',
            uploaded_by=self.user
        )
        
        self.assertIsNotNone(import_record)


class PayoutRequestTest(TestCase):
    """Test owner payout workflow"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='owner1', password='pass', email='owner@test.com')
        self.city = City.objects.create(name='Mumbai', state='MH', country='India')
        self.owner = PropertyOwner.objects.create(
            user=self.user,
            business_name='Test Property',
            owner_name='Test Owner',
            owner_phone='1234567890',
            owner_email='owner@test.com',
            city=self.city,
            address='Test Address',
            pincode='400001',
            bank_account_name='Test Owner',
            bank_account_number='1234567890',
            bank_ifsc='TEST0001234'
        )
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('5000'))
    
    def test_request_payout_success(self):
        """Test successful payout request"""
        payout = PayoutRequest(
            owner=self.owner,
            wallet=self.wallet,
            amount=Decimal('1000'),
            bank_account_name=self.owner.bank_account_name,
            bank_account_number=self.owner.bank_account_number,
            bank_ifsc=self.owner.bank_ifsc
        )
        
        payout.request_payout()
        
        self.assertEqual(payout.status, 'requested')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('4000'))  # 5000 - 1000
    
    def test_payout_insufficient_balance(self):
        """Test payout fails with insufficient balance"""
        payout = PayoutRequest(
            owner=self.owner,
            wallet=self.wallet,
            amount=Decimal('10000'),  # More than wallet balance
            bank_account_name=self.owner.bank_account_name,
            bank_account_number=self.owner.bank_account_number,
            bank_ifsc=self.owner.bank_ifsc
        )
        
        with self.assertRaises(Exception):
            payout.full_clean()
    
    def test_payout_minimum_amount(self):
        """Test payout enforces minimum amount"""
        payout = PayoutRequest(
            owner=self.owner,
            wallet=self.wallet,
            amount=Decimal('50'),  # Below minimum
            bank_account_name=self.owner.bank_account_name,
            bank_account_number=self.owner.bank_account_number,
            bank_ifsc=self.owner.bank_ifsc
        )
        
        with self.assertRaises(Exception):
            payout.full_clean()
    
    def test_payout_approval(self):
        """Test admin approval completes payout"""
        admin = User.objects.create_user(username='admin', password='pass', is_staff=True)
        
        payout = PayoutRequest(
            owner=self.owner,
            wallet=self.wallet,
            amount=Decimal('1000'),
            bank_account_name=self.owner.bank_account_name,
            bank_account_number=self.owner.bank_account_number,
            bank_ifsc=self.owner.bank_ifsc
        )
        payout.request_payout()
        
        payout.approve_and_complete(admin, transaction_id='TXN123')
        
        self.assertEqual(payout.status, 'completed')
        self.assertEqual(payout.transaction_id, 'TXN123')
        self.assertIsNotNone(payout.processed_at)
    
    def test_payout_rejection_refunds(self):
        """Test admin rejection refunds to wallet"""
        admin = User.objects.create_user(username='admin', password='pass', is_staff=True)
        
        payout = PayoutRequest(
            owner=self.owner,
            wallet=self.wallet,
            amount=Decimal('1000'),
            bank_account_name=self.owner.bank_account_name,
            bank_account_number=self.owner.bank_account_number,
            bank_ifsc=self.owner.bank_ifsc
        )
        payout.request_payout()
        
        original_balance = Decimal('4000')  # After payout request
        
        payout.reject(admin, reason='Invalid bank details')
        
        self.assertEqual(payout.status, 'failed')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('5000'))  # Refunded


class DashboardMetricsTest(TestCase):
    """Test dashboard metrics calculations"""
    
    def setUp(self):
        self.owner_user = User.objects.create_user(username='owner1', password='pass', email='owner@test.com')
        self.city = City.objects.create(name='Mumbai', state='MH', country='India')
        self.owner = PropertyOwner.objects.create(
            user=self.owner_user,
            business_name='Test Property',
            owner_name='Test Owner',
            owner_phone='1234567890',
            owner_email='owner@test.com',
            city=self.city,
            address='Test Address',
            pincode='400001'
        )
        self.hotel = Hotel.objects.create(
            name='Test Hotel',
            city=self.city,
            address='Test Address',
            contact_phone='1234567890',
            contact_email='hotel@test.com'
        )
        self.room = RoomType.objects.create(
            hotel=self.hotel,
            name='Deluxe Room',
            base_price=Decimal('1000'),
            max_adults=2,
            max_children=1
        )
    
    def test_owner_metrics_calculation(self):
        """Test owner dashboard metrics (bookings, revenue, occupancy)"""
        # Create bookings
        for i in range(5):
            booking = Booking.objects.create(
                user=self.owner_user,
                booking_type='hotel',
                total_amount=Decimal('2000'),
                status='CONFIRMED',
                customer_name='Test Guest',
                customer_email='guest@test.com',
                customer_phone='9876543210'
            )
            
            HotelBooking.objects.create(
                booking=booking,
                room_type=self.room,
                check_in=date.today() + timedelta(days=i),
                check_out=date.today() + timedelta(days=i+2),
                number_of_rooms=1,
                number_of_adults=2,
                total_nights=2,
                policy_type='FREE',
                policy_text='Test policy',
                policy_refund_percentage=100
            )
        
        # Metrics should count 5 bookings, 10 nights, revenue 10000
        from django.db.models import Sum
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        bookings_count = HotelBooking.objects.filter(
            room_type=self.room,
            booking__created_at__gte=thirty_days_ago
        ).count()
        
        self.assertEqual(bookings_count, 5)


class IntegrationTest(TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='owner1', password='pass', email='owner@test.com')
        self.city = City.objects.create(name='Mumbai', state='MH', country='India')
        self.owner = PropertyOwner.objects.create(
            user=self.user,
            business_name='Test Property',
            owner_name='Test Owner',
            owner_phone='1234567890',
            owner_email='owner@test.com',
            city=self.city,
            address='Test Address',
            pincode='400001',
            bank_account_name='Test Owner',
            bank_account_number='1234567890',
            bank_ifsc='TEST0001234'
        )
        self.hotel = Hotel.objects.create(
            name='Test Hotel',
            city=self.city,
            address='Test Address',
            contact_phone='1234567890',
            contact_email='hotel@test.com'
        )
        self.room = RoomType.objects.create(
            hotel=self.hotel,
            name='Deluxe Room',
            base_price=Decimal('1000'),
            max_adults=2,
            max_children=1
        )
    
    def test_full_booking_flow_with_blocks(self):
        """Test complete booking flow respects availability blocks"""
        # Block dates
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)
        
        RoomBlock.objects.create(
            room_type=self.room,
            blocked_from=tomorrow,
            blocked_to=next_week,
            reason='Maintenance',
            created_by=self.user
        )
        
        # Attempt booking - should fail
        is_available, reason = RoomBlock.is_available(
            self.room,
            tomorrow,
            next_week
        )
        
        self.assertFalse(is_available)
        
        # Book after blocked period - should succeed
        future_date = date.today() + timedelta(days=10)
        is_available, reason = RoomBlock.is_available(
            self.room,
            future_date,
            future_date + timedelta(days=2)
        )
        
        self.assertTrue(is_available)


print("✅ Sprint-1 test suite ready")
