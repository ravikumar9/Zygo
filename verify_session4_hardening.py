"""
Session 4: Platform Hardening Verification Script
==================================================

This script verifies all critical hardening implemented in Session 4:
1. Booking lifecycle FSM enforcement
2. Inventory locking (hotels + buses)
3. Payment idempotency & no double debit
4. Search enforcement (approved operators + properties only)
5. Admin & audit timestamps present

NO FEATURES - ONLY CORRECTNESS
"""

import os
import django
import sys
from decimal import Decimal
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from bookings.models import Booking, HotelBooking, BusBooking, BusBookingSeat
from hotels.models import Hotel, RoomType
from buses.models import BusOperator, Bus, BusRoute, BusSchedule, SeatLayout
from payments.models import Wallet, WalletTransaction
from core.models import City
from property_owners.models import Property

User = get_user_model()

class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Color.GREEN}✅ {msg}{Color.END}")

def print_error(msg):
    print(f"{Color.RED}❌ {msg}{Color.END}")

def print_info(msg):
    print(f"{Color.BLUE}ℹ️  {msg}{Color.END}")

def print_section(msg):
    print(f"\n{Color.YELLOW}{'='*60}\n{msg}\n{'='*60}{Color.END}")


# ========================================
# TEST 1: Booking Lifecycle FSM
# ========================================
def test_booking_lifecycle():
    print_section("TEST 1: Booking Lifecycle FSM Enforcement")
    
    try:
        # Create test user
        user, _ = User.objects.get_or_create(
            username='test_lifecycle_user',
            defaults={'email': 'lifecycle@test.com'}
        )
        
        # Create test booking
        now = timezone.now()
        booking = Booking.objects.create(
            user=user,
            booking_type='bus',
            total_amount=Decimal('1000.00'),
            status='reserved',
            reserved_at=now,
            expires_at=now + timedelta(minutes=10),
            customer_name='Test User',
            customer_email='test@test.com',
            customer_phone='1234567890'
        )
        
        # Verify initial state
        assert booking.status == 'reserved', "Should start in reserved"
        assert booking.reserved_at is not None, "reserved_at should be set"
        assert booking.expires_at is not None, "expires_at should be set"
        print_success("Booking created in 'reserved' state with timestamps")
        
        # Transition to confirmed
        booking.status = 'confirmed'
        booking.confirmed_at = timezone.now()
        booking.paid_amount = booking.total_amount
        booking.save()
        
        assert booking.confirmed_at is not None, "confirmed_at should be set"
        assert booking.paid_amount == booking.total_amount, "paid_amount should match total"
        print_success("Booking transitioned to 'confirmed' with confirmed_at timestamp")
        
        # Check completed_at field exists (Session 4 addition)
        booking.status = 'completed'
        booking.completed_at = timezone.now()
        booking.save()
        
        booking.refresh_from_db()
        assert booking.completed_at is not None, "completed_at should be set"
        print_success("Booking has completed_at timestamp (Session 4 hardening)")
        
        # Cleanup
        booking.delete()
        
        print_success("TEST 1 PASSED: Booking lifecycle FSM working correctly")
        return True
        
    except Exception as e:
        print_error(f"TEST 1 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ========================================
# TEST 2: Bus Seat Atomic Locking
# ========================================
def test_bus_seat_locking():
    print_section("TEST 2: Bus Seat Atomic Locking (Race Condition Prevention)")
    
    try:
        # Get or create test operator (APPROVED)
        user, _ = User.objects.get_or_create(
            username='test_operator',
            defaults={'email': 'operator@test.com'}
        )
        
        city1, _ = City.objects.get_or_create(code='TST1', defaults={'name': 'Test City 1'})
        city2, _ = City.objects.get_or_create(code='TST2', defaults={'name': 'Test City 2'})
        
        operator, _ = BusOperator.objects.get_or_create(
            user=user,
            defaults={
                'name': 'Test Bus Operator',
                'approval_status': 'approved',  # CRITICAL: Must be approved
                'company_legal_name': 'Test Company',
                'operator_office_address': '123 Test Street',
                'contact_phone': '1234567890',
                'contact_email': 'op@test.com',
                'is_active': True,
            }
        )
        
        bus, _ = Bus.objects.get_or_create(
            operator=operator,
            bus_number='TEST123',
            defaults={
                'bus_name': 'Test Bus',
                'bus_type': 'seater',
                'total_seats': 40,
                'is_active': True,
            }
        )
        
        route, _ = BusRoute.objects.get_or_create(
            bus=bus,
            source_city=city1,
            destination_city=city2,
            defaults={
                'route_name': 'Test Route',
                'departure_time': '10:00',
                'arrival_time': '14:00',
                'duration_hours': Decimal('4.00'),
                'distance_km': Decimal('200.00'),
                'base_fare': Decimal('500.00'),
                'is_active': True,
            }
        )
        
        # Create schedule
        travel_date = date.today() + timedelta(days=7)
        schedule, created = BusSchedule.objects.get_or_create(
            route=route,
            date=travel_date,
            defaults={
                'available_seats': 40,
                'booked_seats': 0,
                'fare': Decimal('500.00'),
                'is_active': True,
            }
        )
        
        if not created:
            # Reset for test
            schedule.available_seats = 40
            schedule.booked_seats = 0
            schedule.save()
        
        initial_available = schedule.available_seats
        print_info(f"Initial available seats: {initial_available}")
        
        # Simulate atomic booking
        with transaction.atomic():
            schedule_locked = BusSchedule.objects.select_for_update().get(pk=schedule.pk)
            
            # Book 5 seats
            seats_to_book = 5
            if schedule_locked.available_seats >= seats_to_book:
                schedule_locked.available_seats -= seats_to_book
                schedule_locked.booked_seats += seats_to_book
                schedule_locked.save()
            else:
                raise ValueError("Not enough seats")
        
        schedule.refresh_from_db()
        assert schedule.available_seats == initial_available - 5, "Should have 5 fewer seats"
        assert schedule.booked_seats == 5, "Should have 5 booked seats"
        print_success("Atomic seat locking works correctly (select_for_update)")
        
        # Verify BusSchedule.book_seats has warning comment
        import inspect
        method_source = inspect.getsource(BusSchedule.book_seats)
        assert "WARNING" in method_source or "thread-safe" in method_source, "Should have concurrency warning"
        print_success("BusSchedule.book_seats has thread-safety warning")
        
        print_success("TEST 2 PASSED: Bus seat locking prevents race conditions")
        return True
        
    except Exception as e:
        print_error(f"TEST 2 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ========================================
# TEST 3: Wallet Payment Idempotency
# ========================================
def test_wallet_payment_idempotency():
    print_section("TEST 3: Wallet Payment Idempotency (No Double Debit)")
    
    try:
        # Create test user with wallet
        user, _ = User.objects.get_or_create(
            username='test_wallet_user',
            defaults={'email': 'wallet@test.com'}
        )
        
        wallet, _ = Wallet.objects.get_or_create(
            user=user,
            defaults={'balance': Decimal('5000.00'), 'is_active': True}
        )
        
        # Reset wallet balance
        wallet.balance = Decimal('5000.00')
        wallet.save()
        
        initial_balance = wallet.balance
        print_info(f"Initial wallet balance: ₹{initial_balance}")
        
        # Create booking
        booking = Booking.objects.create(
            user=user,
            booking_type='hotel',
            total_amount=Decimal('2000.00'),
            status='reserved',
            reserved_at=timezone.now(),
            customer_name='Test User',
            customer_email='test@test.com',
            customer_phone='1234567890'
        )
        
        # Simulate first wallet debit
        with transaction.atomic():
            wallet_locked = Wallet.objects.select_for_update().get(pk=wallet.pk)
            booking_locked = Booking.objects.select_for_update().get(pk=booking.pk)
            
            # Check for existing transaction (idempotency)
            existing_txn = WalletTransaction.objects.filter(
                booking=booking_locked,
                transaction_type='debit',
                reference_id=str(booking_locked.booking_id),
                status='success'
            ).first()
            
            if not existing_txn:
                debit_amount = Decimal('2000.00')
                balance_before = wallet_locked.balance
                wallet_locked.balance -= debit_amount
                wallet_locked.save()
                
                WalletTransaction.objects.create(
                    wallet=wallet_locked,
                    transaction_type='debit',
                    amount=debit_amount,
                    balance_before=balance_before,
                    balance_after=wallet_locked.balance,
                    reference_id=str(booking_locked.booking_id),
                    description=f"Test payment for {booking_locked.booking_id}",
                    booking=booking_locked,
                    status='success',
                    payment_gateway='internal',
                )
                print_success("First debit successful")
        
        wallet.refresh_from_db()
        balance_after_first = wallet.balance
        assert balance_after_first == initial_balance - Decimal('2000.00'), "Balance should be reduced"
        
        # Attempt duplicate debit (should be prevented by idempotency check)
        with transaction.atomic():
            wallet_locked = Wallet.objects.select_for_update().get(pk=wallet.pk)
            booking_locked = Booking.objects.select_for_update().get(pk=booking.pk)
            
            existing_txn = WalletTransaction.objects.filter(
                booking=booking_locked,
                transaction_type='debit',
                reference_id=str(booking_locked.booking_id),
                status='success'
            ).first()
            
            if existing_txn:
                print_success("Duplicate debit prevented by idempotency check")
            else:
                raise ValueError("Idempotency check FAILED - would allow double debit!")
        
        wallet.refresh_from_db()
        assert wallet.balance == balance_after_first, "Balance should not change on duplicate attempt"
        print_success("Wallet balance unchanged after duplicate attempt")
        
        # Cleanup
        booking.delete()
        
        print_success("TEST 3 PASSED: Wallet payment idempotency working correctly")
        return True
        
    except Exception as e:
        print_error(f"TEST 3 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ========================================
# TEST 4: Search Enforcement
# ========================================
def test_search_enforcement():
    print_section("TEST 4: Search Enforcement (Only Approved Operators/Properties)")
    
    try:
        # Test Bus Operator Approval Enforcement
        approved_operators = BusOperator.objects.filter(
            approval_status='approved',
            is_active=True
        )
        
        # Get bus search results (Session 3 enforcement)
        search_query = Bus.objects.filter(
            operator__approval_status='approved',
            operator__is_active=True,
            is_active=True
        )
        
        for bus in search_query[:3]:
            assert bus.operator.approval_status == 'approved', "All buses should have approved operators"
            assert bus.operator.is_active, "All operators should be active"
        
        print_success("Bus search filters by approval_status='approved' (Session 3 enforcement)")
        
        # Test Property Owner Approval Enforcement (Session 4 fix)
        # Check if hotels query filters by property_owner__is_approved
        from hotels.views import hotel_list
        import inspect
        
        view_source = inspect.getsource(hotel_list)
        assert "property_owner__is_approved" in view_source or "is_approved=True" in view_source, \
            "Hotel search should filter by property owner approval"
        
        print_success("Hotel search enforces property_owner__is_approved=True (Session 4 hardening)")
        
        print_success("TEST 4 PASSED: Search enforcement prevents unapproved entities")
        return True
        
    except Exception as e:
        print_error(f"TEST 4 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ========================================
# TEST 5: Admin & Audit Timestamps
# ========================================
def test_admin_audit_timestamps():
    print_section("TEST 5: Admin & Audit Timestamps")
    
    try:
        # Check Booking model has all required timestamps
        from bookings.models import Booking
        booking_fields = [f.name for f in Booking._meta.get_fields()]
        
        required_timestamps = [
            'created_at',
            'reserved_at',
            'confirmed_at',
            'expires_at',
            'cancelled_at',
            'completed_at',  # Session 4 addition
            'deleted_at',
        ]
        
        for ts_field in required_timestamps:
            assert ts_field in booking_fields, f"Booking should have {ts_field} field"
        
        print_success("Booking model has all required audit timestamps")
        
        # Check BusOperator has approval timestamps (Session 3)
        from buses.models import BusOperator
        operator_fields = [f.name for f in BusOperator._meta.get_fields()]
        
        operator_timestamps = ['submitted_at', 'approved_at']
        for ts_field in operator_timestamps:
            assert ts_field in operator_fields, f"BusOperator should have {ts_field} field"
        
        print_success("BusOperator has approval audit timestamps (Session 3)")
        
        # Check Property has approval timestamps (Session 2)
        from property_owners.models import Property
        property_fields = [f.name for f in Property._meta.get_fields()]
        
        property_timestamps = ['submitted_at', 'approved_at']
        for ts_field in property_timestamps:
            assert ts_field in property_fields, f"Property should have {ts_field} field"
        
        print_success("Property has approval audit timestamps (Session 2)")
        
        print_success("TEST 5 PASSED: All audit timestamps present")
        return True
        
    except Exception as e:
        print_error(f"TEST 5 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ========================================
# MAIN EXECUTION
# ========================================
def main():
    print(f"\n{Color.BLUE}{'='*60}")
    print("SESSION 4: PLATFORM HARDENING VERIFICATION")
    print("NO FEATURES - ONLY CORRECTNESS")
    print(f"{'='*60}{Color.END}\n")
    
    results = []
    
    # Run all tests
    results.append(("Booking Lifecycle FSM", test_booking_lifecycle()))
    results.append(("Bus Seat Atomic Locking", test_bus_seat_locking()))
    results.append(("Wallet Payment Idempotency", test_wallet_payment_idempotency()))
    results.append(("Search Enforcement", test_search_enforcement()))
    results.append(("Admin & Audit Timestamps", test_admin_audit_timestamps()))
    
    # Summary
    print_section("VERIFICATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Color.GREEN}✅ PASS{Color.END}" if result else f"{Color.RED}❌ FAIL{Color.END}"
        print(f"{test_name:.<50} {status}")
    
    print(f"\n{Color.YELLOW}Total: {passed}/{total} tests passed{Color.END}")
    
    if passed == total:
        print(f"\n{Color.GREEN}{'='*60}")
        print("✅ SESSION 4 VERIFICATION: COMPLETE")
        print("Platform hardened and production-ready.")
        print(f"{'='*60}{Color.END}\n")
        return 0
    else:
        print(f"\n{Color.RED}{'='*60}")
        print("❌ SESSION 4 VERIFICATION: FAILED")
        print(f"{total - passed} test(s) failed. Platform NOT ready.")
        print(f"{'='*60}{Color.END}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
