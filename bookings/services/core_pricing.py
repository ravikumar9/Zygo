from decimal import Decimal

SERVICE_FEE_RATE = Decimal("0.05")
SERVICE_FEE_CAP = Decimal("500")
GST_THRESHOLD = Decimal("7500")
GST_LOW = Decimal("0.05")
GST_HIGH = Decimal("0.18")


class CorePricing:

    @staticmethod
    def calculate(room_price, nights, meal_delta=0, wallet_amount=0):

        room_price = Decimal(room_price or 0)
        meal_delta = Decimal(meal_delta or 0)
        nights = max(int(nights), 0)

        base = (room_price + meal_delta) * nights

        service_fee = min(base * SERVICE_FEE_RATE, SERVICE_FEE_CAP)

        gst_rate = GST_LOW if room_price < GST_THRESHOLD else GST_HIGH
        gst = service_fee * gst_rate

        taxes = service_fee + gst
        total = base + taxes

        wallet = min(Decimal(wallet_amount or 0), total)
        payable = total - wallet

        print(f"[CORE_PRICING] base={base} fee={service_fee} gst={gst} total={total}")

        return {
            "base_amount": base,
            "service_fee": service_fee,
            "gst_amount": gst,
            "taxes_total": taxes,
            "total_before_wallet": total,
            "wallet_applied": wallet,
            "gateway_payable": payable,
        }
