from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from bookings.models import Booking, InventoryLock
from core.models import PromoCode
from hotels.models import Hotel, RoomAvailability
from payments.models import Wallet
from users.models import User


class Command(BaseCommand):
    help = "Reset Playwright test inventory/bookings/wallets to deterministic values"

    def handle(self, *args, **options):
        hotel = Hotel.objects.filter(name="Playwright Test Hotel").first()
        if not hotel:
            self.stdout.write("Playwright Test Hotel not found; run seed_playwright_data first.")
            return

        # Delete test bookings and locks
        Booking.objects.filter(hotel_details__room_type__hotel=hotel).delete()
        InventoryLock.objects.filter(hotel=hotel).delete()

        # Reset room availability to 5 for next 30 days and price back to base
        today = date.today()
        for room in hotel.room_types.all():
            for offset in range(30):
                the_date = today + timedelta(days=offset)
                RoomAvailability.objects.update_or_create(
                    room_type=room,
                    date=the_date,
                    defaults={"available_rooms": 5, "price": room.base_price},
                )

        # Reset wallet balances for test users
        wallets = {
            "lowwallet@test.com": Decimal("1000"),
            "richwallet@test.com": Decimal("50000"),
        }
        for email, balance in wallets.items():
            try:
                user = User.objects.get(username=email)
                wallet, _ = Wallet.objects.get_or_create(user=user)
                wallet.balance = balance
                wallet.save(update_fields=["balance", "updated_at"])
            except User.DoesNotExist:
                continue

        # Reset promo usage counters (not discount config)
        PromoCode.objects.filter(code__in=["PWVALID10", "PWINVALID"]).update(total_uses=0)

        self.stdout.write("Reset complete: bookings cleared, inventory=5, wallets reset, promo usage cleared.")
