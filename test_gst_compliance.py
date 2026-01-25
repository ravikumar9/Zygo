#!/usr/bin/env python
"""
Phase-2 Pricing Compliance Matrix (No GST)
Validates pricing_calculator.py for service fee cap + wallet behavior.
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from bookings.pricing_calculator import calculate_pricing
from bookings.models import Booking, HotelBooking
from datetime import datetime, timedelta


class TestGSTCompliance:
    def __init__(self):
        self.results = []

    def test_service_fee_under_cap(self):
        """5% service fee below ₹500 cap"""
        class MockBooking:
            booking_type = 'hotel'
            total_amount = Decimal('4000')
            booking_id = 'TEST-4000'
            metadata = {}

        booking = MockBooking()
        result = calculate_pricing(booking)

        expected_fee = Decimal('200.00')  # 5% of 4000
        assert result['platform_fee'] == expected_fee
        assert result['gst_amount'] == Decimal('0.00')
        assert result['total_payable'] == booking.total_amount + expected_fee

        self.results.append({
            'test': 'Hotel ₹4000 (5% fee)',
            'base': '₹4000',
            'service_fee': result['platform_fee'],
            'gst_amount': result['gst_amount'],
            'total_payable': result['total_payable'],
            'status': '✅ PASS'
        })
        print(f"✅ Service fee under cap: ₹{result['platform_fee']} | Total: ₹{result['total_payable']}")

    def test_service_fee_capped(self):
        """Service fee capped at ₹500 for high amounts"""
        class MockBooking:
            booking_type = 'hotel'
            total_amount = Decimal('20000')
            booking_id = 'TEST-20000'
            metadata = {}

        booking = MockBooking()
        result = calculate_pricing(booking)

        assert result['platform_fee'] == Decimal('500')
        assert result['gst_amount'] == Decimal('0.00')
        assert result['total_payable'] == Decimal('20500.00')

        self.results.append({
            'test': 'Hotel ₹20000 (fee cap)',
            'base': '₹20000',
            'service_fee': result['platform_fee'],
            'gst_amount': result['gst_amount'],
            'total_payable': result['total_payable'],
            'status': '✅ PASS'
        })
        print(f"✅ Service fee capped at ₹500 | Total: ₹{result['total_payable']}")

    def test_wallet_reduces_gateway_only(self):
        """Wallet deduction reduces gateway payable, fees unchanged."""
        class MockBooking:
            booking_type = 'hotel'
            total_amount = Decimal('6000')
            booking_id = 'TEST-WALLET'
            metadata = {}

        booking = MockBooking()

        result_without_wallet = calculate_pricing(booking, wallet_apply_amount=None)
        result_with_wallet = calculate_pricing(booking, wallet_apply_amount=Decimal('1000'))

        assert result_without_wallet['platform_fee'] == Decimal('300.00')
        assert result_with_wallet['platform_fee'] == result_without_wallet['platform_fee']
        assert result_without_wallet['gateway_payable'] - result_with_wallet['gateway_payable'] == Decimal('1000.00')

        self.results.append({
            'test': 'Wallet reduces gateway',
            'base': '₹6000',
            'service_fee': result_with_wallet['platform_fee'],
            'gateway_without': result_without_wallet['gateway_payable'],
            'gateway_with': result_with_wallet['gateway_payable'],
            'status': '✅ PASS'
        })
        print(f"✅ Wallet reduces gateway: ₹{result_without_wallet['gateway_payable']} → ₹{result_with_wallet['gateway_payable']}")

    def run_all(self):
        print("\n" + "="*80)
        print("PHASE-2 PRICING TEST MATRIX (NO GST)")
        print("="*80 + "\n")
        
        try:
            self.test_service_fee_under_cap()
            self.test_service_fee_capped()
            self.test_wallet_reduces_gateway_only()
            
            print("\n" + "="*80)
            print("✅ ALL TESTS PASSED")
            print("="*80 + "\n")
            return True
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {e}\n")
            return False


if __name__ == '__main__':
    tester = TestGSTCompliance()
    success = tester.run_all()
    sys.exit(0 if success else 1)
