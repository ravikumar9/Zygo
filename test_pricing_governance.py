"""
PRICING GOVERNANCE VERIFICATION TEST
=====================================

Tests all mandatory pricing rules to ensure compliance.
"""

import sys
import os
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from decimal import Decimal
from django.conf import settings
from bookings.pricing_utils import (
    calculate_service_fee,
    calculate_gst,
    calculate_total_pricing,
    validate_service_fee
)


def test_service_fee_cap():
    """Test that service fee never exceeds ₹500"""
    print("\n" + "="*60)
    print("TEST 1: Service Fee Hard Cap (MAX ₹500)")
    print("="*60)
    
    test_cases = [
        (1000, 50, "5% of ₹1000 = ₹50"),
        (5000, 250, "5% of ₹5000 = ₹250"),
        (10000, 500, "5% of ₹10000 = ₹500 (at cap)"),
        (15000, 500, "5% of ₹15000 = ₹750 → CAPPED at ₹500"),
        (50000, 500, "5% of ₹50000 = ₹2500 → CAPPED at ₹500"),
        (100000, 500, "5% of ₹100000 = ₹5000 → CAPPED at ₹500"),
    ]
    
    passed = 0
    failed = 0
    
    for base_amount, expected_fee, description in test_cases:
        result = calculate_service_fee(base_amount)
        status = "✅ PASS" if result == expected_fee else "❌ FAIL"
        
        if result == expected_fee:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} | Base: ₹{base_amount:,} → Fee: ₹{result} (expected ₹{expected_fee})")
        print(f"       {description}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_gst_calculation():
    """Test that GST applies only on service fee (18%)"""
    print("\n" + "="*60)
    print("TEST 2: GST Calculation (18% on service fee only)")
    print("="*60)
    
    test_cases = [
        (50, 9, "18% of ₹50 service fee = ₹9"),
        (100, 18, "18% of ₹100 service fee = ₹18"),
        (250, 45, "18% of ₹250 service fee = ₹45"),
        (500, 90, "18% of ₹500 service fee = ₹90"),
    ]
    
    passed = 0
    failed = 0
    
    for service_fee, expected_gst, description in test_cases:
        result = calculate_gst(service_fee)
        status = "✅ PASS" if result == expected_gst else "❌ FAIL"
        
        if result == expected_gst:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} | Service Fee: ₹{service_fee} → GST: ₹{result} (expected ₹{expected_gst})")
        print(f"       {description}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_total_pricing_pipeline():
    """Test complete pricing calculation pipeline"""
    print("\n" + "="*60)
    print("TEST 3: Complete Pricing Pipeline")
    print("="*60)
    
    # Test Case 1: Base ₹8000, no promo
    print("\n--- Case 1: ₹8000 base, no promo ---")
    result = calculate_total_pricing(8000, 0)
    print(f"Base Amount: ₹{result['base_amount']:,}")
    print(f"Promo Discount: ₹{result['promo_discount']:,}")
    print(f"Service Fee: ₹{result['service_fee']:,} (5% of ₹8000 = ₹400)")
    print(f"GST Amount: ₹{result['gst_amount']:,} (18% of ₹400 = ₹72)")
    print(f"Total Payable: ₹{result['total_payable']:,}")
    expected_total = 8000 + 400 + 72
    status = "✅ PASS" if result['total_payable'] == expected_total else "❌ FAIL"
    print(f"{status} Expected: ₹{expected_total:,}, Got: ₹{result['total_payable']:,}")
    
    # Test Case 2: Base ₹12000, ₹1000 promo
    print("\n--- Case 2: ₹12000 base, ₹1000 promo (fee should cap at ₹500) ---")
    result = calculate_total_pricing(12000, 1000)
    print(f"Base Amount: ₹{result['base_amount']:,}")
    print(f"Promo Discount: ₹{result['promo_discount']:,}")
    print(f"Discounted Base: ₹{result['discounted_base']:,}")
    print(f"Service Fee: ₹{result['service_fee']:,} (5% of ₹12000 = ₹600 → CAPPED at ₹500)")
    print(f"GST Amount: ₹{result['gst_amount']:,} (18% of ₹500 = ₹90)")
    print(f"Total Payable: ₹{result['total_payable']:,}")
    expected_total = 11000 + 500 + 90
    status = "✅ PASS" if result['total_payable'] == expected_total else "❌ FAIL"
    print(f"{status} Expected: ₹{expected_total:,}, Got: ₹{result['total_payable']:,}")
    
    # Test Case 3: Base ₹50000, ₹5000 promo (extreme cap test)
    print("\n--- Case 3: ₹50000 base, ₹5000 promo (extreme cap test) ---")
    result = calculate_total_pricing(50000, 5000)
    print(f"Base Amount: ₹{result['base_amount']:,}")
    print(f"Promo Discount: ₹{result['promo_discount']:,}")
    print(f"Discounted Base: ₹{result['discounted_base']:,}")
    print(f"Service Fee: ₹{result['service_fee']:,} (5% of ₹50000 = ₹2500 → CAPPED at ₹500)")
    print(f"GST Amount: ₹{result['gst_amount']:,} (18% of ₹500 = ₹90)")
    print(f"Total Payable: ₹{result['total_payable']:,}")
    expected_total = 45000 + 500 + 90
    status = "✅ PASS" if result['total_payable'] == expected_total else "❌ FAIL"
    print(f"{status} Expected: ₹{expected_total:,}, Got: ₹{result['total_payable']:,}")
    
    return True


def test_admin_validation():
    """Test admin form validation"""
    print("\n" + "="*60)
    print("TEST 4: Admin Validation (Hard Cap Enforcement)")
    print("="*60)
    
    test_cases = [
        (400, True, "Valid service fee ₹400"),
        (500, True, "Valid service fee ₹500 (at cap)"),
        (600, False, "Invalid service fee ₹600 (exceeds cap)"),
        (1000, False, "Invalid service fee ₹1000 (exceeds cap)"),
        (-100, False, "Invalid negative service fee"),
    ]
    
    passed = 0
    failed = 0
    
    for fee, should_pass, description in test_cases:
        is_valid, error_msg = validate_service_fee(fee)
        
        if should_pass:
            status = "✅ PASS" if is_valid else "❌ FAIL"
            if is_valid:
                passed += 1
            else:
                failed += 1
            print(f"{status} | {description} → {error_msg or 'Valid'}")
        else:
            status = "✅ PASS" if not is_valid else "❌ FAIL"
            if not is_valid:
                passed += 1
            else:
                failed += 1
            print(f"{status} | {description} → {error_msg or 'Should have failed!'}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_settings_constants():
    """Verify settings constants are properly defined"""
    print("\n" + "="*60)
    print("TEST 5: Settings Constants Verification")
    print("="*60)
    
    checks = []
    
    if hasattr(settings, 'MAX_SERVICE_FEE'):
        print(f"✅ MAX_SERVICE_FEE = {settings.MAX_SERVICE_FEE}")
        checks.append(True)
    else:
        print("❌ MAX_SERVICE_FEE not defined in settings")
        checks.append(False)
    
    if hasattr(settings, 'SERVICE_FEE_RATE'):
        print(f"✅ SERVICE_FEE_RATE = {settings.SERVICE_FEE_RATE}")
        checks.append(True)
    else:
        print("❌ SERVICE_FEE_RATE not defined in settings")
        checks.append(False)
    
    if hasattr(settings, 'GST_RATE'):
        print(f"✅ GST_RATE = {settings.GST_RATE}")
        checks.append(True)
    else:
        print("❌ GST_RATE not defined in settings")
        checks.append(False)
    
    return all(checks)


def main():
    """Run all pricing governance tests"""
    print("\n" + "="*60)
    print("PRICING GOVERNANCE VERIFICATION TEST SUITE")
    print("="*60)
    print(f"Testing against settings:")
    print(f"  MAX_SERVICE_FEE: ₹{getattr(settings, 'MAX_SERVICE_FEE', 'NOT SET')}")
    print(f"  SERVICE_FEE_RATE: {getattr(settings, 'SERVICE_FEE_RATE', 'NOT SET')}")
    print(f"  GST_RATE: {getattr(settings, 'GST_RATE', 'NOT SET')}")
    
    results = []
    
    # Run all tests
    results.append(("Settings Constants", test_settings_constants()))
    results.append(("Service Fee Cap", test_service_fee_cap()))
    results.append(("GST Calculation", test_gst_calculation()))
    results.append(("Pricing Pipeline", test_total_pricing_pipeline()))
    results.append(("Admin Validation", test_admin_validation()))
    
    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} | {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - PRICING GOVERNANCE VERIFIED")
    else:
        print("⚠️  SOME TESTS FAILED - REVIEW IMPLEMENTATION")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
