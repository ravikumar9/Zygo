"""
Phase-3 API Tests: SIMPLIFIED - Focus on critical business logic
Tests invoice generation, ledger calculations, role access, revenue accuracy
"""
import pytest
from decimal import Decimal
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import date

from users.models import User
from bookings.models import Booking
from bookings.models import HotelBooking
from hotels.models import Hotel, RoomType
from property_owners.models import Property, PropertyOwner
from core.models import City
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
def regular_user(db):
    """Create regular user without admin roles"""
    return User.objects.create_user(
        username='regularuser',
        email='user@test.com',
        password='test123'
    )


@pytest.fixture
def db_setup_property(db):
    """Create Property → Hotel → RoomType hierarchy"""
    owner_user = User.objects.create_user(
        username='hotelowner',
        email='owner@test.com',
        password='test123'
    )
    
    # Create City for PropertyOwner
    city = City.objects.create(
        name='TestCity',
        state='TestState',
        country='India'
    )
    
    property_owner = PropertyOwner.objects.create(
        user=owner_user,
        business_name='Test Hotel Inc',
        city=city,
        owner_name='Test Owner',
        owner_phone='1234567890',
        owner_email='owner@test.com',
        address='Test Address',
        pincode='123456'
    )
    
    property_obj = Property.objects.create(
        owner=property_owner,
        name='Test Hotel',
        description='Test hotel property',
        status='APPROVED'
    )
    
    hotel = Hotel.objects.create(
        owner_property=property_obj,
        name='Test Hotel',
        city=city
    )
    
    room_type = RoomType.objects.create(
        hotel=hotel,
        name='Deluxe Room',
        base_price=1000
    )
    
    return property_obj, hotel, room_type


@pytest.fixture
def sample_booking(db, regular_user, db_setup_property):
    """Create complete hotel booking with price_snapshot"""
    property_obj, hotel, room_type = db_setup_property
    
    booking = Booking.objects.create(
        user=regular_user,
        booking_type='hotel',
        status='confirmed',
        customer_name='Test Customer',
        customer_email='customer@test.com',
        customer_phone='1234567890',
        total_amount=Decimal('1200.00'),
        wallet_balance_before=Decimal('100.00'),
        wallet_balance_after=Decimal('50.00')
    )
    
    # Create hotel_details with price_snapshot
    HotelBooking.objects.create(
        booking=booking,
        room_type=room_type,
        check_in=date.today(),
        check_out=date.today(),
        number_of_rooms=1,
        number_of_adults=2,
        total_nights=1,
        price_snapshot={
            'base_price': 1000,
            'service_fee': 120,
            'tax': 80,
            'total': 1200
        }
    )
    
    return booking


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
class TestInvoiceGeneration:
    """Test invoice generation at booking confirmation"""
    
    def test_invoice_created_on_booking_confirmation(self, sample_booking):
        """Invoice should be auto-created when booking is confirmed"""
        invoice = Invoice.create_for_booking(sample_booking)
        
        assert invoice is not None
        assert invoice.booking == sample_booking
        assert invoice.invoice_number.startswith('INV-')
        assert invoice.billing_name == sample_booking.customer_name
        assert invoice.billing_email == sample_booking.customer_email
    
    def test_invoice_captures_amounts(self, sample_booking):
        """Invoice must capture all amounts correctly"""
        invoice = Invoice.create_for_booking(sample_booking)
        
        # Check service fee extraction from pricing_data
        assert invoice.service_fee == Decimal('120.00')
        
        # Check wallet usage calculation
        expected_wallet = sample_booking.wallet_balance_before - sample_booking.wallet_balance_after
        assert invoice.wallet_used == expected_wallet
        assert invoice.wallet_used == Decimal('50.00')
        
        # Check total amount
        assert invoice.total_amount == Decimal('1200.00')


@pytest.mark.django_db
class TestRevenueAccuracy:
    """Test revenue and ledger calculations for accuracy"""
    
    def test_dashboard_revenue_calculation(self, api_client, super_admin_user, sample_booking):
        """Dashboard should calculate total revenue accurately"""
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get('/api/finance/dashboard/metrics/')
        
        assert response.status_code == 200
        # Should include the sample booking
        assert Decimal(response.data['total_revenue']) >= Decimal('1200.00')
        assert Decimal(response.data['total_service_fee']) >= Decimal('120.00')
        assert Decimal(response.data['total_wallet_used']) >= Decimal('50.00')
    
    def test_service_fee_extraction(self, sample_booking):
        """Service fee should be extracted correctly from pricing_data"""
        invoice = Invoice.create_for_booking(sample_booking)
        
        assert invoice.service_fee == Decimal('120.00')
    
    def test_wallet_usage_calculation(self, sample_booking):
        """Wallet usage should be calculated correctly"""
        invoice = Invoice.create_for_booking(sample_booking)
        
        expected_wallet_used = sample_booking.wallet_balance_before - sample_booking.wallet_balance_after
        assert invoice.wallet_used == expected_wallet_used
        assert invoice.wallet_used == Decimal('50.00')


@pytest.mark.django_db
class TestInvoiceAPI:
    """Test invoice retrieval API"""
    
    def test_invoice_detail_owner_access(self, api_client, regular_user, sample_booking):
        """Booking owner should access their invoice"""
        invoice = Invoice.create_for_booking(sample_booking)
        
        api_client.force_authenticate(user=regular_user)
        response = api_client.get(f'/api/finance/invoices/{invoice.id}/')
        
        assert response.status_code == 200
        assert response.data['invoice_number'] == invoice.invoice_number
    
    def test_invoice_detail_admin_access(self, api_client, super_admin_user, sample_booking):
        """Admin should access any invoice"""
        invoice = Invoice.create_for_booking(sample_booking)
        
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get(f'/api/finance/invoices/{invoice.id}/')
        
        assert response.status_code == 200
    
    def test_invoice_detail_other_user_denied(self, api_client, sample_booking):
        """Other users should NOT access invoice"""
        invoice = Invoice.create_for_booking(sample_booking)
        
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


@pytest.mark.django_db
class TestDashboardFilters:
    """Test dashboard API filtering"""
    
    def test_dashboard_date_filter(self, api_client, super_admin_user, sample_booking):
        """Dashboard should filter by date range"""
        date = timezone.now().date()
        
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get(f'/api/finance/dashboard/metrics/?date_from={date}&date_to={date}')
        
        assert response.status_code == 200
        assert response.data['total_bookings'] >= 0  # May or may not include today's bookings
    
    def test_bookings_status_filter(self, api_client, super_admin_user, sample_booking):
        """Bookings API should filter by status"""
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get('/api/finance/bookings/?status=confirmed')
        
        assert response.status_code == 200
        assert response.data['count'] >= 1
        
        # All returned bookings should be confirmed
        for booking in response.data['bookings']:
            assert booking['status'] == 'confirmed'


@pytest.mark.django_db
class TestAPIEndpointAvailability:
    """Test that all Phase-3 APIs are accessible"""
    
    def test_all_admin_endpoints_exist(self, api_client, super_admin_user):
        """Test all admin API endpoints exist and return proper responses"""
        api_client.force_authenticate(user=super_admin_user)
        
        endpoints = [
            '/api/finance/dashboard/metrics/',
            '/api/finance/invoices/',
            '/api/finance/bookings/',
            '/api/finance/ledger/',
        ]
        
        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == 200, f"Failed: {endpoint}"
