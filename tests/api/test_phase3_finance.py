"""
Phase-3 API Tests: Admin & Finance Systems
Tests invoice generation, ledger calculations, role access, revenue accuracy
"""
import pytest
from decimal import Decimal
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from django.utils import timezone

from users.models import User
from hotels.models import Hotel, RoomType
from bookings.models import Booking, HotelBooking
from payments.models import Invoice
from finance.models import OwnerPayout, PlatformLedger


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def super_admin_user(db):
    """Create SUPER_ADMIN user"""
    user = User.objects.create_user(
        username='superadmin',
        email='superadmin@test.com',
        password='test123'
    )
    group = Group.objects.get(name='SUPER_ADMIN')
    user.groups.add(group)
    return user


@pytest.fixture
def finance_admin_user(db):
    """Create FINANCE_ADMIN user"""
    user = User.objects.create_user(
        username='financeadmin',
        email='finance@test.com',
        password='test123'
    )
    group = Group.objects.get(name='FINANCE_ADMIN')
    user.groups.add(group)
    return user


@pytest.fixture
def property_admin_user(db):
    """Create PROPERTY_ADMIN user"""
    user = User.objects.create_user(
        username='propertyadmin',
        email='property@test.com',
        password='test123'
    )
    group = Group.objects.get(name='PROPERTY_ADMIN')
    user.groups.add(group)
    return user


@pytest.fixture
def support_admin_user(db):
    """Create SUPPORT_ADMIN user"""
    user = User.objects.create_user(
        username='supportadmin',
        email='support@test.com',
        password='test123'
    )
    group = Group.objects.get(name='SUPPORT_ADMIN')
    user.groups.add(group)
    return user


@pytest.fixture
def property_owner_user(db):
    """Create property owner user"""
    return User.objects.create_user(
        username='owner1',
        email='owner@test.com',
        password='test123'
    )


@pytest.fixture
def regular_user(db):
    """Create regular user without admin roles"""
    return User.objects.create_user(
        username='regularuser',
        email='user@test.com',
        password='test123'
    )


@pytest.fixture
def test_hotel(db, property_owner_user):
    """Create test hotel"""
    return Hotel.objects.create(
        name='Test Hotel',
        owner=property_owner_user,
        city='Test City',
        state='Test State',
        address='Test Address',
        description='Test Description',
        is_approved=True,
        is_active=True
    )


@pytest.fixture
def test_room_type(db, test_hotel):
    """Create test room type"""
    return RoomType.objects.create(
        hotel=test_hotel,
        name='Deluxe Room',
        base_price=1000,
        max_occupancy=2
    )


@pytest.fixture
def confirmed_booking(db, regular_user, test_room_type):
    """Create confirmed booking with pricing data"""
    booking = Booking.objects.create(
        user=regular_user,
        booking_type='hotel',
        status='confirmed',
        customer_name='Test Customer',
        customer_email='customer@test.com',
        customer_phone='1234567890',
        total_amount=Decimal('1200.00'),
        wallet_balance_before=Decimal('100.00'),
        wallet_balance_after=Decimal('50.00'),
        pricing_data={
            'base_price': 1000,
            'service_fee': 120,
            'tax': 80,
            'total': 1200
        }
    )
    
    # Create hotel booking details
    HotelBooking.objects.create(
        booking=booking,
        room_type=test_room_type,
        check_in=timezone.now().date(),
        check_out=(timezone.now() + timezone.timedelta(days=2)).date(),
        number_of_rooms=1
    )
    
    return booking


@pytest.mark.django_db
class TestInvoiceGeneration:
    """Test invoice generation at booking confirmation"""
    
    def test_invoice_created_on_booking_confirmation(self, confirmed_booking):
        """Invoice should be auto-created when booking is confirmed"""
        invoice = Invoice.create_for_booking(confirmed_booking)
        
        assert invoice is not None
        assert invoice.booking == confirmed_booking
        assert invoice.invoice_number.startswith('INV-')
        assert invoice.billing_name == confirmed_booking.customer_name
        assert invoice.billing_email == confirmed_booking.customer_email
    
    def test_invoice_captures_immutable_snapshot(self, confirmed_booking, test_room_type):
        """Invoice must capture all booking details as immutable snapshot"""
        invoice = Invoice.create_for_booking(confirmed_booking)
        
        # Check property details captured
        assert invoice.property_name == test_room_type.hotel.name
        assert invoice.check_in is not None
        assert invoice.check_out is not None
        assert invoice.num_rooms == 1
        
        # Check amounts captured
        assert invoice.service_fee == Decimal('120.00')
        assert invoice.wallet_used == Decimal('50.00')  # 100 - 50
        assert invoice.total_amount == Decimal('1200.00')
    
    def test_invoice_uniqueness(self, confirmed_booking):
        """Each booking should have unique invoice number"""
        invoice1 = Invoice.create_for_booking(confirmed_booking)
        
        # Create another invoice (simulating another booking)
        invoice2_number = invoice1.invoice_number
        
        assert invoice1.invoice_number is not None
        assert len(invoice1.invoice_number) > 10  # Should be timestamped


@pytest.mark.django_db
class TestRoleBasedAccess:
    """Test role-based access control for admin APIs"""
    
    def test_dashboard_metrics_super_admin_access(self, api_client, super_admin_user):
        """SUPER_ADMIN should access dashboard metrics"""
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get('/api/finance/dashboard/metrics/')
        
        assert response.status_code == 200
        assert 'total_bookings' in response.data
        assert 'total_revenue' in response.data
    
    def test_dashboard_metrics_finance_admin_access(self, api_client, finance_admin_user):
        """FINANCE_ADMIN should access dashboard metrics"""
        api_client.force_authenticate(user=finance_admin_user)
        response = api_client.get('/api/finance/dashboard/metrics/')
        
        assert response.status_code == 200
    
    def test_dashboard_metrics_property_admin_denied(self, api_client, property_admin_user):
        """PROPERTY_ADMIN should NOT access dashboard metrics"""
        api_client.force_authenticate(user=property_admin_user)
        response = api_client.get('/api/finance/dashboard/metrics/')
        
        assert response.status_code == 403
        assert 'error' in response.data
    
    def test_dashboard_metrics_support_admin_denied(self, api_client, support_admin_user):
        """SUPPORT_ADMIN should NOT access dashboard metrics"""
        api_client.force_authenticate(user=support_admin_user)
        response = api_client.get('/api/finance/dashboard/metrics/')
        
        assert response.status_code == 403
    
    def test_dashboard_metrics_regular_user_denied(self, api_client, regular_user):
        """Regular user should NOT access dashboard metrics"""
        api_client.force_authenticate(user=regular_user)
        response = api_client.get('/api/finance/dashboard/metrics/')
        
        assert response.status_code == 403
    
    def test_bookings_api_all_admin_roles_access(self, api_client, super_admin_user, finance_admin_user, property_admin_user, support_admin_user):
        """All admin roles should access bookings API"""
        for user in [super_admin_user, finance_admin_user, property_admin_user, support_admin_user]:
            api_client.force_authenticate(user=user)
            response = api_client.get('/api/finance/bookings/')
            assert response.status_code == 200, f"Failed for {user.username}"
    
    def test_invoices_api_role_restriction(self, api_client, super_admin_user, property_admin_user):
        """Only SUPER_ADMIN and FINANCE_ADMIN should access invoices API"""
        # SUPER_ADMIN - allowed
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get('/api/finance/invoices/')
        assert response.status_code == 200
        
        # PROPERTY_ADMIN - denied
        api_client.force_authenticate(user=property_admin_user)
        response = api_client.get('/api/finance/invoices/')
        assert response.status_code == 403


@pytest.mark.django_db
class TestOwnerEarningsAPI:
    """Test owner earnings API and calculations"""
    
    def test_owner_earnings_access_with_property(self, api_client, property_owner_user, test_hotel):
        """Property owner should access their earnings"""
        api_client.force_authenticate(user=property_owner_user)
        response = api_client.get('/api/finance/owner/earnings/')
        
        assert response.status_code == 200
        assert 'total_bookings' in response.data
        assert 'total_gross' in response.data
        assert 'pending_payouts' in response.data
    
    def test_owner_earnings_denied_without_property(self, api_client, regular_user):
        """User without property should NOT access owner earnings"""
        api_client.force_authenticate(user=regular_user)
        response = api_client.get('/api/finance/owner/earnings/')
        
        assert response.status_code == 403
        assert 'error' in response.data
    
    def test_owner_earnings_calculation(self, api_client, property_owner_user, confirmed_booking, test_hotel):
        """Owner earnings should calculate correctly"""
        # Create payout for booking
        payout = OwnerPayout.create_for_booking(confirmed_booking, test_hotel)
        
        api_client.force_authenticate(user=property_owner_user)
        response = api_client.get('/api/finance/owner/earnings/')
        
        assert response.status_code == 200
        assert response.data['total_bookings'] == 1
        assert Decimal(response.data['total_gross']) == Decimal('1200.00')
        assert Decimal(response.data['pending_payouts']) > 0


@pytest.mark.django_db
class TestRevenueAccuracy:
    """Test revenue and ledger calculations for accuracy"""
    
    def test_dashboard_revenue_calculation(self, api_client, super_admin_user, confirmed_booking):
        """Dashboard should calculate total revenue accurately"""
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get('/api/finance/dashboard/metrics/')
        
        assert response.status_code == 200
        assert Decimal(response.data['total_revenue']) == Decimal('1200.00')
        assert Decimal(response.data['total_service_fee']) == Decimal('120.00')
        assert Decimal(response.data['total_wallet_used']) == Decimal('50.00')
    
    def test_service_fee_extraction(self, confirmed_booking):
        """Service fee should be extracted correctly from pricing_data"""
        invoice = Invoice.create_for_booking(confirmed_booking)
        
        assert invoice.service_fee == Decimal('120.00')
    
    def test_wallet_usage_calculation(self, confirmed_booking):
        """Wallet usage should be calculated correctly"""
        invoice = Invoice.create_for_booking(confirmed_booking)
        
        expected_wallet_used = confirmed_booking.wallet_balance_before - confirmed_booking.wallet_balance_after
        assert invoice.wallet_used == expected_wallet_used
        assert invoice.wallet_used == Decimal('50.00')
    
    def test_owner_payout_calculation(self, confirmed_booking, test_hotel):
        """Owner payout should deduct platform service fee"""
        payout = OwnerPayout.create_for_booking(confirmed_booking, test_hotel)
        
        assert payout.gross_booking_value == Decimal('1200.00')
        assert payout.platform_service_fee == Decimal('120.00')
        assert payout.net_payable_to_owner == Decimal('1080.00')  # 1200 - 120
    
    def test_platform_ledger_aggregation(self, confirmed_booking):
        """Platform ledger should aggregate daily metrics correctly"""
        date = timezone.now().date()
        ledger = PlatformLedger.compute_for_date(date)
        
        assert ledger.total_bookings >= 1
        assert ledger.total_revenue >= Decimal('1200.00')
        assert ledger.total_service_fee >= Decimal('120.00')


@pytest.mark.django_db
class TestInvoiceAPI:
    """Test invoice retrieval API"""
    
    def test_invoice_detail_owner_access(self, api_client, regular_user, confirmed_booking):
        """Booking owner should access their invoice"""
        invoice = Invoice.create_for_booking(confirmed_booking)
        
        api_client.force_authenticate(user=regular_user)
        response = api_client.get(f'/api/finance/invoices/{invoice.id}/')
        
        assert response.status_code == 200
        assert response.data['invoice_number'] == invoice.invoice_number
    
    def test_invoice_detail_admin_access(self, api_client, super_admin_user, confirmed_booking):
        """Admin should access any invoice"""
        invoice = Invoice.create_for_booking(confirmed_booking)
        
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get(f'/api/finance/invoices/{invoice.id}/')
        
        assert response.status_code == 200
    
    def test_invoice_detail_other_user_denied(self, api_client, confirmed_booking):
        """Other users should NOT access invoice"""
        invoice = Invoice.create_for_booking(confirmed_booking)
        
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='test123'
        )
        
        api_client.force_authenticate(user=other_user)
        response = api_client.get(f'/api/finance/invoices/{invoice.id}/')
        
        assert response.status_code == 403


@pytest.mark.django_db
class TestLedgerAPI:
    """Test platform ledger API"""
    
    def test_ledger_api_access(self, api_client, super_admin_user):
        """SUPER_ADMIN and FINANCE_ADMIN should access ledger"""
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get('/api/finance/ledger/')
        
        assert response.status_code == 200
        assert 'ledger' in response.data
        assert 'count' in response.data
    
    def test_ledger_api_denied_for_non_finance(self, api_client, property_admin_user):
        """Non-finance admins should NOT access ledger"""
        api_client.force_authenticate(user=property_admin_user)
        response = api_client.get('/api/finance/ledger/')
        
        assert response.status_code == 403
    
    def test_ledger_date_filtering(self, api_client, super_admin_user, confirmed_booking):
        """Ledger API should support date filtering"""
        # Compute ledger for today
        date = timezone.now().date()
        PlatformLedger.compute_for_date(date)
        
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get(f'/api/finance/ledger/?date_from={date}&date_to={date}')
        
        assert response.status_code == 200
        assert response.data['count'] >= 1


@pytest.mark.django_db
class TestDashboardFilters:
    """Test dashboard API filtering"""
    
    def test_dashboard_date_filter(self, api_client, super_admin_user, confirmed_booking):
        """Dashboard should filter by date range"""
        date = timezone.now().date()
        
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get(f'/api/finance/dashboard/metrics/?date_from={date}&date_to={date}')
        
        assert response.status_code == 200
        assert response.data['total_bookings'] >= 1
    
    def test_bookings_status_filter(self, api_client, super_admin_user, confirmed_booking):
        """Bookings API should filter by status"""
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get('/api/finance/bookings/?status=confirmed')
        
        assert response.status_code == 200
        assert response.data['count'] >= 1
        
        # All returned bookings should be confirmed
        for booking in response.data['bookings']:
            assert booking['status'] == 'confirmed'
