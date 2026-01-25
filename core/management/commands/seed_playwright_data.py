from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import Booking, InventoryLock
from core.models import City, PromoCode
from hotels.models import Hotel, MealPlan, RoomAvailability, RoomMealPlan, RoomType
from payments.models import Wallet
from django.conf import settings


class Command(BaseCommand):
    help = "Seed deterministic Playwright test data: hotel, rooms, meal plans, promos, wallets"

    def handle(self, *args, **options):
        User = get_user_model()
        today = date.today()
        horizon = 30

        # City
        city, _ = City.objects.get_or_create(
            code="BLR",
            defaults={"name": "Bangalore", "state": "Karnataka", "country": "India"},
        )

        # Hotel
        hotel_defaults = {
            "description": "Playwright deterministic test hotel (is_test_data=True)",
            "address": "Test Address, Bangalore",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "property_type": "hotel",
            "amenities_rules": "Test data only",
            "property_rules": "Test data only",
            "star_rating": 4,
            "review_rating": Decimal("4.5"),
            "review_count": 10,
            "contact_phone": "9999999999",
            "contact_email": "playwright-hotel@test.com",
            "inventory_source": "internal_cm",
            "is_active": True,
        }
        hotel, _ = Hotel.objects.update_or_create(
            name="Playwright Test Hotel",
            city=city,
            defaults=hotel_defaults,
        )

        # Meal plans (global)
        meal_plan_specs = [
            ("Room Only", "room_only", 0, True),
            ("Breakfast", "breakfast", 500, False),
            ("Half Board", "half_board", 1200, False),
            ("Full Board", "full_board", 2000, False),
        ]
        meal_plan_map = {}
        for name, plan_type, _, _ in meal_plan_specs:
            mp, _ = MealPlan.objects.get_or_create(
                plan_type=plan_type,
                defaults={
                    "name": name,
                    "description": "Playwright test meal plan",
                    "display_order": 0,
                    "is_active": True,
                },
            )
            meal_plan_map[plan_type] = mp

        # Room types
        room_specs = [
            {
                "code": "PW_BUDGET",
                "name": "PW_BUDGET - Budget Room",
                "base_price": Decimal("6999"),
                "bed_type": "queen",
                "room_size": 220,
                "max_adults": 2,
                "max_children": 0,
                "total_rooms": 5,
            },
            {
                "code": "PW_PREMIUM",
                "name": "PW_PREMIUM - Premium Room",
                "base_price": Decimal("15000"),
                "bed_type": "king",
                "room_size": 320,
                "max_adults": 2,
                "max_children": 1,
                "total_rooms": 5,
            },
        ]

        room_types = {}
        for spec in room_specs:
            rt, _ = RoomType.objects.update_or_create(
                hotel=hotel,
                name=spec["name"],
                defaults={
                    "description": f"Deterministic {spec['code']} test room",
                    "room_type": "standard",
                    "max_adults": spec["max_adults"],
                    "max_children": spec["max_children"],
                    "max_occupancy": spec["max_adults"] + spec["max_children"],
                    "bed_type": spec["bed_type"],
                    "number_of_beds": 1,
                    "room_size": spec["room_size"],
                    "base_price": spec["base_price"],
                    "is_refundable": True,
                    "status": "READY",
                    "discount_type": "none",
                    "discount_value": Decimal("0"),
                    "total_rooms": spec["total_rooms"],
                    "is_available": True,
                },
            )
            room_types[spec["code"]] = rt

            # Room meal plans
            RoomMealPlan.objects.filter(room_type=rt).delete()
            for name, plan_type, delta, is_default in meal_plan_specs:
                mp = meal_plan_map[plan_type]
                RoomMealPlan.objects.create(
                    room_type=rt,
                    meal_plan=mp,
                    price_delta=Decimal(str(delta)),
                    is_default=is_default,
                    is_active=True,
                    display_order=0,
                )

            # Availability for next horizon days
            for offset in range(horizon):
                the_date = today + timedelta(days=offset)
                RoomAvailability.objects.update_or_create(
                    room_type=rt,
                    date=the_date,
                    defaults={
                        "available_rooms": spec["total_rooms"],
                        "price": spec["base_price"],
                    },
                )

        # Promo codes
        now = timezone.now()
        valid_promo_defaults = {
            "description": "Playwright valid 10%",
            "discount_type": "percentage",
            "discount_value": Decimal("10"),
            "applicable_to": "hotel",
            "min_booking_amount": Decimal("5000"),
            "max_discount_amount": None,
            "valid_from": now - timedelta(days=1),
            "valid_until": now + timedelta(days=365),
            "is_active": True,
        }
        PromoCode.objects.update_or_create(
            code="PWVALID10",
            defaults=valid_promo_defaults,
        )
        PromoCode.objects.update_or_create(
            code="PWINVALID",
            defaults={
                **valid_promo_defaults,
                "description": "Playwright invalid promo",
                "is_active": False,
            },
        )

        # Users and wallets
        def ensure_user(email, password, balance):
            user, created = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "password": make_password(password)},
            )
            if created:
                user.email_verified = True
                user.phone_verified = True
                user.save(update_fields=["email_verified", "phone_verified"])
            wallet, _ = Wallet.objects.get_or_create(user=user)
            wallet.balance = Decimal(str(balance))
            wallet.save(update_fields=["balance", "updated_at"])
            return user

        ensure_user("lowwallet@test.com", "Test@123", balance=1000)
        ensure_user("richwallet@test.com", "Test@123", balance=50000)

        # Admin user
        if not User.objects.filter(username="admin@test.com").exists():
            User.objects.create_superuser(
                username="admin@test.com",
                email="admin@test.com",
                password="Admin@123",
            )

        # Clean existing test bookings/locks for repeatability
        Booking.objects.filter(hotel_details__room_type__hotel=hotel).delete()
        InventoryLock.objects.filter(hotel=hotel).delete()

        summary = [
            "Playwright Seed Complete",
            f"Hotel: {hotel.name} (ID={hotel.id})",
            "Rooms: PW_BUDGET, PW_PREMIUM (inventory=5)",
            "Promo: PWVALID10 active, PWINVALID inactive",
            "Wallets: lowwallet (1000), richwallet (50000)",
            "Hold Timer: {} minutes".format(getattr(settings, 'PLAYWRIGHT_HOLD_MINUTES', 10)),
        ]
        self.stdout.write("\n".join(summary))
