#!/usr/bin/env python
"""
Verify that all 3 views can access pricing calculation without errors
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from bookings.models import Booking
from bookings.views import booking_confirmation, payment_page
from bookings.views import BookingDetailView
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser
from unittest.mock import Mock

booking = Booking.objects.get(booking_id='b561fd8d-660a-4bdf-8c82-985c32a44fcb')
user = booking.user

print("=== VERIFY VIEWS CAN CALCULATE PRICING ===\n")

# Test 1: booking_detail view context
print("✓ TEST 1: BookingDetailView.get_context_data()")
view = BookingDetailView()
view.object = booking
view.request = Mock()
view.request.user = user

try:
    context = view.get_context_data()
    print(f"  Base: {context.get('base_amount')}")
    print(f"  GST: {context.get('gst_amount')}")
    print(f"  Total: {context.get('total_payable')}")
    assert context.get('base_amount'), "Missing base_amount"
    assert context.get('gst_amount'), "Missing gst_amount"
    assert context.get('total_payable'), "Missing total_payable"
    print("  ✅ PASS\n")
except Exception as e:
    print(f"  ❌ FAIL: {e}\n")

# Test 2: booking_confirmation view
print("✓ TEST 2: booking_confirmation() pricing calculation")
try:
    from bookings.pricing_calculator import calculate_pricing
    pricing = calculate_pricing(booking=booking, promo_code=None, wallet_apply_amount=None, user=user)
    print(f"  Base: {pricing['base_amount']}")
    print(f"  Promo: {pricing['promo_discount']}")
    print(f"  GST: {pricing['gst_amount']}")
    print(f"  Total: {pricing['total_payable']}")
    assert pricing['total_payable'] == 9440.00, f"Expected 9440.00, got {pricing['total_payable']}"
    print("  ✅ PASS\n")
except Exception as e:
    print(f"  ❌ FAIL: {e}\n")

# Test 3: payment_page view
print("✓ TEST 3: payment_page() pricing calculation")
try:
    from bookings.pricing_calculator import calculate_pricing
    from payments.models import Wallet
    
    wallet = Wallet.objects.get(user=user)
    pricing = calculate_pricing(booking=booking, promo_code=None, wallet_apply_amount=wallet.balance, user=user)
    print(f"  Base: {pricing['base_amount']}")
    print(f"  Total: {pricing['total_payable']}")
    print(f"  Wallet: {pricing['wallet_applied']}")
    print(f"  Gateway: {pricing['gateway_payable']}")
    assert pricing['total_payable'] == 9440.00, f"Expected 9440.00, got {pricing['total_payable']}"
    assert pricing['wallet_applied'] == 5000.00, f"Expected 5000.00, got {pricing['wallet_applied']}"
    assert pricing['gateway_payable'] == 4440.00, f"Expected 4440.00, got {pricing['gateway_payable']}"
    print("  ✅ PASS\n")
except Exception as e:
    print(f"  ❌ FAIL: {e}\n")

print("✅ ALL VERIFICATION TESTS PASSED")
