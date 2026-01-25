"""Test GST tier calculations"""

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from decimal import Decimal
from bookings.pricing_utils import calculate_hotel_gst, calculate_total_pricing, get_hotel_gst_rate

def test_gst_tiers():
    print("\n" + "="*60)
    print("Testing Hotel GST Tiers")
    print("="*60)
    
    # Test Budget: < ₹7,500 = 0% GST
    print("\n1. Budget Booking (< ₹7,500):")
    base = Decimal('6000.00')
    service_fee = 300  # 5% of 6000
    gst_amount, gst_rate = calculate_hotel_gst(base, service_fee)
    print(f"   Base: ₹{base}")
    print(f"   Service Fee: ₹{service_fee}")
    print(f"   GST Rate: {gst_rate}%")
    print(f"   GST Amount: ₹{gst_amount}")
    print(f"   ✅ PASS" if gst_amount == 0 and gst_rate == 0 else "   ❌ FAIL")
    
    # Test Mid-range: ₹7,500 - ₹14,999 = 0% GST
    print("\n2. Mid-range Booking (₹7,500 - ₹14,999):")
    base = Decimal('10000.00')
    service_fee = 500  # 5% of 10000 = 500 (capped)
    gst_amount, gst_rate = calculate_hotel_gst(base, service_fee)
    print(f"   Base: ₹{base}")
    print(f"   Service Fee: ₹{service_fee}")
    print(f"   GST Rate: {gst_rate}%")
    print(f"   GST Amount: ₹{gst_amount}")
    print(f"   ✅ PASS" if gst_amount == 0 and gst_rate == 0 else "   ❌ FAIL")
    
    # Test Premium: ≥ ₹15,000 = 5% GST on (base + service fee)
    print("\n3. Premium Booking (≥ ₹15,000):")
    base = Decimal('18000.00')
    service_fee = 500  # Capped at 500
    gst_amount, gst_rate = calculate_hotel_gst(base, service_fee)
    expected_gst = int((base + Decimal(service_fee)) * Decimal('0.05'))
    print(f"   Base: ₹{base}")
    print(f"   Service Fee: ₹{service_fee}")
    print(f"   Taxable: ₹{base + Decimal(service_fee)}")
    print(f"   GST Rate: {gst_rate}%")
    print(f"   GST Amount: ₹{gst_amount} (Expected: ₹{expected_gst})")
    print(f"   ✅ PASS" if gst_amount == expected_gst and gst_rate == 5 else "   ❌ FAIL")
    
    # Test Complete Pricing
    print("\n" + "="*60)
    print("Testing Complete Pricing Calculations")
    print("="*60)
    
    # Budget booking
    print("\n4. Complete Budget Booking:")
    pricing = calculate_total_pricing(6000, 0, 'hotel')
    print(f"   Base: ₹{pricing['base_amount']}")
    print(f"   Service Fee: ₹{pricing['service_fee']}")
    print(f"   GST ({pricing['gst_rate_percent']}%): ₹{pricing['gst_amount']}")
    print(f"   Total: ₹{pricing['total_payable']}")
    print(f"   ✅ PASS" if pricing['gst_amount'] == 0 else "   ❌ FAIL")
    
    # Premium booking
    print("\n5. Complete Premium Booking:")
    pricing = calculate_total_pricing(18000, 0, 'hotel')
    expected_total = 18000 + 500 + 925  # base + service_fee + gst (5% of 18500)
    print(f"   Base: ₹{pricing['base_amount']}")
    print(f"   Service Fee: ₹{pricing['service_fee']}")
    print(f"   GST ({pricing['gst_rate_percent']}%): ₹{pricing['gst_amount']}")
    print(f"   Total: ₹{pricing['total_payable']} (Expected: ₹{expected_total})")
    print(f"   ✅ PASS" if pricing['total_payable'] == expected_total else "   ❌ FAIL")
    
    # Premium booking with promo
    print("\n6. Premium Booking with Promo:")
    pricing = calculate_total_pricing(18000, 2000, 'hotel')
    expected_discounted = 16000  # 18000 - 2000
    expected_service = 500  # Capped (5% of 18000 = 900, but cap = 500)
    expected_gst = 925  # 5% of (18000 + 500)
    expected_total = expected_discounted + expected_service + expected_gst
    print(f"   Base: ₹{pricing['base_amount']}")
    print(f"   Promo: -₹{pricing['promo_discount']}")
    print(f"   Discounted Base: ₹{pricing['discounted_base']}")
    print(f"   Service Fee: ₹{pricing['service_fee']}")
    print(f"   GST ({pricing['gst_rate_percent']}%): ₹{pricing['gst_amount']}")
    print(f"   Total: ₹{pricing['total_payable']} (Expected: ₹{expected_total})")
    print(f"   ✅ PASS" if pricing['total_payable'] == expected_total else "   ❌ FAIL")

if __name__ == '__main__':
    test_gst_tiers()
