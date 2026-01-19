"""
Unified pricing calculation (single source of truth)

Order of operations (MANDATORY):
1. Base Amount
2. Apply Promo Discount
3. Calculate GST (on post-discount base)
4. Apply Wallet Deduction
5. Calculate Final Payable

All views must use this function to ensure consistency.
"""
from decimal import Decimal
from django.conf import settings


def calculate_pricing(booking, promo_code=None, wallet_apply_amount=None, user=None):
    """
    Calculate complete pricing breakdown for a booking.
    
    Args:
        booking: Booking object
        promo_code: PromoCode object (optional, from core.models)
        wallet_apply_amount: Amount to apply from wallet (optional, <= wallet_balance)
        user: User object (for promo validation)
    
    Returns:
        dict with:
            - base_amount
            - promo_discount
            - subtotal_after_promo
            - gst_amount
            - wallet_applied
            - total_payable
            - gateway_payable (total_payable - wallet_applied)
    """
    # Step 1: Base Amount (always)
    base_amount = Decimal(str(booking.total_amount))
    
    # Add corporate discount if applicable (stored in metadata)
    promo_discount = Decimal('0.00')
    metadata = getattr(booking, 'metadata', None)
    if metadata and isinstance(metadata, dict):
        if 'corporate_discount_amount' in metadata:
            promo_discount += abs(Decimal(str(metadata['corporate_discount_amount'])))
    
    # Step 2: Apply Promo Code Discount (if valid)
    if promo_code and user:
        # Use core.PromoCode.calculate_discount method
        promo_discount += promo_code.calculate_discount(base_amount - promo_discount, user)
    
    subtotal_after_promo = base_amount - promo_discount
    
    # Step 3: Calculate GST on post-discount base (18%)
    gst_percentage = Decimal('0.18')
    gst_amount = (subtotal_after_promo * gst_percentage).quantize(Decimal('0.01'))
    
    subtotal_with_gst = subtotal_after_promo + gst_amount
    
    # Step 4: Apply Wallet Deduction
    wallet_applied = Decimal('0.00')
    if wallet_apply_amount and wallet_apply_amount > Decimal('0.00'):
        # Never let wallet exceed total payable
        wallet_applied = min(wallet_apply_amount, subtotal_with_gst)
    
    # Step 5: Calculate Final Payable (to gateway)
    total_payable = subtotal_with_gst
    gateway_payable = total_payable - wallet_applied
    
    return {
        'base_amount': base_amount,
        'promo_discount': promo_discount,
        'subtotal_after_promo': subtotal_after_promo,
        'gst_amount': gst_amount,
        'subtotal_with_gst': subtotal_with_gst,
        'wallet_applied': wallet_applied,
        'total_payable': total_payable,
        'gateway_payable': gateway_payable,
    }
