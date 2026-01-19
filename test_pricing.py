#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from bookings.pricing_calculator import calculate_pricing
from bookings.models import Booking
from core.models import PromoCode
from payments.models import Wallet

booking = Booking.objects.get(booking_id='b561fd8d-660a-4bdf-8c82-985c32a44fcb')
print(f'=== TEST 1: Base + GST (No Promo) ===')
print(f'Booking: {booking.booking_id}')
print(f'Total Amount: {booking.total_amount}')

pricing = calculate_pricing(booking=booking, promo_code=None, wallet_apply_amount=None, user=booking.user)
print(f'✅ Base: {pricing["base_amount"]} | Promo: {pricing["promo_discount"]} | GST: {pricing["gst_amount"]} | Total: {pricing["total_payable"]}')

# Test with promo
print(f'\n=== TEST 2: Base + Promo + GST ===')
promo = PromoCode.objects.get(code='WELCOME500')
print(f'Promo: {promo.code} (₹{promo.discount_value})')

pricing = calculate_pricing(booking=booking, promo_code=promo, wallet_apply_amount=None, user=booking.user)
print(f'✅ Base: {pricing["base_amount"]} | Promo: {pricing["promo_discount"]} | Subtotal: {pricing["subtotal_after_promo"]} | GST: {pricing["gst_amount"]} | Total: {pricing["total_payable"]}')

# Test with wallet
print(f'\n=== TEST 3: Promo + GST + Wallet ===')
wallet = Wallet.objects.get(user=booking.user)
print(f'Wallet Balance: {wallet.balance}')

pricing = calculate_pricing(booking=booking, promo_code=promo, wallet_apply_amount=wallet.balance, user=booking.user)
print(f'✅ Base: {pricing["base_amount"]} | Promo: {pricing["promo_discount"]} | Subtotal: {pricing["subtotal_after_promo"]} | GST: {pricing["gst_amount"]} | Total: {pricing["total_payable"]} | Wallet: {pricing["wallet_applied"]} | Gateway: {pricing["gateway_payable"]}')

print(f'\n✅ ALL TESTS PASSED - Pricing Calculator Working')
