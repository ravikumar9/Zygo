"""
PRICING GOVERNANCE - SINGLE SOURCE OF TRUTH
============================================

This module enforces mandatory pricing rules across GoExplorer.
All pricing calculations MUST use these functions.

MANDATORY RULES:
1. Service fee NEVER exceeds ₹500 (hard cap)
2. Hotel GST Rules (Goibibo-grade):
   - Budget booking (< ₹7,500): 0% GST
   - Premium booking (≥ ₹15,000): 5% GST on (base + service fee)
   - Mid-range (₹7,500 - ₹14,999): 0% GST
3. Promo codes affect ONLY base amount (never taxes)
4. All values stored in booking (no runtime recalculation)

DO NOT modify these functions without business approval.
"""

from decimal import Decimal
from django.conf import settings

# Hotel GST thresholds (Goibibo-grade)
BUDGET_THRESHOLD = Decimal('7500.00')
PREMIUM_THRESHOLD = Decimal('15000.00')


def calculate_service_fee(base_amount):
    """
    Calculate service fee with hard cap enforcement.
    
    Business Rules:
    - 5% of base amount
    - Hard cap at ₹500 (NEVER exceeded)
    - Rounded to nearest integer
    
    Args:
        base_amount: Base price before any fees
        
    Returns:
        int: Service fee in INR (max ₹500)
        
    Examples:
        >>> calculate_service_fee(1000)
        50  # 5% of ₹1000
        >>> calculate_service_fee(10000)
        500  # Capped at ₹500
        >>> calculate_service_fee(50000)
        500  # Still capped at ₹500
    """
    try:
        amount_decimal = Decimal(str(base_amount))
        calculated_fee = amount_decimal * Decimal(str(settings.SERVICE_FEE_RATE))
        
        # HARD CAP ENFORCEMENT - never exceed MAX_SERVICE_FEE
        capped_fee = min(calculated_fee, Decimal(str(settings.MAX_SERVICE_FEE)))
        
        # Round to nearest integer (no decimals)
        return int(capped_fee.quantize(Decimal('1')))
    except Exception:
        return 0


def calculate_hotel_gst(base_amount, service_fee=0):
    """
    Calculate GST for hotel bookings based on Goibibo-grade pricing tiers.
    
    Business Rules (Hotel Industry Standard):
    - Budget (< ₹7,500): 0% GST
    - Premium (≥ ₹15,000): 5% GST on (base + service fee)
    - Mid-range (₹7,500 - ₹14,999): 0% GST
    
    Args:
        base_amount: Base booking amount
        service_fee: Service fee (default 0)
        
    Returns:
        tuple: (gst_amount, gst_rate_percent)
        
    Examples:
        >>> calculate_hotel_gst(6000, 300)
        (0, 0)  # Budget: 0% GST
        >>> calculate_hotel_gst(18000, 500)
        (925, 5)  # Premium: 5% of (18000 + 500) = 925
        >>> calculate_hotel_gst(10000, 500)
        (0, 0)  # Mid-range: 0% GST
    """
    try:
        base = Decimal(str(base_amount))
        fee = Decimal(str(service_fee))
        
        # Budget: < ₹7,500 = 0% GST
        if base < BUDGET_THRESHOLD:
            return (0, 0)
        
        # Mid-range: ₹7,500 - ₹14,999 = 0% GST
        if base < PREMIUM_THRESHOLD:
            return (0, 0)
        
        # Premium: ≥ ₹15,000 = 5% GST on (base + service fee)
        taxable_amount = base + fee
        gst_rate = Decimal('0.05')  # 5%
        gst_amount = (taxable_amount * gst_rate).quantize(Decimal('0.01'))
        
        return (int(gst_amount), 5)
    except Exception:
        return (0, 0)


def calculate_gst(service_fee, base_amount=None):
    """
    Calculate GST - delegates to hotel-specific logic if base_amount provided.
    
    For backward compatibility:
    - If base_amount provided: use hotel GST tiers
    - If base_amount not provided: 18% on service fee only (legacy)
    
    Business Rules:
    - Hotel bookings: Use tiered GST (0% or 5% based on base price)
    - Other bookings: 18% GST on service fee
    
    Args:
        service_fee: Service fee amount
        base_amount: Base booking amount (optional, for hotel bookings)
        
    Returns:
        int: GST amount in INR
        
    Examples:
        >>> calculate_gst(500, 6000)
        0  # Budget hotel: 0% GST
        >>> calculate_gst(500, 18000)
        925  # Premium hotel: 5% of (18000 + 500)
        >>> calculate_gst(500)
        90  # Legacy: 18% of ₹500
    """
    # Hotel booking with tiered GST
    if base_amount is not None:
        gst_amount, gst_rate = calculate_hotel_gst(base_amount, service_fee)
        return gst_amount
    
    # Legacy/other bookings: 18% on service fee
    try:
        fee_decimal = Decimal(str(service_fee))
        gst = fee_decimal * Decimal(str(settings.GST_RATE))
        return int(gst.quantize(Decimal('1')))
    except Exception:
        return 0


def get_hotel_gst_rate(base_amount):
    """
    Get GST rate percentage for hotel booking.
    
    Returns:
        int: GST rate as percentage (0 or 5)
    """
    try:
        base = Decimal(str(base_amount))
        if base < PREMIUM_THRESHOLD:
            return 0
        return 5
    except Exception:
        return 0


def calculate_total_pricing(base_amount, promo_discount=0, booking_type='hotel'):
    """
    Calculate complete pricing breakdown following mandatory pipeline.
    
    Calculation Pipeline (DO NOT CHANGE ORDER):
    1. Base Amount
    2. Apply Promo Discount (to base only)
    3. Calculate Service Fee (on base, capped at ₹500)
    4. Calculate GST (tiered for hotels: 0% or 5% based on base)
    5. Calculate Total
    
    Args:
        base_amount: Base price
        promo_discount: Discount amount (affects base only)
        booking_type: Type of booking ('hotel', 'bus', 'package')
        
    Returns:
        dict: Complete pricing breakdown
            - base_amount: Original base price
            - promo_discount: Discount applied
            - discounted_base: Base after promo
            - service_fee: Service fee (max ₹500)
            - gst_amount: GST amount
            - gst_rate_percent: GST rate (0 or 5 for hotels)
            - taxes_total: Service fee + GST
            - total_payable: Final amount
            
    Examples:
        >>> calculate_total_pricing(6000, 0, 'hotel')
        {
            'base_amount': 6000,
            'promo_discount': 0,
            'discounted_base': 6000,
            'service_fee': 300,  # 5% of 6000
            'gst_amount': 0,     # Budget: 0% GST
            'gst_rate_percent': 0,
            'taxes_total': 300,
            'total_payable': 6300
        }
        
        >>> calculate_total_pricing(18000, 1000, 'hotel')
        {
            'base_amount': 18000,
            'promo_discount': 1000,
            'discounted_base': 17000,
            'service_fee': 500,  # Capped! (5% of 18000 = 900, but cap = 500)
            'gst_amount': 925,   # 5% of (18000 + 500) = 925
            'gst_rate_percent': 5,
            'taxes_total': 1425,
            'total_payable': 18425
        }
    """
    try:
        base = Decimal(str(base_amount))
        promo = Decimal(str(promo_discount))
        
        # Step 1-2: Apply promo to base
        discounted_base = base - promo
        
        # Step 3: Service fee (on original base, not discounted)
        service_fee = calculate_service_fee(base) if booking_type == 'hotel' else 0
        
        # Step 4: GST (tiered for hotels)
        gst_amount = 0
        gst_rate_percent = 0
        
        if booking_type == 'hotel':
            gst_amount, gst_rate_percent = calculate_hotel_gst(base, service_fee)
        elif service_fee > 0:
            # Legacy: 18% on service fee for non-hotel bookings
            gst_amount = calculate_gst(service_fee)
            gst_rate_percent = 18
        
        # Step 5: Total
        taxes_total = service_fee + gst_amount
        total_payable = int((discounted_base + Decimal(taxes_total)).quantize(Decimal('1')))
        
        return {
            'base_amount': int(base),
            'promo_discount': int(promo),
            'discounted_base': int(discounted_base),
            'service_fee': service_fee,
            'gst_amount': gst_amount,
            'gst_rate_percent': gst_rate_percent,
            'taxes_total': taxes_total,
            'total_payable': total_payable,
        }
    except Exception:
        return {
            'base_amount': 0,
            'promo_discount': 0,
            'discounted_base': 0,
            'service_fee': 0,
            'gst_amount': 0,
            'gst_rate_percent': 0,
            'taxes_total': 0,
            'total_payable': 0,
        }


def validate_service_fee(fee):
    """
    Validate service fee doesn't exceed hard cap.
    Used in admin panels and API validation.
    
    Args:
        fee: Service fee to validate
        
    Returns:
        tuple: (is_valid, error_message)
        
    Examples:
        >>> validate_service_fee(400)
        (True, None)
        >>> validate_service_fee(600)
        (False, 'Service fee cannot exceed ₹500')
    """
    try:
        fee_decimal = Decimal(str(fee))
        max_fee = Decimal(str(settings.MAX_SERVICE_FEE))
        
        if fee_decimal > max_fee:
            return (False, f'Service fee cannot exceed ₹{settings.MAX_SERVICE_FEE}')
        
        if fee_decimal < 0:
            return (False, 'Service fee cannot be negative')
            
        return (True, None)
    except Exception:
        return (False, 'Invalid service fee value')
