"""
Deterministic, idempotent seeding for packages.
Usage: python manage.py seed_packages [--clear]
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
from datetime import date, timedelta
from decimal import Decimal

from PIL import Image
import io

from core.models import City
from packages.models import (
    Package,
    PackageImage,
    PackageItinerary,
    PackageInclusion,
    PackageDeparture,
)


def _make_placeholder_image(color=(60, 120, 200), size=(800, 600)):
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class Command(BaseCommand):
    help = "Seed holiday packages with images, itineraries, inclusions, and departures (deterministic/idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing packages before seeding",
        )

    def handle(self, *args, **options):
        if options.get("clear"):
            self.stdout.write(self.style.WARNING("Clearing existing package data..."))
            PackageDeparture.objects.all().delete()
            PackageItinerary.objects.all().delete()
            PackageInclusion.objects.all().delete()
            PackageImage.objects.all().delete()
            Package.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("✓ Packages cleared"))

        # Ensure destination cities exist (shared with hotels command codes)
        cities_spec = [
            {"name": "Goa", "state": "Goa", "country": "India", "code": "GOA"},
            {"name": "Jaipur", "state": "Rajasthan", "country": "India", "code": "JAI"},
            {"name": "Manali", "state": "Himachal Pradesh", "country": "India", "code": "MNL"},
            {"name": "Darjeeling", "state": "West Bengal", "country": "India", "code": "DRG"},
            {"name": "Kerala", "state": "Kerala", "country": "India", "code": "COK"},
            {"name": "Andaman", "state": "Andaman & Nicobar", "country": "India", "code": "IXA"},
            {"name": "Leh", "state": "Ladakh", "country": "India", "code": "IXL"},
        ]

        city_map = {}
        for c in cities_spec:
            city, _ = City.objects.get_or_create(
                code=c["code"],
                defaults={
                    "name": c["name"],
                    "state": c["state"],
                    "country": c["country"],
                    "is_popular": True,
                },
            )
            city_map[c["name"]] = city

        # Deterministic package dataset
        packages_data = [
            {
                "name": "Goa Beach Escape",
                "type": "beach",
                "cities": ["Goa"],
                "days": 4,
                "nights": 3,
                "price": Decimal("24999.00"),
                "featured": True,
                "rating": Decimal("4.5"),
                "image_color": (0, 140, 200),
            },
            {
                "name": "Jaipur Cultural Heritage",
                "type": "cultural",
                "cities": ["Jaipur"],
                "days": 3,
                "nights": 2,
                "price": Decimal("19999.00"),
                "featured": True,
                "rating": Decimal("4.4"),
                "image_color": (200, 120, 60),
            },
            {
                "name": "Manali Adventure Trails",
                "type": "adventure",
                "cities": ["Manali"],
                "days": 5,
                "nights": 4,
                "price": Decimal("29999.00"),
                "featured": False,
                "rating": Decimal("4.3"),
                "image_color": (60, 180, 120),
            },
            {
                "name": "Darjeeling Family Getaway",
                "type": "family",
                "cities": ["Darjeeling"],
                "days": 4,
                "nights": 3,
                "price": Decimal("22999.00"),
                "featured": False,
                "rating": Decimal("4.2"),
                "image_color": (140, 80, 160),
            },
            {
                "name": "Leh-Ladakh Honeymoon Special",
                "type": "honeymoon",
                "cities": ["Leh"],
                "days": 6,
                "nights": 5,
                "price": Decimal("39999.00"),
                "featured": True,
                "rating": Decimal("4.6"),
                "image_color": (40, 100, 160),
            },
        ]

        created_count = 0
        for pdata in packages_data:
            pkg, created = Package.objects.get_or_create(
                name=pdata["name"],
                defaults={
                    "description": f"{pdata['name']} — curated experiences and guided tours.",
                    "package_type": pdata["type"],
                    "duration_days": pdata["days"],
                    "duration_nights": pdata["nights"],
                    "starting_price": pdata["price"],
                    "includes_hotel": True,
                    "includes_transport": True,
                    "includes_meals": True,
                    "includes_sightseeing": True,
                    "includes_guide": True,
                    "breakfast_included": True,
                    "lunch_included": False,
                    "dinner_included": True,
                    "is_active": True,
                    "is_featured": pdata["featured"],
                    "rating": pdata["rating"],
                    "review_count": 120,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"✓ Created package: {pkg.name}")

            # Destination cities (idempotent)
            for cname in pdata["cities"]:
                pkg.destination_cities.add(city_map[cname])

            # Attach primary image deterministically if not present
            if not pkg.image:
                img_bytes = _make_placeholder_image(color=pdata["image_color"])
                filename = f"packages/{pkg.id}_primary.png"
                pkg.image.save(filename, ContentFile(img_bytes), save=True)

            # Gallery image
            if not pkg.images.filter(is_primary=True).exists():
                gallery_bytes = _make_placeholder_image(color=(220, 220, 220))
                PackageImage.objects.get_or_create(
                    package=pkg,
                    is_primary=True,
                    defaults={
                        "caption": "Primary visual",
                        "image": ContentFile(gallery_bytes, name=f"packages/gallery/{pkg.id}_gallery_primary.png"),
                    },
                )

            # Inclusions (deterministic list)
            inclusions = [
                "3-star/4-star hotels",
                "Airport/railway transfers",
                "Daily breakfast",
                "City sightseeing with guide",
                "All taxes included",
            ]
            for inc in inclusions:
                PackageInclusion.objects.get_or_create(
                    package=pkg,
                    description=inc,
                    defaults={"is_included": True},
                )

            # Itinerary — fixed 3 days minimum
            base_days = min(3, pkg.duration_days)
            itinerary = [
                (1, "Arrival & Check-in", "Arrival, hotel check-in, evening at leisure", "Welcome drink, Dinner"),
                (2, "City Tour", "Guided sightseeing covering highlights", "Breakfast"),
                (3, "Excursion/Leisure", "Optional excursion or leisure time", "Breakfast, Dinner"),
            ]
            for day_num, title, desc, meals in itinerary[:base_days]:
                PackageItinerary.objects.get_or_create(
                    package=pkg,
                    day_number=day_num,
                    defaults={
                        "title": title,
                        "description": desc,
                        "activities": "Sightseeing, Photography, Shopping",
                        "meals_included": meals,
                        "accommodation": "Hotel",
                    },
                )

            # Departures: next 6 fixed dates
            start = date.today() + timedelta(days=3)
            for i in range(6):
                dep = start + timedelta(days=i * 7)
                ret = dep + timedelta(days=pkg.duration_days)
                PackageDeparture.objects.get_or_create(
                    package=pkg,
                    departure_date=dep,
                    defaults={
                        "return_date": ret,
                        "available_slots": 24,
                        "price_per_person": pkg.starting_price,
                        "is_active": True,
                    },
                )

        self.stdout.write(self.style.SUCCESS("\n✓ Successfully seeded packages"))
        self.stdout.write(f"  • Created/Ensured {len(packages_data)} packages")
        self.stdout.write(f"  • Ensured images, inclusions, itineraries, and departures")
