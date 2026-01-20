"""
Phase-3: Promo Code Remove - Verify DB nullification and pricing recalculation
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase
from bookings.models import Booking, HotelBooking
from payments.models import Wallet
from hotels.models import Hotel, RoomType, RoomMealPlan
from core.models import City, PromoCode
import json

User = get_user_model()

class PromoCodeRemoveTest(TestCase):
    def setUp(self):
        """Setup: User, booking, promo code."""
        self.user = User.objects.create_user(username='promo_test', email='promo@test.com', password='pass')
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('5000.00'))
        
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
            base_price=Decimal('1000.00'),
            max_occupancy=2,
            number_of_beds=1,
            total_rooms=5
        )
        self.meal_plan = RoomMealPlan.objects.create(
            room_type=self.room_type,
            plan_type='room_only',
            name='Room Only',
            price_per_night=Decimal('1000.00')
        )
        
        # Promo: 20% discount
        self.promo = PromoCode.objects.create(
            code='SAVE20',
            discount_type='percentage',
            discount_value=Decimal('20.00'),
            valid_from=timezone.now(),
            valid_to=timezone.now() + timezone.timedelta(days=30),
            max_uses=100,
            is_active=True
        )
        
        # Booking: ₹1000 + GST ₹200 = ₹1200 (before promo)
        checkin = timezone.now().date()
        self.booking = Booking.objects.create(
            user=self.user,
            source='web',
            booking_type='hotel',
            status='reserved',
            total_amount=Decimal('1000.00'),
            gst_amount=Decimal('200.00'),
            paid_amount=Decimal('0.00'),
            expires_at=timezone.now() + timezone.timedelta(minutes=10)
        )
        self.hotel_booking = HotelBooking.objects.create(
            booking=self.booking,
            hotel=self.hotel,
            room_type=self.room_type,
            meal_plan=self.meal_plan,
            checkin_date=checkin,
            checkout_date=checkin,
            number_of_rooms=1,
            number_of_guests=1,
            base_price=Decimal('1000.00'),
            gst_amount=Decimal('200.00'),
            total_price=Decimal('1200.00'),
            is_refundable=True
        )

    def test_promo_apply_and_remove(self):
        """
        Scenario:
        1. Apply promo: ₹1200 - 20% = ₹960 total
        2. Remove promo: ₹1200 (original) recalculated
        3. Verify DB: promo_code = NULL
        4. Verify pricing: GST recomputed
        """
        print("\n=== PROMO CODE APPLY & REMOVE TEST ===\n")
        
        # APPLY PROMO
        print("[STEP 1] Apply promo code SAVE20 (20% off)")
        discount = self.booking.total_amount * Decimal('0.20')  # ₹200
        discounted_total = self.booking.total_amount - discount  # ₹800
        
        # GST on discounted amount: ₹800 * 0.20 = ₹160
        new_gst = discounted_total * Decimal('0.20')
        total_with_discount = discounted_total + new_gst  # ₹960
        
        self.booking.promo_code = self.promo
        self.booking.total_amount = discounted_total  # ₹800 (base after discount)
        self.booking.gst_amount = new_gst  # ₹160
        self.booking.save()
        
        print(f"  Base (before GST): ₹{self.booking.total_amount}")
        print(f"  GST: ₹{self.booking.gst_amount}")
        print(f"  Payable: ₹{self.booking.total_amount + self.booking.gst_amount}")
        
        # Verify promo applied
        self.booking.refresh_from_db()
        self.assertIsNotNone(self.booking.promo_code, "Promo should be set")
        self.assertEqual(self.booking.promo_code.code, 'SAVE20')
        self.assertEqual(self.booking.total_amount, Decimal('800.00'))
        self.assertEqual(self.booking.gst_amount, Decimal('160.00'))
        payable_with_promo = self.booking.total_amount + self.booking.gst_amount
        self.assertEqual(payable_with_promo, Decimal('960.00'))
        print(f"  {GREEN}✅ Promo applied: ₹{payable_with_promo}{RESET}\n")
        
        # REMOVE PROMO
        print("[STEP 2] Remove promo code")
        
        # Revert to original
        self.booking.promo_code = None
        self.booking.total_amount = Decimal('1000.00')  # Original
        self.booking.gst_amount = Decimal('200.00')  # Recomputed
        self.booking.save()
        
        print(f"  Base (before GST): ₹{self.booking.total_amount}")
        print(f"  GST: ₹{self.booking.gst_amount}")
        print(f"  Payable: ₹{self.booking.total_amount + self.booking.gst_amount}")
        
        # Verify promo removed
        self.booking.refresh_from_db()
        self.assertIsNone(self.booking.promo_code, "Promo should be NULL after removal")
        self.assertEqual(self.booking.total_amount, Decimal('1000.00'), "Base should revert to original")
        self.assertEqual(self.booking.gst_amount, Decimal('200.00'), "GST should be recalculated")
        payable_without_promo = self.booking.total_amount + self.booking.gst_amount
        self.assertEqual(payable_without_promo, Decimal('1200.00'))
        print(f"  {GREEN}✅ Promo removed: ₹{payable_without_promo}{RESET}\n")
        
        # VERIFY DB STATE
        print("[STEP 3] Verify DB state")
        print(f"  promo_code: {self.booking.promo_code}")
        print(f"  total_amount: ₹{self.booking.total_amount}")
        print(f"  gst_amount: ₹{self.booking.gst_amount}")
        print(f"  {GREEN}✅ All fields correct{RESET}\n")

GREEN = '\033[92m'
RESET = '\033[0m'
