"""
FIX-4 IMMUTABILITY PROOF TEST
Tests that changing room policy AFTER booking does NOT affect existing bookings.
"""
import os
import django
import json
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from hotels.models import Hotel, RoomType, RoomCancellationPolicy, RoomMealPlan
from bookings.models import Booking, HotelBooking
from users.models import User


def test_immutability():
    print("=" * 80)
    print("FIX-4 IMMUTABILITY PROOF TEST")
    print("=" * 80)
    print()
    
    # Step 1: Get test data
    print("STEP 1: Getting test hotel and room...")
    hotel = Hotel.objects.filter(is_active=True).first()
    if not hotel:
        print("❌ ERROR: No active hotel found. Run seed_comprehensive_data.py first.")
        return
    
    room = RoomType.objects.filter(hotel=hotel, is_available=True).first()
    if not room:
        print("❌ ERROR: No available room found. Run seed_comprehensive_data.py first.")
        return
    
    print(f"✅ Hotel: {hotel.name}")
    print(f"✅ Room: {room.name}")
    print()
    
    # Step 2: Create initial 50% PARTIAL policy
    print("STEP 2: Creating PARTIAL (50%) cancellation policy...")
    policy_partial = RoomCancellationPolicy.objects.create(
        room_type=room,
        policy_type='PARTIAL',
        refund_percentage=50,
        policy_text='50% refund if cancelled 24 hours before check-in',
        is_active=True
    )
    print(f"✅ Created policy ID: {policy_partial.id}")
    print(f"   Type: {policy_partial.policy_type}")
    print(f"   Refund: {policy_partial.refund_percentage}%")
    print()
    
    # Step 3: Create booking with this policy
    print("STEP 3: Creating booking with 50% policy...")
    user = User.objects.filter(is_active=True).first()
    if not user:
        user = User.objects.create_user(
            email='testimmutability@example.com',
            username='testimmutability',
            password='testpass123',
            first_name='Immutability',
            last_name='Test User'
        )
    
    customer_name = user.get_full_name() or user.username
    
    meal_plan = RoomMealPlan.objects.filter(room_type=room).first()
    if not meal_plan:
        print("❌ ERROR: No meal plan found. Run seed_comprehensive_data.py first.")
        return
    
    check_in = timezone.now().date() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)
    
    booking = Booking.objects.create(
        user=user,
        booking_type='hotel',
        status='confirmed',
        confirmed_at=timezone.now(),
        total_amount=Decimal('6000.00'),
        paid_amount=Decimal('6000.00'),
        customer_name=customer_name,
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
    
    # Lock the policy snapshot
    hotel_booking.lock_cancellation_policy(policy_partial)
    hotel_booking.refresh_from_db()
    
    print(f"✅ Booking created: {booking.booking_id}")
    print(f"   Policy locked at: {hotel_booking.policy_locked_at}")
    print(f"   Policy type: {hotel_booking.policy_type}")
    print(f"   Refund %: {hotel_booking.policy_refund_percentage}%")
    print(f"   Total paid: Rs {booking.paid_amount}")
    print(f"   Expected refund: Rs {float(booking.paid_amount) * hotel_booking.policy_refund_percentage / 100}")
    print()
    
    # Step 4: Capture BEFORE state
    print("STEP 4: Capturing BEFORE state...")
    before_state = {
        'booking_id': str(booking.booking_id),
        'policy_type': hotel_booking.policy_type,
        'policy_refund_percentage': hotel_booking.policy_refund_percentage,
        'policy_text': hotel_booking.policy_text,
        'policy_locked_at': str(hotel_booking.policy_locked_at),
        'paid_amount': float(booking.paid_amount),
        'expected_refund': float(booking.paid_amount) * hotel_booking.policy_refund_percentage / 100
    }
    
    print("BEFORE STATE:")
    print(json.dumps(before_state, indent=2))
    print()
    
    # Step 5: Change room policy to 100% FREE
    print("STEP 5: Changing room policy to FREE (100%)...")
    policy_free = RoomCancellationPolicy.objects.create(
        room_type=room,
        policy_type='FREE',
        refund_percentage=100,
        policy_text='100% refund if cancelled anytime',
        is_active=True
    )
    
    # Deactivate old policy
    policy_partial.is_active = False
    policy_partial.save()
    
    print(f"✅ New policy created: {policy_free.policy_type} {policy_free.refund_percentage}%")
    print(f"✅ Old policy deactivated")
    print()
    
    # Step 6: Refresh booking and check if it changed
    print("STEP 6: Checking if existing booking changed...")
    hotel_booking.refresh_from_db()
    booking.refresh_from_db()
    
    after_state = {
        'booking_id': str(booking.booking_id),
        'policy_type': hotel_booking.policy_type,
        'policy_refund_percentage': hotel_booking.policy_refund_percentage,
        'policy_text': hotel_booking.policy_text,
        'policy_locked_at': str(hotel_booking.policy_locked_at),
        'paid_amount': float(booking.paid_amount),
        'expected_refund': float(booking.paid_amount) * hotel_booking.policy_refund_percentage / 100
    }
    
    print("AFTER STATE:")
    print(json.dumps(after_state, indent=2))
    print()
    
    # Step 7: Compare states
    print("STEP 7: Comparing BEFORE vs AFTER...")
    print("-" * 80)
    
    immutable = True
    
    if before_state['policy_type'] == after_state['policy_type']:
        print(f"✅ Policy Type: {before_state['policy_type']} → {after_state['policy_type']} (UNCHANGED)")
    else:
        print(f"❌ Policy Type: {before_state['policy_type']} → {after_state['policy_type']} (CHANGED!)")
        immutable = False
    
    if before_state['policy_refund_percentage'] == after_state['policy_refund_percentage']:
        print(f"✅ Refund %: {before_state['policy_refund_percentage']}% → {after_state['policy_refund_percentage']}% (UNCHANGED)")
    else:
        print(f"❌ Refund %: {before_state['policy_refund_percentage']}% → {after_state['policy_refund_percentage']}% (CHANGED!)")
        immutable = False
    
    if before_state['expected_refund'] == after_state['expected_refund']:
        print(f"✅ Expected Refund: Rs {before_state['expected_refund']} → Rs {after_state['expected_refund']} (UNCHANGED)")
    else:
        print(f"❌ Expected Refund: Rs {before_state['expected_refund']} → Rs {after_state['expected_refund']} (CHANGED!)")
        immutable = False
    
    if before_state['policy_locked_at'] == after_state['policy_locked_at']:
        print(f"✅ Policy Locked At: {before_state['policy_locked_at']} (UNCHANGED)")
    else:
        print(f"❌ Policy Locked At: {before_state['policy_locked_at']} → {after_state['policy_locked_at']} (CHANGED!)")
        immutable = False
    
    print("-" * 80)
    print()
    
    # Step 8: Final verdict
    print("=" * 80)
    if immutable:
        print("✅ IMMUTABILITY CONFIRMED")
        print("   Booking policy snapshot is LOCKED and IMMUTABLE")
        print("   Changing room policy does NOT affect existing bookings")
        print()
        print("PROOF:")
        print(f"   1. Room policy changed from PARTIAL 50% to FREE 100%")
        print(f"   2. Existing booking STILL shows PARTIAL 50%")
        print(f"   3. Refund calculation STILL uses 50% (Rs {after_state['expected_refund']})")
        print(f"   4. Policy locked timestamp UNCHANGED")
    else:
        print("❌ IMMUTABILITY VIOLATION DETECTED!")
        print("   Booking policy changed after locking - THIS IS A BUG!")
    
    print("=" * 80)
    print()
    
    # Step 9: Database proof
    print("DATABASE PROOF:")
    print("-" * 80)
    print(f"Booking ID: {booking.booking_id}")
    print(f"Hotel Booking ID: {hotel_booking.id}")
    print()
    print("Snapshot Fields:")
    print(f"  policy_type = '{hotel_booking.policy_type}'")
    print(f"  policy_refund_percentage = {hotel_booking.policy_refund_percentage}")
    print(f"  policy_text = '{hotel_booking.policy_text}'")
    print(f"  policy_locked_at = {hotel_booking.policy_locked_at}")
    print()
    print("Refund Formula:")
    print(f"  refund = paid_amount × refund_percentage / 100")
    print(f"  refund = {booking.paid_amount} × {hotel_booking.policy_refund_percentage} / 100")
    print(f"  refund = Rs {float(booking.paid_amount) * hotel_booking.policy_refund_percentage / 100}")
    print("-" * 80)
    print()
    
    return immutable


if __name__ == '__main__':
    result = test_immutability()
    exit(0 if result else 1)
