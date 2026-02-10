from decimal import Decimal
from bookings.services.core_pricing import CorePricing


# -----------------------------------------------------------
# INTERNAL
# -----------------------------------------------------------

def _get_room_inputs(booking):
    hotel_booking = getattr(booking, "hotel_details", None)
    room_type = getattr(hotel_booking, "room_type", None) if hotel_booking else None
    meal_plan = getattr(hotel_booking, "meal_plan", None) if hotel_booking else None
    num_rooms = getattr(hotel_booking, "number_of_rooms", 1) or 1
    nights = getattr(hotel_booking, "total_nights", 1) or 1

    room_price = Decimal(str(room_type.get_effective_price())) if room_type else Decimal("0.00")
    meal_delta = Decimal(str(getattr(meal_plan, "price_delta", 0) or 0)) if meal_plan else Decimal("0.00")

    room_price *= Decimal(str(num_rooms))
    meal_delta *= Decimal(str(num_rooms))

    return room_price, meal_delta, nights


def _from_frozen(booking, wallet_amount):
    total = Decimal(str(booking.final_amount or 0))
    service_fee = Decimal(str(booking.service_fee_amount or 0))
    gst = Decimal(str(booking.gst_amount or 0))
    taxes = Decimal(str(booking.taxes_total or 0))

    wallet = min(Decimal(str(wallet_amount or 0)), total)
    payable = total - wallet

    return {
        "base_amount": total - taxes,
        "service_fee": service_fee,
        "gst_amount": gst,
        "taxes_total": taxes,
        "total_before_wallet": total,
        "wallet_applied": wallet,
        "gateway_payable": payable,
    }


# -----------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------

def build_pricing_preview(booking, wallet_amount=0):
    """Only before confirmation"""
    room_price, meal_delta, nights = _get_room_inputs(booking)
    return CorePricing.calculate(room_price, nights, meal_delta, wallet_amount)


def freeze_pricing_for_booking(booking):
    """Freeze once at confirmation only"""
    if booking.final_amount is not None:
        return _from_frozen(booking, 0)

    pricing = build_pricing_preview(booking, 0)

    booking.final_amount = pricing["total_before_wallet"]
    booking.service_fee_amount = pricing["service_fee"]
    booking.gst_amount = pricing["gst_amount"]
    booking.taxes_total = pricing["taxes_total"]
    booking.total_amount = pricing["total_before_wallet"]

    booking.save(update_fields=[
        "final_amount",
        "service_fee_amount",
        "gst_amount",
        "taxes_total",
        "total_amount",
        "updated_at",
    ])

    return _from_frozen(booking, 0)


def build_pricing_from_frozen(booking, wallet_amount=0):
    """After freeze only — NEVER recompute"""
    if booking.final_amount is None:
        raise ValueError("Frozen pricing missing")
    return _from_frozen(booking, wallet_amount)
