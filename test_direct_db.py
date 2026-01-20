"""
ZERO-TOLERANCE DIRECT DATABASE TEST SUITE
Tests core architectural components directly via Django ORM
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
sys.path.insert(0, r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model
from bookings.models import Booking
from hotels.models import Hotel, RoomType, RoomAvailability
from core.models import City
from payments.models import Wallet, WalletTransaction
from bookings.payment_finalization import finalize_booking_payment
from bookings.pricing_calculator import calculate_pricing

User = get_user_model()

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def section(title):
    print(f"\n{Colors.YELLOW}{Colors.BOLD}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Colors.END}\n")

def success(message):
    print(f"{Colors.GREEN}{Colors.BOLD}✅ {message}{Colors.END}")

def error(message):
    print(f"{Colors.RED}{Colors.BOLD}❌ {message}{Colors.END}")

def log(message):
    print(f"{Colors.BLUE}[TEST]{Colors.END} {message}")


def test_1_pricing_single_source():
    """Test that pricing comes from unified calculator"""
    section("TEST 1: Single Source of Truth - Pricing")
    
    # Get/create test data
    city, _ = City.objects.get_or_create(
        name="Test City",
        defaults={'state': 'Test State', 'country': 'India'}
    )
    
    hotel, _ = Hotel.objects.get_or_create(
        name="Test Hotel",
        defaults={
            'description': 'Test',
            'city': city,
            'address': 'Test Address',
            'contact_phone': '9999999999',
            'contact_email': 'test@test.com'
        }
    )
    
    user, _ = User.objects.get_or_create(
        phone='9999888811',
        defaults={'name': 'Test User'}
    )
    
    # Create booking
    check_in = datetime.now().date() + timedelta(days=5)
    check_out = check_in + timedelta(days=2)
    
    booking = Booking.objects.create(
        user=user,
        hotel=hotel,
        check_in_date=check_in,
        check_out_date=check_out,
        guests=2,
        rooms=1,
        room_type='deluxe',
        base_amount=Decimal('2000.00'),
        gst_amount=Decimal('360.00'),
        total_payable=Decimal('2360.00'),
        status='reserved'
    )
    
    log(f"Created Booking ID: {booking.id}")
    log(f"  Base Amount: ₹{booking.base_amount}")
    log(f"  GST Amount: ₹{booking.gst_amount}")
    log(f"  Total Payable: ₹{booking.total_payable}")
    
    # Verify pricing calculator
    pricing = calculate_pricing(booking, None, Decimal('0.00'), user)
    
    log(f"Pricing Calculator Returns:")
    log(f"  Base: ₹{pricing['base_amount']}")
    log(f"  GST: ₹{pricing['gst_amount']}")
    log(f"  Total: ₹{pricing['total_payable']}")
    
    if pricing['total_payable'] != booking.total_payable:
        error(f"Pricing mismatch: {pricing['total_payable']} != {booking.total_payable}")
        return False
    
    success("Pricing calculated from single source ✅")
    return True


def test_2_backend_driven_timer():
    """Test that timer is calculated from DB expires_at"""
    section("TEST 2: Backend-Driven Timer")
    
    # Get latest booking
    booking = Booking.objects.filter(status='reserved').first()
    
    if not booking:
        error("No reserved booking to test")
        return False
    
    log(f"Testing Booking ID: {booking.id}")
    log(f"  Reserved At: {booking.reserved_at}")
    log(f"  Expires At: {booking.expires_at}")
    
    if not booking.expires_at:
        error("expires_at not set")
        return False
    
    # Calculate seconds left
    seconds_left = booking.reservation_seconds_left
    
    log(f"  Seconds Left (from property): {seconds_left}")
    
    if seconds_left is None:
        error("reservation_seconds_left returned None")
        return False
    
    # Verify it's ~10 minutes
    if seconds_left < 550 or seconds_left > 610:
        error(f"Timer should be ~600s (10 min), got {seconds_left}s")
        return False
    
    success(f"Timer backend-driven: {seconds_left}s from DB ✅")
    return True


def test_3_unified_payment_function():
    """Test that unified finalize_booking_payment works"""
    section("TEST 3: Unified Payment Finalization Function")
    
    # Create test booking
    city, _ = City.objects.get_or_create(
        name="Payment Test City",
        defaults={'state': 'Test State', 'country': 'India'}
    )
    
    hotel, _ = Hotel.objects.get_or_create(
        name="Payment Test Hotel",
        defaults={
            'description': 'Test',
            'city': city,
            'address': 'Test Address',
            'contact_phone': '9999999988',
            'contact_email': 'payment@test.com'
        }
    )
    
    user, _ = User.objects.get_or_create(
        phone='9999888822',
        defaults={'name': 'Payment Test User'}
    )
    
    # Ensure wallet exists with funds
    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet.balance = Decimal('5000.00')
    wallet.save()
    
    log(f"Wallet Balance: ₹{wallet.balance}")
    
    # Create booking
    check_in = datetime.now().date() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    
    booking = Booking.objects.create(
        user=user,
        hotel=hotel,
        check_in_date=check_in,
        check_out_date=check_out,
        guests=2,
        rooms=1,
        room_type='standard',
        base_amount=Decimal('1000.00'),
        gst_amount=Decimal('180.00'),
        total_payable=Decimal('1180.00'),
        status='reserved'
    )
    
    log(f"Created Booking ID: {booking.id}")
    log(f"  Total Payable: ₹{booking.total_payable}")
    
    # Test unified payment function
    log("Calling finalize_booking_payment()...")
    
    result = finalize_booking_payment(
        booking=booking,
        payment_mode='wallet',
        wallet_applied=Decimal('1180.00'),
        gateway_amount=Decimal('0.00'),
        gateway_transaction_id='',
        user=user
    )
    
    log(f"Result:")
    log(f"  Status: {result['status']}")
    log(f"  Message: {result['message']}")
    log(f"  New Status: {result['new_status']}")
    log(f"  Wallet Deducted: ₹{result['wallet_deducted']}")
    log(f"  Gateway Charged: ₹{result['gateway_charged']}")
    
    if result['status'] != 'success':
        error(f"Payment failed: {result['message']}")
        return False
    
    if result['new_status'] != 'confirmed':
        error(f"Booking not confirmed: {result['new_status']}")
        return False
    
    # Verify booking status in DB
    booking.refresh_from_db()
    
    if booking.status != 'confirmed':
        error(f"DB status not updated: {booking.status}")
        return False
    
    if not booking.confirmed_at:
        error("confirmed_at not set")
        return False
    
    # Verify wallet deduction
    wallet.refresh_from_db()
    expected_balance = Decimal('5000.00') - Decimal('1180.00')
    
    if wallet.balance != expected_balance:
        error(f"Wallet not deducted correctly: {wallet.balance} != {expected_balance}")
        return False
    
    success(f"Unified payment function works: Booking confirmed, wallet deducted ✅")
    return True


def test_4_inventory_expiry():
    """Test that expiry is set to 10 minutes"""
    section("TEST 4: Inventory Expiry (10 Minutes)")
    
    # Create new booking
    city, _ = City.objects.get_or_create(
        name="Expiry Test City",
        defaults={'state': 'Test State', 'country': 'India'}
    )
    
    hotel, _ = Hotel.objects.get_or_create(
        name="Expiry Test Hotel",
        defaults={
            'description': 'Test',
            'city': city,
            'address': 'Test Address',
            'contact_phone': '9999999977',
            'contact_email': 'expiry@test.com'
        }
    )
    
    user, _ = User.objects.get_or_create(
        phone='9999888833',
        defaults={'name': 'Expiry Test User'}
    )
    
    check_in = datetime.now().date() + timedelta(days=15)
    check_out = check_in + timedelta(days=2)
    
    # Record time before creation
    before = datetime.now()
    
    booking = Booking.objects.create(
        user=user,
        hotel=hotel,
        check_in_date=check_in,
        check_out_date=check_out,
        guests=2,
        rooms=1,
        room_type='deluxe',
        base_amount=Decimal('1500.00'),
        gst_amount=Decimal('270.00'),
        total_payable=Decimal('1770.00'),
        status='reserved'
    )
    
    after = datetime.now()
    
    log(f"Booking Created: ID {booking.id}")
    log(f"  Reserved At: {booking.reserved_at}")
    log(f"  Expires At: {booking.expires_at}")
    
    if not booking.reserved_at:
        error("reserved_at not set")
        return False
    
    if not booking.expires_at:
        error("expires_at not set")
        return False
    
    # Verify expires_at is reserved_at + 10 minutes
    expected_expiry = booking.reserved_at + timedelta(minutes=10)
    
    # Allow 1 second tolerance
    diff = abs((booking.expires_at - expected_expiry).total_seconds())
    
    if diff > 1:
        error(f"Expiry not 10 min: reserved_at + 10 min = {expected_expiry}, got {booking.expires_at}")
        return False
    
    success(f"Expiry correctly set to 10 minutes: {booking.reserved_at} → {booking.expires_at} ✅")
    return True


def test_5_logging_infrastructure():
    """Test that logging tags are in place"""
    section("TEST 5: Comprehensive Logging Infrastructure")
    
    log("Checking logging implementation...")
    
    # Check signals.py
    with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\bookings\signals.py', 'r') as f:
        signals_code = f.read()
    
    required_tags = [
        '[BOOKING_CREATED]',
        '[BOOKING_RESERVED]',
        '[BOOKING_CONFIRMED]',
    ]
    
    missing = []
    for tag in required_tags:
        if tag not in signals_code:
            missing.append(tag)
    
    if missing:
        error(f"Missing logging tags in signals.py: {missing}")
        return False
    
    success(f"Logging tags present in signals.py ✅")
    
    # Check payment finalization
    with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\bookings\payment_finalization.py', 'r') as f:
        payment_code = f.read()
    
    payment_tags = [
        '[PAYMENT_FINALIZE_SUCCESS]',
        '[PAYMENT_FINALIZE_ERROR]',
        '[WALLET_DEDUCTED]',
    ]
    
    missing_payment = []
    for tag in payment_tags:
        if tag not in payment_code:
            missing_payment.append(tag)
    
    if missing_payment:
        error(f"Missing logging tags in payment_finalization.py: {missing_payment}")
        return False
    
    success(f"Logging tags present in payment_finalization.py ✅")
    return True


def test_6_atomic_transactions():
    """Verify atomic transactions are used"""
    section("TEST 6: Atomic Transaction Usage")
    
    log("Checking atomic transaction implementation...")
    
    with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\bookings\payment_finalization.py', 'r') as f:
        code = f.read()
    
    if 'from django.db import transaction' not in code:
        error("Missing transaction import")
        return False
    
    if '@transaction.atomic' not in code and 'with transaction.atomic()' not in code:
        error("Atomic decorator/context manager not used")
        return False
    
    if 'select_for_update()' in code:
        success("Uses select_for_update() for database locking ✅")
    else:
        log("Note: select_for_update() not in payment finalization (may be in channel manager)")
    
    success("Atomic transactions implemented ✅")
    return True


def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔" + "═"*58 + "╗")
    print("║" + " "*58 + "║")
    print("║  ZERO-TOLERANCE DATABASE TEST SUITE".center(58) + "║")
    print("║  Direct ORM Validation".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "═"*58 + "╝")
    print(Colors.END)
    
    tests = [
        ("Single Source Pricing", test_1_pricing_single_source),
        ("Backend-Driven Timer", test_2_backend_driven_timer),
        ("Unified Payment Function", test_3_unified_payment_function),
        ("10-Minute Inventory Expiry", test_4_inventory_expiry),
        ("Comprehensive Logging", test_5_logging_infrastructure),
        ("Atomic Transactions", test_6_atomic_transactions),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            error(f"Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    section("TEST SUMMARY")
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for test_name, passed_flag in results:
        if passed_flag:
            success(f"{test_name}")
        else:
            error(f"{test_name}")
    
    print(f"\n{Colors.BOLD}RESULTS: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED - CORE ARCHITECTURE SOLID{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  FAILURES DETECTED{Colors.END}\n")
        return 1


if __name__ == "__main__":
    exit(main())
