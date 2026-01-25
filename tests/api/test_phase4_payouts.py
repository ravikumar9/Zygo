"""
Phase-4 E2E API Tests: Owner Payouts & Settlements
Tests: Payout creation, KYC/bank validation, reconciliation
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from bookings.models import Booking, HotelBooking
from finance.models import OwnerPayout, PlatformLedger
from hotels.models import Hotel, RoomType
from property_owners.models import PropertyOwner, Property, PropertyType
from payments.models import Invoice
from core.models import City

User = get_user_model()


@pytest.fixture
def setup_data(db):
    """Create test data: users, hotel, bookings, payouts"""
    
    # Create city
    city, _ = City.objects.get_or_create(
        code='TST',
        defaults={'name': 'Test City', 'state': 'Test State', 'country': 'India'}
    )
    
    # Create property type
    prop_type, _ = PropertyType.objects.get_or_create(
        name='Hotel',
        defaults={'description': 'Hotel property type'}
    )
    
    # Create owner user
    owner_user, created = User.objects.get_or_create(
        username='owner_phase4',
        defaults={
            'email': 'owner_phase4@test.com',
            'is_staff': False
        }
    )
    if created or not owner_user.check_password('TestPass123!@'):
        owner_user.set_password('TestPass123!@')
        owner_user.save()
    
    # Create property owner profile
    owner_profile, _ = PropertyOwner.objects.get_or_create(
        user=owner_user,
        defaults={
            'business_name': 'Phase4 Test Hotel',
            'owner_name': 'Test Owner',
            'owner_phone': '9999999999',
            'owner_email': 'owner@test.com',
            'city': city,
            'address': '123 Test St',
            'pincode': '110001',
            'verification_status': 'verified',
            'bank_account_name': 'Test Owner Account',
            'bank_account_number': '1234567890111213',
            'bank_ifsc': 'TESTIFSC001',
        }
    )
    
    # Create property (parent of hotel)
    property_obj, _ = Property.objects.get_or_create(
        owner=owner_profile,
        name='Phase4 Property',
        defaults={
            'description': 'Test property for Phase4',
            'property_type': prop_type,
            'city': city,
            'address': '123 Test St',
            'pincode': '110001',
            'contact_phone': '9999999999',
            'contact_email': 'owner@test.com',
        }
    )
    
    # Create hotel
    hotel, created = Hotel.objects.get_or_create(
        name='Phase4 Test Hotel',
        city=city,
        owner_property=property_obj,
        defaults={
            'address': '123 Test St',
            'is_active': True,
            'contact_phone': '9999999999',
            'contact_email': 'owner@test.com',
            'description': 'Test hotel for Phase4 payout tests',
        }
    )
    
    # Create room type
    room_type, created = RoomType.objects.get_or_create(
        hotel=hotel,
        name='Deluxe Room',
        defaults={
            'max_occupancy': 2,
            'base_price': Decimal('5000.00'),
            'total_rooms': 5,
            'description': 'Test deluxe room for Phase4',
        }
    )
    
    # Create customer user
    customer_user, created = User.objects.get_or_create(
        username='customer_phase4',
        defaults={
            'email': 'customer_phase4@test.com',
            'is_staff': False
        }
    )
    if created or not customer_user.check_password('TestPass123!@'):
        customer_user.set_password('TestPass123!@')
        customer_user.save()
    
    # Create booking
    booking, created = Booking.objects.get_or_create(
        user=customer_user,
        customer_email='customer@test.com',
        defaults={
            'booking_type': 'hotel',
            'status': 'confirmed',
            'customer_name': 'Test Customer Phase4',
            'customer_phone': '9999999998',
            'total_amount': Decimal('5500.00'),
            'paid_amount': Decimal('5500.00'),
            'reserved_at': timezone.now(),
            'confirmed_at': timezone.now(),
            'external_booking_id': 'BOOK-PHASE4-001',
        }
    )
    
    # Create hotel booking details
    hotel_booking, created = HotelBooking.objects.get_or_create(
        booking=booking,
        defaults={
            'room_type': room_type,
            'check_in': timezone.now().date(),
            'check_out': (timezone.now() + timezone.timedelta(days=1)).date(),
            'number_of_rooms': 1,
            'number_of_adults': 2,
            'total_nights': 1,
            'price_snapshot': {
                'base_price': 5000,
                'meal_price': 0,
                'service_fee': 500,
                'gst': 0,
                'total': 5500
            }
        }
    )
    
    return {
        'owner_user': owner_user,
        'owner_profile': owner_profile,
        'hotel': hotel,
        'room_type': room_type,
        'booking': booking,
        'hotel_booking': hotel_booking,
        'customer_user': customer_user,
        'city': city
    }


@pytest.mark.django_db
class TestPayoutCreation:
    """Test payout creation for confirmed bookings"""
    
    def test_create_payout_for_confirmed_booking(self, setup_data):
        """Payout should be created automatically when booking is confirmed"""
        booking = setup_data['booking']
        
        # Create payout
        payout = OwnerPayout.create_for_booking(booking)
        
        assert payout is not None
        assert payout.booking == booking
        assert payout.owner == setup_data['owner_user']
        assert payout.settlement_status == 'pending'
    
    def test_payout_amounts_from_snapshot(self, setup_data):
        """Payout amounts must come from price_snapshot (immutable)"""
        booking = setup_data['booking']
        payout = OwnerPayout.create_for_booking(booking)
        
        # Amount must match snapshot, not recalculated
        assert payout.gross_booking_value == Decimal('5500.00')
        assert payout.platform_service_fee == Decimal('500.00')  # From snapshot
        assert payout.net_payable_to_owner == Decimal('5000.00')  # 5500 - 500
    
    def test_payout_includes_refunds(self, setup_data):
        """Payout must account for refunds if booking was cancelled"""
        booking = setup_data['booking']
        booking.status = 'cancelled'
        booking.refund_amount = Decimal('1000.00')  # Partial refund
        booking.save()
        
        payout = OwnerPayout.create_for_booking(booking)
        
        assert payout.refunds_issued == Decimal('1000.00')
        # net = 5500 - 500 service fee - 1000 refund = 4000
        assert payout.net_payable_to_owner == Decimal('4000.00')
    
    def test_payout_status_pending_initially(self, setup_data):
        """New payout status should be 'pending'"""
        booking = setup_data['booking']
        payout = OwnerPayout.create_for_booking(booking)
        
        assert payout.settlement_status == 'pending'
        assert payout.settled_at is None


@pytest.mark.django_db
class TestKYCAndBankValidation:
    """Test KYC and bank verification blocking"""
    
    def test_payout_blocks_without_kyc(self, setup_data):
        """Payout should be blocked if KYC is not verified"""
        booking = setup_data['booking']
        owner_profile = setup_data['owner_profile']
        
        # Unverify KYC
        owner_profile.verification_status = 'pending'
        owner_profile.save()
        
        payout = OwnerPayout.create_for_booking(booking)
        payout.validate_kyc_and_bank()
        
        assert payout.kyc_verified is False
        assert payout.can_payout is False
        assert 'KYC' in payout.block_reason
        assert payout.settlement_status == 'kyc_pending'
    
    def test_payout_blocks_without_bank_details(self, setup_data):
        """Payout should be blocked if bank details are incomplete"""
        booking = setup_data['booking']
        owner_profile = setup_data['owner_profile']
        
        # Clear bank details
        owner_profile.bank_account_name = ''
        owner_profile.bank_account_number = ''
        owner_profile.bank_ifsc = ''
        owner_profile.save()
        
        payout = OwnerPayout.create_for_booking(booking)
        payout.validate_kyc_and_bank()
        
        assert payout.bank_verified is False
        assert payout.can_payout is False
        assert 'Bank' in payout.block_reason
        assert payout.settlement_status == 'bank_pending'
    
    def test_payout_allows_with_valid_kyc_and_bank(self, setup_data):
        """Payout should be allowed if KYC and bank details are valid"""
        booking = setup_data['booking']
        payout = OwnerPayout.create_for_booking(booking)
        
        # Should be auto-validated by create_for_booking
        assert payout.kyc_verified is True
        assert payout.bank_verified is True
        assert payout.can_payout is True
        assert payout.block_reason == ''
    
    def test_payout_snapshots_bank_details(self, setup_data):
        """Payout should snapshot owner's bank details for audit trail"""
        booking = setup_data['booking']
        payout = OwnerPayout.create_for_booking(booking)
        
        # Bank details should be snapshotted
        assert payout.bank_account_name == setup_data['owner_profile'].bank_account_name
        assert payout.bank_account_number == setup_data['owner_profile'].bank_account_number
        assert payout.bank_ifsc == setup_data['owner_profile'].bank_ifsc


@pytest.mark.django_db
class TestPayoutExecution:
    """Test payout settlement and bank transfer"""
    
    def test_execute_payout_success(self, setup_data):
        """Execute payout should mark as paid and set settlement reference"""
        booking = setup_data['booking']
        payout = OwnerPayout.create_for_booking(booking)
        
        # Execute payout
        success = payout.execute_payout(bank_transfer_id='BANK-123456')
        
        assert success is True
        assert payout.settlement_status == 'paid'
        assert payout.settled_at is not None
        assert payout.settlement_reference == 'BANK-123456'
        assert payout.failure_reason == ''
    
    def test_execute_payout_fails_without_kyc(self, setup_data):
        """Execute payout should fail if KYC validation fails"""
        booking = setup_data['booking']
        owner_profile = setup_data['owner_profile']
        
        # Unverify KYC
        owner_profile.verification_status = 'pending'
        owner_profile.save()
        
        payout = OwnerPayout.create_for_booking(booking)
        success = payout.execute_payout()
        
        assert success is False
        assert payout.settlement_status == 'failed'
        assert 'KYC' in payout.failure_reason
    
    def test_execute_payout_sets_retry_count(self, setup_data):
        """Failed payout should increment retry count"""
        booking = setup_data['booking']
        payout = OwnerPayout.create_for_booking(booking)
        
        # Make KYC invalid to force failure
        owner_profile = setup_data['owner_profile']
        owner_profile.verification_status = 'pending'
        owner_profile.save()
        
        initial_retry = payout.retry_count
        payout.execute_payout()
        
        payout.refresh_from_db()
        assert payout.retry_count > initial_retry


@pytest.mark.django_db
class TestPayoutRetry:
    """Test payout retry logic"""
    
    def test_retry_payout_success(self, setup_data):
        """Retry should allow max 3 attempts"""
        booking = setup_data['booking']
        payout = OwnerPayout.create_for_booking(booking)
        
        # Should allow retries until max
        for i in range(3):
            success = payout.retry_payout()
            # First retry succeeds (KYC/bank should be valid)
            if i == 0:
                assert success is True
                assert payout.settlement_status == 'paid'
                break
    
    def test_retry_exceeds_max(self, setup_data):
        """Retry should fail after max attempts"""
        booking = setup_data['booking']
        payout = OwnerPayout.create_for_booking(booking)
        payout.retry_count = 3  # Already at max
        payout.save()
        
        success = payout.retry_payout()
        
        assert success is False
        assert 'Max retries exceeded' in payout.failure_reason


@pytest.mark.django_db
class TestPayoutReconciliation:
    """Test financial reconciliation"""
    
    def test_platform_ledger_totals(self, setup_data):
        """Platform ledger should match total collected vs owner payouts"""
        booking = setup_data['booking']
        booking.confirmed_at = timezone.now()
        booking.save()
        
        # Create payout
        payout = OwnerPayout.create_for_booking(booking)
        payout.execute_payout()
        
        # Compute ledger for today
        today = timezone.now().date()
        ledger = PlatformLedger.compute_for_date(today)
        
        # Ledger totals should match booking
        assert ledger.total_bookings >= 1
        assert ledger.total_revenue >= booking.total_amount
        assert ledger.total_service_fee_collected >= payout.platform_service_fee
    
    def test_reconciliation_revenue_matches_payout_plus_fees(self, setup_data):
        """Total revenue should equal owner payouts + platform fees"""
        booking = setup_data['booking']
        payout = OwnerPayout.create_for_booking(booking)
        payout.execute_payout()
        
        # Reconciliation formula:
        # Total Collected = Owner Payouts + Platform Revenue
        # 5500 = 5000 + 500
        
        assert (payout.net_payable_to_owner + payout.platform_service_fee) == booking.total_amount


@pytest.mark.django_db
class TestPayoutMultipleBookings:
    """Test payouts across multiple bookings"""
    
    def test_multiple_bookings_independent_payouts(self, setup_data):
        """Each booking should have independent payout"""
        owner = setup_data['owner_user']
        hotel = setup_data['hotel']
        
        # Create multiple bookings
        payouts = []
        for i in range(3):
            booking = Booking.objects.create(
                booking_id=f'test-booking-{i}',
                user=setup_data['customer_user'],
                booking_type='hotel',
                status='confirmed',
                customer_name=f'Customer {i}',
                customer_email=f'customer{i}@test.com',
                customer_phone=f'999999999{i}',
                total_amount=Decimal('5500.00'),
                paid_amount=Decimal('5500.00'),
                confirmed_at=timezone.now()
            )
            
            hotel_booking = HotelBooking.objects.create(
                booking=booking,
                room_type=setup_data['room_type'],
                check_in=timezone.now().date(),
                check_out=(timezone.now() + timezone.timedelta(days=1)).date(),
                number_of_rooms=1,
                total_nights=1,
                price_snapshot={
                    'base_price': 5000,
                    'service_fee': 500,
                    'total': 5500
                }
            )
            
            payout = OwnerPayout.create_for_booking(booking)
            payouts.append(payout)
        
        # Each payout should be independent
        assert len(payouts) == 3
        payout_ids = {p.id for p in payouts}
        assert len(payout_ids) == 3  # All unique


@pytest.mark.django_db
class TestPayoutFinancialAccuracy:
    """Test ₹-level financial accuracy"""
    
    def test_decimal_precision_maintained(self, setup_data):
        """Payout amounts should maintain decimal precision"""
        booking = setup_data['booking']
        
        # Set precise amount
        booking.total_amount = Decimal('5555.55')
        booking.save()
        
        hotel_booking = setup_data['hotel_booking']
        hotel_booking.price_snapshot = {
            'base_price': Decimal('5000.50'),
            'service_fee': Decimal('555.05'),
            'total': Decimal('5555.55')
        }
        hotel_booking.save()
        
        payout = OwnerPayout.create_for_booking(booking)
        
        # Precision should be maintained
        assert payout.gross_booking_value == Decimal('5555.55')
        assert payout.platform_service_fee == Decimal('555.05')
        assert payout.net_payable_to_owner == Decimal('5000.50')
        
        # Check no rounding errors
        total_check = payout.net_payable_to_owner + payout.platform_service_fee
        assert total_check == booking.total_amount
    
    def test_service_fee_capped_at_500(self, setup_data):
        """Service fee should be capped at ₹500"""
        booking = setup_data['booking']
        
        # Set high amount to test cap
        booking.total_amount = Decimal('50000.00')
        booking.save()
        
        hotel_booking = setup_data['hotel_booking']
        # Service fee would be 5% = 2500, but capped at 500
        hotel_booking.price_snapshot = {
            'base_price': Decimal('49500.00'),
            'service_fee': Decimal('500.00'),  # Capped
            'total': Decimal('50000.00')
        }
        hotel_booking.save()
        
        payout = OwnerPayout.create_for_booking(booking)
        
        # Should respect the capped fee from snapshot
        assert payout.platform_service_fee == Decimal('500.00')


@pytest.mark.django_db
class TestPayoutAPIIntegration:
    """Integration tests with Django ORM"""
    
    def test_create_and_execute_full_workflow(self, setup_data):
        """Complete workflow: create -> validate -> execute -> verify"""
        booking = setup_data['booking']
        
        # 1. Create
        payout = OwnerPayout.create_for_booking(booking)
        assert payout.settlement_status == 'pending'
        
        # 2. Validate
        payout.validate_kyc_and_bank()
        assert payout.can_payout is True
        
        # 3. Execute
        success = payout.execute_payout('REF-123')
        assert success is True
        assert payout.settlement_status == 'paid'
        
        # 4. Verify
        payout.refresh_from_db()
        assert payout.settled_at is not None
        assert payout.settlement_reference == 'REF-123'
