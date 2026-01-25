"""
Unified pricing calculation (single source of truth)

Phase-2 locked order of operations:
1. Base Amount
2. Apply Promo Discount
3. Calculate Service Fee (5% capped at ₹500)
4. Apply Wallet Deduction
5. Calculate Final Payable

Notes:
- NO GST slabs in Phase-2 (gst fields remain for compatibility but are always 0)
- Service fee is capped at ₹500 and is the only fee shown behind the ℹ breakdown
"""
from decimal import Decimal
from bookings.utils.pricing import calculate_service_fee


def calculate_pricing(booking, promo_code=None, wallet_apply_amount=None, user=None):
    """
    Calculate complete pricing breakdown for a booking following Phase-2 rules (no GST).

    Service Fee:
        - 5% of base amount
        - Hard cap at ₹500
        - Included in fees breakdown (hidden in primary UI)
    """
    # Step 1: Base Amount (always)
    base_amount = Decimal(str(booking.total_amount)).quantize(Decimal('0.01'))

    # Prefer stored pricing snapshot if available to avoid recomputation drift
    pricing_data = getattr(booking, 'pricing_data', None) or {}
    snapshot_base = pricing_data.get('total_before_fee') or pricing_data.get('base_amount')
    if snapshot_base:
        try:
            base_amount = Decimal(str(snapshot_base)).quantize(Decimal('0.01'))
        except Exception:
            pass

    # Add corporate discount if applicable (stored in metadata)
    promo_discount = Decimal('0.00')
    metadata = getattr(booking, 'metadata', None)
    if metadata and isinstance(metadata, dict):
        if 'corporate_discount_amount' in metadata:
            promo_discount += abs(Decimal(str(metadata['corporate_discount_amount']))).quantize(Decimal('0.01'))

    # Step 2: Apply Promo Code Discount (if valid)
    if promo_code:
        # Use core.PromoCode.calculate_discount method (returns tuple: (amount, error))
        # service_type uses booking.booking_type to ensure hotel/bus/package correctness
        service_type = getattr(booking, 'booking_type', 'all') or 'all'
        try:
            discount_amount, error = promo_code.calculate_discount(base_amount - promo_discount, service_type)
            if not error:
                promo_discount += Decimal(str(discount_amount)).quantize(Decimal('0.01'))
        except Exception as e:
            # Defensive: never break pricing flow due to promo errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error("[PRICING_CALC_PROMO_ERROR] booking=%s promo=%s error=%s", booking.booking_id, promo_code.code, str(e))
            discount_amount, error = (0, 'Promo calculation failed')

    subtotal_after_promo = (base_amount - promo_discount).quantize(Decimal('0.01'))

    # Step 3: Service Fee - 5% of base, capped at ₹500
    service_fee = Decimal('0.00')
    if getattr(booking, 'booking_type', None) == 'hotel':
        service_fee = Decimal(str(calculate_service_fee(base_amount)))

    # Legacy compatibility: keep platform_fee alias
    platform_fee = service_fee

    # No GST in Phase-2
    gst_amount = Decimal('0.00')
    gst_rate_percent = 0
    taxes_and_fees = service_fee
    taxable_amount = service_fee

    subtotal_with_fees = subtotal_after_promo + taxes_and_fees

    # Step 5: Apply Wallet Deduction
    wallet_applied = Decimal('0.00')
    if wallet_apply_amount and wallet_apply_amount > Decimal('0.00'):
        # Never let wallet exceed total payable
        wallet_applied = min(Decimal(str(wallet_apply_amount)).quantize(Decimal('0.01')), subtotal_with_fees)

    # Step 6: Calculate Final Payable (to gateway)
    total_payable = subtotal_with_fees
    gateway_payable = (total_payable - wallet_applied).quantize(Decimal('0.01'))

    return {
        'base_amount': base_amount,
        'promo_discount': promo_discount,
        'subtotal_after_promo': subtotal_after_promo,
        'platform_fee': platform_fee,
        'service_fee': service_fee,
        'gst_rate': Decimal('0.00'),
        'gst_rate_percent': gst_rate_percent,
        'gst_amount': gst_amount,
        'taxable_amount': taxable_amount,
        'taxes_and_fees': taxes_and_fees,
        'subtotal_with_gst': subtotal_with_fees,
        'wallet_applied': wallet_applied,
        'total_payable': total_payable,
        'gateway_payable': gateway_payable,
    }
