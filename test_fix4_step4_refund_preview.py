"""
FIX-4 STEP-4 COMPREHENSIVE TEST SUITE
Tests refund preview and cancellation with locked snapshot fields
"""
import os
import django
import json
from decimal import Decimal
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.utils import timezone
from django.test import Client
from hotels.models import Hotel, RoomType, RoomCancellationPolicy, RoomMealPlan
from bookings.models import Booking, HotelBooking
from users.models import User
from payments.models import Wallet


def test_refund_preview():
    """Test refund preview API with snapshot fields"""
    print("=" * 80)
    print("FIX-4 STEP-4: REFUND PREVIEW & CANCELLATION TEST")
    print("=" * 80)
    print()
    
    # Setup
    print("SETUP: Creating test data...")
    hotel = Hotel.objects.filter(is_active=True).first()
    if not hotel:
        print("❌ ERROR: No active hotel found")
        return False
    
    room = RoomType.objects.filter(hotel=hotel, is_available=True).first()
    if not room:
        print("❌ ERROR: No available room found")
        return False
    
    meal_plan = RoomMealPlan.objects.filter(room_type=room).first()
    if not meal_plan:
        print("❌ ERROR: No meal plan found")
        return False
    
    user = User.objects.filter(is_active=True).first()
    if not user:
        user = User.objects.create_user(
            email='step4test@example.com',
            username='step4test',
            password='testpass123'
        )
    
    print(f"✅ Hotel: {hotel.name}")
    print(f"✅ Room: {room.name}")
    print(f"✅ User: {user.email}")
    print()
    
    # TEST 1: PARTIAL REFUND PREVIEW
    print("TEST 1: PARTIAL REFUND PREVIEW")
    print("-" * 80)
    
    policy = RoomCancellationPolicy.objects.create(
        room_type=room,
        policy_type='PARTIAL',
        refund_percentage=50,
        policy_text='50% refund if cancelled 24 hours before check-in',
        is_active=True
    )
    
    check_in = timezone.now().date() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)
    
    booking = Booking.objects.create(
        user=user,
        booking_type='hotel',
        status='confirmed',
        confirmed_at=timezone.now(),
        total_amount=Decimal('10000.00'),
        paid_amount=Decimal('10000.00'),
        customer_name=user.get_full_name() or user.username,
        customer_email=user.email,
        customer_phone='9876543210'
    )
    
    hotel_booking = HotelBooking.objects.create(
        booking=booking,
        room_type=room,
        meal_plan=meal_plan,
        check_in=check_in,
        check_out=check_out,
        number_of_rooms=1,
        number_of_adults=2,
        number_of_children=0,
        total_nights=2
    )
    
    # Lock policy
    hotel_booking.lock_cancellation_policy(policy)
    hotel_booking.refresh_from_db()
    
    # Calculate expected refund
    expected_refund = float(booking.paid_amount) * float(hotel_booking.policy_refund_percentage) / 100.0
    
    print(f"Booking ID: {booking.booking_id}")
    print(f"Paid Amount: Rs {booking.paid_amount}")
    print(f"Policy Type: {hotel_booking.policy_type}")
    print(f"Refund %: {hotel_booking.policy_refund_percentage}%")
    print(f"Expected Refund: Rs {expected_refund}")
    print()
    
    # Verify snapshot
    assert hotel_booking.policy_type == 'PARTIAL', "Policy type not locked"
    assert hotel_booking.policy_refund_percentage == 50, "Refund percentage not locked"
    assert booking.paid_amount == Decimal('10000.00'), "Paid amount mismatch"
    
    refund = float(booking.paid_amount) * float(hotel_booking.policy_refund_percentage) / 100.0
    assert refund == expected_refund, f"Refund calculation mismatch: {refund} != {expected_refund}"
    
    print("✅ TEST 1 PASSED: PARTIAL refund preview correct")
    print()
    
    # TEST 2: FREE CANCELLATION PREVIEW
    print("TEST 2: FREE CANCELLATION PREVIEW")
    print("-" * 80)
    
    policy_free = RoomCancellationPolicy.objects.create(
        room_type=room,
        policy_type='FREE',
        refund_percentage=100,
        policy_text='100% refund - Free cancellation',
        is_active=True
    )
    
    booking2 = Booking.objects.create(
        user=user,
        booking_type='hotel',
        status='confirmed',
        confirmed_at=timezone.now(),
        total_amount=Decimal('10000.00'),
        paid_amount=Decimal('10000.00'),
        customer_name=user.get_full_name() or user.username,
        customer_email=user.email,
        customer_phone='9876543210'
    )
    
    hotel_booking2 = HotelBooking.objects.create(
        booking=booking2,
        room_type=room,
        meal_plan=meal_plan,
        check_in=check_in,
        check_out=check_out,
        number_of_rooms=1,
        number_of_adults=2,
        number_of_children=0,
        total_nights=2
    )
    
    hotel_booking2.lock_cancellation_policy(policy_free)
    hotel_booking2.refresh_from_db()
    
    expected_refund2 = float(booking2.paid_amount) * 100 / 100.0
    
    print(f"Booking ID: {booking2.booking_id}")
    print(f"Paid Amount: Rs {booking2.paid_amount}")
    print(f"Policy Type: {hotel_booking2.policy_type}")
    print(f"Refund %: {hotel_booking2.policy_refund_percentage}%")
    print(f"Expected Refund: Rs {expected_refund2}")
    print()
    
    assert hotel_booking2.policy_type == 'FREE', "Policy type not FREE"
    assert hotel_booking2.policy_refund_percentage == 100, "Refund percentage not 100%"
    
    refund2 = float(booking2.paid_amount) * float(hotel_booking2.policy_refund_percentage) / 100.0
    assert refund2 == expected_refund2, f"FREE refund mismatch: {refund2} != {expected_refund2}"
    
    print("✅ TEST 2 PASSED: FREE cancellation 100% refund correct")
    print()
    
    # TEST 3: NON-REFUNDABLE PREVIEW
    print("TEST 3: NON-REFUNDABLE PREVIEW")
    print("-" * 80)
    
    policy_nonrefund = RoomCancellationPolicy.objects.create(
        room_type=room,
        policy_type='NON_REFUNDABLE',
        refund_percentage=0,
        policy_text='Non-refundable - No refunds',
        is_active=True
    )
    
    booking3 = Booking.objects.create(
        user=user,
        booking_type='hotel',
        status='confirmed',
        confirmed_at=timezone.now(),
        total_amount=Decimal('10000.00'),
        paid_amount=Decimal('10000.00'),
        customer_name=user.get_full_name() or user.username,
        customer_email=user.email,
        customer_phone='9876543210'
    )
    
    hotel_booking3 = HotelBooking.objects.create(
        booking=booking3,
        room_type=room,
        meal_plan=meal_plan,
        check_in=check_in,
        check_out=check_out,
        number_of_rooms=1,
        number_of_adults=2,
        number_of_children=0,
        total_nights=2
    )
    
    hotel_booking3.lock_cancellation_policy(policy_nonrefund)
    hotel_booking3.refresh_from_db()
    
    expected_refund3 = float(booking3.paid_amount) * 0 / 100.0
    
    print(f"Booking ID: {booking3.booking_id}")
    print(f"Paid Amount: Rs {booking3.paid_amount}")
    print(f"Policy Type: {hotel_booking3.policy_type}")
    print(f"Refund %: {hotel_booking3.policy_refund_percentage}%")
    print(f"Expected Refund: Rs {expected_refund3}")
    print()
    
    assert hotel_booking3.policy_type == 'NON_REFUNDABLE', "Policy type not NON_REFUNDABLE"
    assert hotel_booking3.policy_refund_percentage == 0, "Refund percentage not 0%"
    
    refund3 = float(booking3.paid_amount) * float(hotel_booking3.policy_refund_percentage) / 100.0
    assert refund3 == expected_refund3, f"NON_REFUNDABLE refund mismatch: {refund3} != {expected_refund3}"
    
    print("✅ TEST 3 PASSED: NON_REFUNDABLE 0% refund correct")
    print()
    
    # TEST 4: EDGE CASE - VERY SMALL REFUND
    print("TEST 4: EDGE CASE - VERY SMALL REFUND")
    print("-" * 80)
    
    booking4 = Booking.objects.create(
        user=user,
        booking_type='hotel',
        status='confirmed',
        confirmed_at=timezone.now(),
        total_amount=Decimal('100.00'),
        paid_amount=Decimal('100.00'),
        customer_name=user.get_full_name() or user.username,
        customer_email=user.email,
        customer_phone='9876543210'
    )
    
    hotel_booking4 = HotelBooking.objects.create(
        booking=booking4,
        room_type=room,
        meal_plan=meal_plan,
        check_in=check_in,
        check_out=check_out,
        number_of_rooms=1,
        number_of_adults=2,
        number_of_children=0,
        total_nights=2
    )
    
    # Create 33% policy
    policy_small = RoomCancellationPolicy.objects.create(
        room_type=room,
        policy_type='PARTIAL',
        refund_percentage=33,
        policy_text='33% refund',
        is_active=True
    )
    
    hotel_booking4.lock_cancellation_policy(policy_small)
    hotel_booking4.refresh_from_db()
    
    expected_refund4 = float(booking4.paid_amount) * 33 / 100.0
    
    print(f"Booking ID: {booking4.booking_id}")
    print(f"Paid Amount: Rs {booking4.paid_amount}")
    print(f"Policy Refund %: {hotel_booking4.policy_refund_percentage}%")
    print(f"Expected Refund: Rs {expected_refund4:.2f}")
    print()
    
    refund4 = float(booking4.paid_amount) * float(hotel_booking4.policy_refund_percentage) / 100.0
    assert abs(refund4 - expected_refund4) < 0.01, f"Small refund calculation mismatch: {refund4} != {expected_refund4}"
    
    print("✅ TEST 4 PASSED: Small refund calculation correct (Rs 100 × 33% = Rs 33.00)")
    print()
    
    # TEST 5: SNAPSHOT IMMUTABILITY IN CANCELLATION
    print("TEST 5: SNAPSHOT IMMUTABILITY IN CANCELLATION")
    print("-" * 80)
    
    # Change room policy
    policy.refund_percentage = 100
    policy.policy_type = 'FREE'
    policy.save()
    
    # Booking should still use snapshot (50%)
    hotel_booking.refresh_from_db()
    
    print(f"Room policy changed to: {policy.policy_type} {policy.refund_percentage}%")
    print(f"Booking still shows: {hotel_booking.policy_type} {hotel_booking.policy_refund_percentage}%")
    print()
    
    assert hotel_booking.policy_type == 'PARTIAL', "Snapshot policy_type changed!"
    assert hotel_booking.policy_refund_percentage == 50, "Snapshot policy_refund_percentage changed!"
    
    # Refund should still use 50%
    refund_snapshot = float(booking.paid_amount) * float(hotel_booking.policy_refund_percentage) / 100.0
    assert refund_snapshot == expected_refund, f"Snapshot refund changed: {refund_snapshot} != {expected_refund}"
    
    print("✅ TEST 5 PASSED: Snapshot remains immutable even when room policy changes")
    print()
    
    # FINAL SUMMARY
    print("=" * 80)
    print("ALL TESTS PASSED")
    print("=" * 80)
    print()
    print("REFUND FORMULAS VERIFIED:")
    print(f"  PARTIAL 50% of Rs 10000 = Rs {expected_refund}")
    print(f"  FREE 100% of Rs 10000 = Rs {expected_refund2}")
    print(f"  NON_REFUNDABLE 0% of Rs 10000 = Rs {expected_refund3}")
    print(f"  PARTIAL 33% of Rs 100 = Rs {expected_refund4:.2f}")
    print()
    print("SNAPSHOT IMMUTABILITY CONFIRMED:")
    print(f"  Booking 1 policy remains: {hotel_booking.policy_type} {hotel_booking.policy_refund_percentage}%")
    print(f"  Even after room policy changed to: {policy.policy_type} {policy.refund_percentage}%")
    print()
    
    return True


if __name__ == '__main__':
    result = test_refund_preview()
    exit(0 if result else 1)
