"""
Phase-3: Timer Persistence - Verify DB-driven countdown across navigation
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase, Client
from bookings.models import Booking, HotelBooking
from hotels.models import Hotel, RoomType, RoomMealPlan
from core.models import City
import time
import logging

User = get_user_model()
logger = logging.getLogger('phase3_timer')

class TimerPersistenceTest(TestCase):
    def setUp(self):
        """Setup: User with booking and 10-min reservation."""
        self.user = User.objects.create_user(username='timer_test', email='timer@test.com', password='pass123')
        self.client = Client()
        self.client.login(username='timer_test', password='pass123')
        
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
        
        # Booking with 10-minute (600s) reservation
        checkin = timezone.now().date()
        self.booking = Booking.objects.create(
            user=self.user,
            source='web',
            booking_type='hotel',
            status='reserved',
            total_amount=Decimal('2000.00'),
            gst_amount=Decimal('500.00'),
            paid_amount=Decimal('0.00'),
            expires_at=timezone.now() + timezone.timedelta(seconds=600)  # 10 min
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
            base_price=Decimal('1500.00'),
            gst_amount=Decimal('500.00'),
            total_price=Decimal('2000.00'),
            is_refundable=True
        )

    def test_timer_persists_across_page_loads(self):
        """
        Scenario:
        1. Check timer on review page: ~600s
        2. Wait 5 seconds
        3. Check timer on payment page: ~595s (NOT reset to 600)
        4. Verify timer property calculates from DB expires_at
        """
        print("\n=== TIMER PERSISTENCE TEST ===\n")
        
        # LOAD 1: Review page
        print("[LOAD 1] Review page")
        self.booking.refresh_from_db()
        timer_1 = self.booking.reservation_seconds_left
        expires_at_1 = self.booking.expires_at
        print(f"  Expires at: {expires_at_1}")
        print(f"  Timer seconds left: {timer_1}s")
        logger.info(f"[TIMER_DB_VALUE] booking_id={self.booking.id} seconds_left={timer_1} expires_at={expires_at_1}")
        
        # Should be ~600s
        self.assertGreater(timer_1, 590, "Timer should be close to 600s")
        self.assertLessEqual(timer_1, 600, "Timer should not exceed 600s")
        print(f"  {GREEN}✅ Timer within expected range (590-600s){RESET}\n")
        
        # WAIT 5 seconds
        print("[WAIT] Pause 5 seconds (simulating page navigation)")
        time.sleep(5)
        
        # LOAD 2: Payment page (same booking, DB refresh)
        print("[LOAD 2] Payment page (refreshed from DB)")
        self.booking.refresh_from_db()
        timer_2 = self.booking.reservation_seconds_left
        expires_at_2 = self.booking.expires_at
        print(f"  Expires at: {expires_at_2}")
        print(f"  Timer seconds left: {timer_2}s")
        logger.info(f"[TIMER_DB_VALUE] booking_id={self.booking.id} seconds_left={timer_2} expires_at={expires_at_2}")
        
        # Should be ~595s (5s less than before)
        self.assertGreater(timer_2, 585, "Timer should decrease (~595s)")
        self.assertLess(timer_2, timer_1, "Timer must be less than first read")
        print(f"  {GREEN}✅ Timer decreased correctly (from {timer_1}s to {timer_2}s){RESET}\n")
        
        # VERIFY: Expires_at unchanged (DB storage works)
        print("[VERIFY] expires_at field unchanged")
        self.assertEqual(expires_at_1, expires_at_2, "expires_at should not change")
        print(f"  Expires at (stored): {expires_at_1}")
        print(f"  {GREEN}✅ expires_at stored correctly in DB{RESET}\n")
        
        # VERIFY: Timer property recalculates (DB-driven)
        print("[VERIFY] Timer property recalculates from DB")
        delta = timer_1 - timer_2
        print(f"  Timer decrease: {delta}s (expected ~5s)")
        self.assertGreaterEqual(delta, 4, "Should decrease by at least 4s")
        self.assertLessEqual(delta, 6, "Should decrease by at most 6s")
        print(f"  {GREEN}✅ Timer property correctly recalculated{RESET}\n")
        
        print(f"{GREEN}✅ TIMER PERSISTENCE: ALL CHECKS PASSED{RESET}\n")

GREEN = '\033[92m'
RESET = '\033[0m'
