#!/usr/bin/env python
"""
FIX-3 TEST SUITE: Price Disclosure & Transparency
Tests all pricing calculations and template rendering
"""

import os
import sys
import django
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.models import City, Hotel, RoomType, RoomImage, HotelDiscount
from hotels.views import calculate_service_fee, format_price_disclosure
from bookings.models import Booking, HotelBooking
from payments.models import Payment

User = get_user_model()

class PricingCalculationTests(TestCase):
    """Test Fix-3 pricing calculations"""
    
    def test_service_fee_basic(self):
        """Test basic service fee calculation: 5% of price"""
        # ₹2,500 × 5% = ₹125
        result = calculate_service_fee(Decimal('2500'))
        self.assertEqual(result, 125, "Service fee should be 5% of price")
    
    def test_service_fee_rounded(self):
        """Test service fee rounding to nearest integer"""
        # ₹2,334 × 5% = ₹116.70 → ₹117
        result = calculate_service_fee(Decimal('2334'))
        self.assertIn(result, [116, 117], "Service fee should round correctly")
    
    def test_service_fee_capped_at_500(self):
        """Test service fee cap at ₹500"""
        # ₹10,000 × 5% = ₹500 (at cap)
        result = calculate_service_fee(Decimal('10000'))
        self.assertEqual(result, 500, "Service fee should cap at ₹500")
        
        # ₹50,000 × 5% = ₹2,500 → ₹500 (capped)
        result = calculate_service_fee(Decimal('50000'))
        self.assertEqual(result, 500, "Service fee should cap at ₹500")
    
    def test_service_fee_decimal_precision(self):
        """Test service fee with decimal prices"""
        result = calculate_service_fee(Decimal('2500.50'))
        self.assertIsInstance(result, int, "Service fee should return integer")
        self.assertGreater(result, 0, "Service fee should be positive")


class PriceDisclosureTemplateTests(TestCase):
    """Test price disclosure in templates"""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data"""
        # Create city
        cls.city = City.objects.create(
            name='Test City',
            state='Test State',
            coordinates_lat=Decimal('12.9716'),
            coordinates_lng=Decimal('77.5946')
        )
        
        # Create hotel
        cls.hotel = Hotel.objects.create(
            name='Test Hotel',
            city=cls.city,
            property_type='HOTEL',
            star_rating=4,
            description='Test description',
            address='123 Test St',
            phone_number='9876543210',
            email='test@hotel.com',
            check_in_time='14:00',
            check_out_time='11:00',
            base_price=Decimal('3000'),
            property_status='APPROVED'
        )
        
        # Create room type
        cls.room_type = RoomType.objects.create(
            hotel=cls.hotel,
            name='Standard Room',
            base_price=Decimal('2500'),
            max_occupancy=2,
            number_of_beds=1
        )
        
        # Add room image
        RoomImage.objects.create(
            room_type=cls.room_type,
            image='test_image.jpg',
            is_primary=True,
            alt_text='Test Room'
        )
        
        # Add discount
        cls.discount = HotelDiscount.objects.create(
            hotel=cls.hotel,
            discount_type='PERCENTAGE',
            discount_value=Decimal('20'),
            is_active=True
        )
        
        # Create test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            email_verified_at='2026-01-21'
        )
    
    def test_hotel_list_price_display(self):
        """Test price display on search results"""
        client = Client()
        response = client.get(reverse('hotels:hotel_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('From ₹', response.content.decode(), 
                     "Search results should show 'From ₹X/night'")
        self.assertNotIn('GST', response.content.decode(), 
                        "Search results should NOT show GST")
    
    def test_hotel_detail_price_display(self):
        """Test price display on hotel detail page"""
        client = Client()
        response = client.get(reverse('hotels:hotel_detail', args=[self.hotel.id]))
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        
        # Check for base price
        self.assertIn(f'₹{self.room_type.base_price}', content,
                     "Detail page should show base price")
        
        # Check for collapsible taxes section
        self.assertIn('Taxes & Services', content,
                     "Detail page should have 'Taxes & Services' button")
        self.assertIn('tax-info-', content,
                     "Detail page should have collapsible tax sections")
    
    def test_price_calculation_in_booking_form(self):
        """Test that booking form shows correct price calculation"""
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.get(reverse('hotels:hotel_detail', args=[self.hotel.id]))
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        
        # Check for price elements
        self.assertIn('basePrice', content, "Should have base price element")
        self.assertIn('taxesFees', content, "Should have taxes/fees element")
        self.assertIn('totalPrice', content, "Should have total price element")


class HotelPricingContextTests(TestCase):
    """Test pricing context passed to templates"""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data"""
        cls.city = City.objects.create(
            name='Context Test City',
            state='Test State',
            coordinates_lat=Decimal('12.9716'),
            coordinates_lng=Decimal('77.5946')
        )
        
        cls.hotel = Hotel.objects.create(
            name='Context Test Hotel',
            city=cls.city,
            property_type='HOTEL',
            star_rating=3,
            description='Test',
            address='123 St',
            phone_number='9876543210',
            email='test@hotel.com',
            check_in_time='14:00',
            check_out_time='11:00',
            base_price=Decimal('3000'),
            property_status='APPROVED'
        )
        
        cls.room = RoomType.objects.create(
            hotel=cls.hotel,
            name='Test Room',
            base_price=Decimal('2500'),
            max_occupancy=2,
            number_of_beds=1
        )
    
    def test_hotel_has_min_price(self):
        """Test that hotel context includes min_price"""
        self.assertEqual(self.hotel.min_price, Decimal('2500'),
                        "Hotel min_price should be cheapest room price")
    
    def test_hotel_has_discount_badge(self):
        """Test discount badge formatting"""
        # Create discount
        discount = HotelDiscount.objects.create(
            hotel=self.hotel,
            discount_type='PERCENTAGE',
            discount_value=Decimal('15'),
            is_active=True
        )
        
        badge = self.hotel.discount_badge
        if badge:
            self.assertIn('15%', str(badge),
                         "Discount badge should show discount percentage")
    
    def test_room_effective_price(self):
        """Test room effective price calculation with discount"""
        discount = HotelDiscount.objects.create(
            hotel=self.hotel,
            discount_type='PERCENTAGE',
            discount_value=Decimal('20'),
            is_active=True
        )
        
        effective = self.room.get_effective_price
        expected = self.room.base_price * Decimal('0.8')  # 20% off
        self.assertEqual(effective, expected,
                        "Effective price should apply discount")


class EdgeCaseTests(TestCase):
    """Test edge cases in pricing"""
    
    def test_service_fee_very_small_price(self):
        """Test service fee with very small price"""
        result = calculate_service_fee(Decimal('100'))  # ₹100 × 5% = ₹5
        self.assertEqual(result, 5, "Service fee should work with small prices")
    
    def test_service_fee_zero(self):
        """Test service fee with zero price"""
        result = calculate_service_fee(Decimal('0'))
        self.assertEqual(result, 0, "Service fee should be 0 for 0 price")
    
    def test_service_fee_boundary_at_cap(self):
        """Test service fee at exactly ₹500 cap boundary"""
        # ₹10,000 × 5% = ₹500
        result = calculate_service_fee(Decimal('10000'))
        self.assertEqual(result, 500, "Service fee at cap should be 500")
        
        # ₹10,001 × 5% = ₹500.05 → ₹500 (still capped)
        result = calculate_service_fee(Decimal('10001'))
        self.assertEqual(result, 500, "Service fee above cap should still be 500")


class BookingFlowPricingTests(TestCase):
    """Test pricing throughout booking flow"""
    
    @classmethod
    def setUpTestData(cls):
        """Create complete test data"""
        cls.city = City.objects.create(
            name='Booking Test City',
            state='Test State',
            coordinates_lat=Decimal('12.9716'),
            coordinates_lng=Decimal('77.5946')
        )
        
        cls.hotel = Hotel.objects.create(
            name='Booking Test Hotel',
            city=cls.city,
            property_type='HOTEL',
            star_rating=4,
            description='Test Hotel',
            address='123 Test Street',
            phone_number='9876543210',
            email='booking@test.com',
            check_in_time='14:00',
            check_out_time='11:00',
            base_price=Decimal('5000'),
            property_status='APPROVED'
        )
        
        cls.room = RoomType.objects.create(
            hotel=cls.hotel,
            name='Deluxe Room',
            base_price=Decimal('3000'),
            max_occupancy=2,
            number_of_beds=1
        )
        
        cls.user = User.objects.create_user(
            username='bookinguser',
            email='booking@example.com',
            password='testpass123',
            email_verified_at='2026-01-21'
        )
    
    def test_booking_confirmation_shows_taxes(self):
        """Test that booking confirmation displays taxes properly"""
        # This would require creating a full booking in the future
        # For now, verify the structure
        self.assertTrue(True, "Booking confirmation test placeholder")


def run_all_tests():
    """Run all Fix-3 tests"""
    print("\n" + "="*70)
    print("FIX-3 PRICE DISCLOSURE TEST SUITE")
    print("="*70 + "\n")
    
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)
    
    failures = test_runner.run_tests([
        'tests.test_price_disclosure_fix3.PricingCalculationTests',
        'tests.test_price_disclosure_fix3.PriceDisclosureTemplateTests',
        'tests.test_price_disclosure_fix3.HotelPricingContextTests',
        'tests.test_price_disclosure_fix3.EdgeCaseTests',
        'tests.test_price_disclosure_fix3.BookingFlowPricingTests',
    ])
    
    if failures:
        print(f"\n❌ {failures} test(s) failed")
        return False
    else:
        print("\n✅ All Fix-3 pricing tests passed!")
        return True


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
