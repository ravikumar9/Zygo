#!/usr/bin/env python
"""
FIX-3 VERIFICATION SCRIPT
Verifies all pricing calculations are working correctly
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.views import calculate_service_fee

def test_service_fee_calculations():
    """Test all service fee calculation scenarios"""
    
    test_cases = [
        # (input_price, expected_service_fee, description)
        (Decimal('2500'), 125, "₹2,500: 5% = ₹125"),
        (Decimal('5000'), 250, "₹5,000: 5% = ₹250"),
        (Decimal('10000'), 500, "₹10,000: 5% = ₹500 (at cap)"),
        (Decimal('50000'), 500, "₹50,000: 5% = ₹2,500 → ₹500 (capped)"),
        (Decimal('100'), 5, "₹100: 5% = ₹5"),
        (Decimal('2334'), 117, "₹2,334: 5% = ₹116.7 → ₹117 (rounded)"),
        (Decimal('0'), 0, "₹0: 5% = ₹0"),
    ]
    
    print("\n" + "="*70)
    print("FIX-3: SERVICE FEE CALCULATION VERIFICATION")
    print("="*70 + "\n")
    
    all_passed = True
    for price, expected, description in test_cases:
        result = calculate_service_fee(price)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result != expected:
            all_passed = False
            print(f"{status} | {description}")
            print(f"       Expected: ₹{expected}, Got: ₹{result}\n")
        else:
            print(f"{status} | {description}")
    
    return all_passed


def verify_pricing_examples():
    """Verify pricing calculation examples from documentation"""
    
    print("\n" + "="*70)
    print("FIX-3: PRICING CALCULATION EXAMPLES VERIFICATION")
    print("="*70 + "\n")
    
    # Example 1: Basic booking (₹2,500/night)
    print("EXAMPLE 1: Basic Booking (₹2,500/night, 2 nights, 1 room)")
    base_amount = Decimal('5000')  # ₹2,500 × 2 × 1
    service_fee = calculate_service_fee(base_amount)
    gst = (Decimal('5000') * Decimal('5')) / Decimal('100')  # 5% GST for base < 7,500
    taxes_fees = Decimal(service_fee) + gst
    total = base_amount + taxes_fees
    
    print(f"  Base Amount: ₹{base_amount}")
    print(f"  Service Fee: ₹{service_fee}")
    print(f"  GST (5%): ₹{int(gst)}")
    print(f"  Taxes & Services: ₹{int(taxes_fees)}")
    print(f"  Total Payable: ₹{int(total)}")
    assert service_fee == 250, "Example 1: Service fee should be 250"
    print("  ✅ Verified\n")
    
    # Example 2: High-price booking
    print("EXAMPLE 2: High-Price Booking (₹10,000/night, 1 night, 1 room)")
    base_amount = Decimal('10000')
    service_fee = calculate_service_fee(base_amount)
    gst = (Decimal('10000') * Decimal('18')) / Decimal('100')  # 18% GST for base ≥ 7,500
    taxes_fees = Decimal(service_fee) + gst
    total = base_amount + taxes_fees
    
    print(f"  Base Amount: ₹{base_amount}")
    print(f"  Service Fee: ₹{service_fee} (5% capped at ₹500)")
    print(f"  GST (18%): ₹{int(gst)}")
    print(f"  Taxes & Services: ₹{int(taxes_fees)}")
    print(f"  Total Payable: ₹{int(total)}")
    assert service_fee == 500, "Example 2: Service fee should be capped at 500"
    print("  ✅ Verified\n")
    
    # Example 3: Discounted booking
    print("EXAMPLE 3: Discounted Booking (₹4,000 effective after 20% off, 3 nights, 1 room)")
    base_amount = Decimal('12000')  # ₹4,000 × 3 × 1
    service_fee = calculate_service_fee(base_amount)
    gst = (Decimal('12000') * Decimal('18')) / Decimal('100')  # 18% GST for base ≥ 7,500
    taxes_fees = Decimal(service_fee) + gst
    total = base_amount + taxes_fees
    
    print(f"  Base Amount (discounted): ₹{base_amount}")
    print(f"  Service Fee: ₹{service_fee} (5% of discounted = ₹600, capped at ₹500)")
    print(f"  GST (18%): ₹{int(gst)}")
    print(f"  Taxes & Services: ₹{int(taxes_fees)}")
    print(f"  Total Payable: ₹{int(total)}")
    assert service_fee == 500, "Example 3: Service fee should be 500 (capped)"
    print("  ✅ Verified\n")
    
    return True


def check_template_files():
    """Verify all templates have been updated for Fix-3"""
    
    print("\n" + "="*70)
    print("FIX-3: TEMPLATE FILES VERIFICATION")
    print("="*70 + "\n")
    
    template_checks = [
        ('templates/hotels/hotel_list.html', 'From <strong', 'Search results price display'),
        ('templates/hotels/hotel_detail.html', 'Taxes & Services', 'Detail page tax section'),
        ('templates/hotels/hotel_detail.html', 'tax-info-', 'Collapsible tax IDs'),
        ('templates/bookings/confirmation.html', 'tax-breakdown', 'Confirmation tax collapse'),
        ('templates/payments/payment.html', 'tax-breakdown-payment', 'Payment tax collapse'),
    ]
    
    all_found = True
    for file_path, search_string, description in template_checks:
        full_path = os.path.join('c:/Users/ravi9/Downloads/cgpt/Go_explorer_clear', file_path)
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if search_string in content:
                    print(f"✅ {file_path}")
                    print(f"   └─ Found: {description}\n")
                else:
                    print(f"❌ {file_path}")
                    print(f"   └─ Missing: {description}\n")
                    all_found = False
        except FileNotFoundError:
            print(f"❌ {file_path}")
            print(f"   └─ File not found\n")
            all_found = False
    
    return all_found


def main():
    """Run all verification checks"""
    
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "FIX-3: PRICE DISCLOSURE VERIFICATION SUITE" + " "*11 + "║")
    print("╚" + "="*68 + "╝")
    
    results = []
    
    # Test service fee calculations
    results.append(("Service Fee Calculations", test_service_fee_calculations()))
    
    # Verify pricing examples
    results.append(("Pricing Examples", verify_pricing_examples()))
    
    # Check template files
    results.append(("Template Files", check_template_files()))
    
    # Print summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70 + "\n")
    
    all_passed = True
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {check_name}")
        if not result:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL FIX-3 VERIFICATIONS PASSED - READY FOR PRODUCTION")
    else:
        print("❌ SOME VERIFICATIONS FAILED - REVIEW REQUIRED")
    print("="*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
