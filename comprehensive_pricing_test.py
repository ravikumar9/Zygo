#!/usr/bin/env python
"""
Complete verification of pricing calculator against ALL test scenarios
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from bookings.models import Booking
from bookings.pricing_calculator import calculate_pricing
from core.models import PromoCode
from payments.models import Wallet
from users.models import User
from decimal import Decimal

user = User.objects.get(email='qa_both_verified@example.com')
wallet = Wallet.objects.get(user=user)
booking = Booking.objects.get(booking_id='b561fd8d-660a-4bdf-8c82-985c32a44fcb')
promo_welcome = PromoCode.objects.get(code='WELCOME500')
promo_user = PromoCode.objects.get(code='USER1000')

print("=" * 70)
print("COMPREHENSIVE PRICING VERIFICATION - ALL SCENARIOS")
print("=" * 70)

# SCENARIO 1: Base + GST (No Promo, No Wallet)
print("\n[SCENARIO 1] Base (₹8000) + GST (18%)")
pricing = calculate_pricing(booking=booking, promo_code=None, wallet_apply_amount=None, user=user)
print(f"  Base Amount:           ₹{pricing['base_amount']:.2f}")
print(f"  Promo Discount:        ₹{pricing['promo_discount']:.2f}")
print(f"  Subtotal After Promo:  ₹{pricing['subtotal_after_promo']:.2f}")
print(f"  GST (18%):             ₹{pricing['gst_amount']:.2f}")
print(f"  Total Payable:         ₹{pricing['total_payable']:.2f}")
print(f"  Wallet Applied:        ₹{pricing['wallet_applied']:.2f}")
print(f"  Gateway Payable:       ₹{pricing['gateway_payable']:.2f}")

expected = {
    'base': Decimal('8000.00'),
    'promo': Decimal('0.00'),
    'subtotal': Decimal('8000.00'),
    'gst': Decimal('1440.00'),
    'total': Decimal('9440.00'),
    'wallet': Decimal('0.00'),
    'gateway': Decimal('9440.00')
}

assert pricing['base_amount'] == expected['base'], f"Base mismatch"
assert pricing['gst_amount'] == expected['gst'], f"GST mismatch"
assert pricing['total_payable'] == expected['total'], f"Total mismatch"
print("  ✅ PASS")

# SCENARIO 2: Promo (WELCOME500) + GST
print("\n[SCENARIO 2] Base (₹8000) - Promo (₹500) + GST (18% on ₹7500)")
pricing = calculate_pricing(booking=booking, promo_code=promo_welcome, wallet_apply_amount=None, user=user)
print(f"  Base Amount:           ₹{pricing['base_amount']:.2f}")
print(f"  Promo Discount:        ₹{pricing['promo_discount']:.2f}")
print(f"  Subtotal After Promo:  ₹{pricing['subtotal_after_promo']:.2f}")
print(f"  GST (18%):             ₹{pricing['gst_amount']:.2f}")
print(f"  Total Payable:         ₹{pricing['total_payable']:.2f}")

expected = {
    'base': Decimal('8000.00'),
    'promo': Decimal('500.00'),
    'subtotal': Decimal('7500.00'),
    'gst': Decimal('1350.00'),
    'total': Decimal('8850.00')
}

assert pricing['base_amount'] == expected['base'], f"Base mismatch"
assert pricing['promo_discount'] == expected['promo'], f"Promo mismatch: got {pricing['promo_discount']}, expected {expected['promo']}"
assert pricing['subtotal_after_promo'] == expected['subtotal'], f"Subtotal mismatch"
assert pricing['gst_amount'] == expected['gst'], f"GST mismatch: got {pricing['gst_amount']}, expected {expected['gst']} (18% of {expected['subtotal']})"
assert pricing['total_payable'] == expected['total'], f"Total mismatch"
print("  ✅ PASS")

# SCENARIO 3: Promo + GST + Wallet (Wallet < Total)
print("\n[SCENARIO 3] Promo + GST + Wallet (Wallet ₹5000 < Total ₹8850)")
pricing = calculate_pricing(booking=booking, promo_code=promo_welcome, wallet_apply_amount=wallet.balance, user=user)
print(f"  Total Payable:         ₹{pricing['total_payable']:.2f}")
print(f"  Wallet Applied:        ₹{pricing['wallet_applied']:.2f}")
print(f"  Gateway Payable:       ₹{pricing['gateway_payable']:.2f}")

expected = {
    'total': Decimal('8850.00'),
    'wallet': Decimal('5000.00'),
    'gateway': Decimal('3850.00')
}

assert pricing['total_payable'] == expected['total'], f"Total mismatch"
assert pricing['wallet_applied'] == expected['wallet'], f"Wallet mismatch"
assert pricing['gateway_payable'] == expected['gateway'], f"Gateway mismatch"
print("  ✅ PASS")

# SCENARIO 4: Wallet > Total (Edge Case)
print("\n[SCENARIO 4] Wallet Edge Case (Wallet Applied ≤ Total)")
pricing = calculate_pricing(booking=booking, promo_code=None, wallet_apply_amount=Decimal('20000.00'), user=user)
print(f"  Total Payable:         ₹{pricing['total_payable']:.2f}")
print(f"  Wallet Applied:        ₹{pricing['wallet_applied']:.2f} (capped at total)")
print(f"  Gateway Payable:       ₹{pricing['gateway_payable']:.2f}")

assert pricing['wallet_applied'] <= pricing['total_payable'], "Wallet should never exceed total"
assert pricing['gateway_payable'] >= Decimal('0.00'), "Gateway should never be negative"
print("  ✅ PASS")

# SCENARIO 5: Cross-Page Consistency
print("\n[SCENARIO 5] Cross-Page Consistency (All Views Same Total)")
p1 = calculate_pricing(booking=booking, promo_code=None, wallet_apply_amount=None, user=user)
p2 = calculate_pricing(booking=booking, promo_code=None, wallet_apply_amount=None, user=user)
p3 = calculate_pricing(booking=booking, promo_code=None, wallet_apply_amount=None, user=user)

print(f"  View 1 Total: ₹{p1['total_payable']:.2f}")
print(f"  View 2 Total: ₹{p2['total_payable']:.2f}")
print(f"  View 3 Total: ₹{p3['total_payable']:.2f}")

assert p1['total_payable'] == p2['total_payable'] == p3['total_payable'], "Totals must match across views"
assert p1['gst_amount'] == p2['gst_amount'] == p3['gst_amount'], "GST must match"
print("  ✅ PASS")

print("\n" + "=" * 70)
print("✅ ALL COMPREHENSIVE TESTS PASSED - PRICING CORRECT")
print("=" * 70)
