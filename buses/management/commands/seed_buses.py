"""
Deterministic, idempotent seeding for buses, operators, routes, boarding/dropping points,
seat layouts (including ladies' seats), and schedules.
Usage: python manage.py seed_buses [--clear]
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.base import ContentFile
from datetime import time, date, timedelta
from decimal import Decimal

from PIL import Image
import io

from core.models import City
from buses.models import (
    BusOperator,
    Bus,
    BusRoute,
    BoardingPoint,
    DroppingPoint,
    BusStop,
    BusSchedule,
    SeatLayout,
)


def _make_logo(color=(30, 30, 200), size=(400, 200)):
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class Command(BaseCommand):
    help = "Seed buses and routes (deterministic/idempotent) with proper seat layouts and ladies seats."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing buses/routes before seeding",
        )

    def handle(self, *args, **options):
        if options.get("clear"):
            # Avoid deleting objects protected by bookings; proceed idempotently.
            self.stdout.write(self.style.WARNING("Clear requested: skipping destructive deletes due to protected bookings; proceeding with idempotent reseed."))

        # Ensure key cities (shared codes with hotels seeding)
        cities_spec = {
            "Bangalore": {"state": "Karnataka", "code": "BLR"},
            "Chennai": {"state": "Tamil Nadu", "code": "MAA"},
            "Mumbai": {"state": "Maharashtra", "code": "MUM"},
            "Pune": {"state": "Maharashtra", "code": "PNQ"},
            "Delhi": {"state": "Delhi", "code": "DEL"},
            "Jaipur": {"state": "Rajasthan", "code": "JAI"},
        }
        city_map = {}
        for name, spec in cities_spec.items():
            city, _ = City.objects.get_or_create(
                code=spec["code"],
                defaults={"name": name, "state": spec["state"], "country": "India", "is_popular": True},
            )
            city_map[name] = city

        # Operators (deterministic)
        operators = [
            {"name": "Swift Travels", "contact_phone": "+91-90000-11111", "contact_email": "support@swifttravels.in", "color": (20, 140, 200)},
            {"name": "Metro Lines", "contact_phone": "+91-90000-22222", "contact_email": "help@metrolines.in", "color": (140, 40, 160)},
        ]
        op_map = {}
        for op in operators:
            operator, created = BusOperator.objects.get_or_create(
                name=op["name"],
                defaults={
                    "description": f"{op['name']} — safe and reliable.",
                    "contact_phone": op["contact_phone"],
                    "contact_email": op["contact_email"],
                    "rating": Decimal("4.2"),
                    "is_active": True,
                    "verification_status": "verified",
                },
            )
            if created:
                self.stdout.write(f"✓ Created operator: {operator.name}")
            if not operator.logo:
                logo_bytes = _make_logo(color=op["color"]) 
                operator.logo.save(f"buses/operators/{operator.id}_logo.png", ContentFile(logo_bytes), save=True)
            op_map[operator.name] = operator

        # Buses dataset: (bus_number unique)
        buses_data = [
            {
                "operator": "Swift Travels",
                "bus_number": "KA-01-AB-1234",
                "bus_name": "Swift Seater",
                "bus_type": "seater",
                "total_seats": 40,
                "amenities": {"has_ac": True, "has_wifi": False, "has_charging_point": True},
                "manufacturing_year": 2018,
                "registration_number": "KA01AB1234",
            },
            {
                "operator": "Metro Lines",
                "bus_number": "MH-12-XY-5678",
                "bus_name": "Metro AC Seater",
                "bus_type": "ac_seater",
                "total_seats": 36,
                "amenities": {"has_ac": True, "has_wifi": True, "has_charging_point": True},
                "manufacturing_year": 2020,
                "registration_number": "MH12XY5678",
            },
        ]
        bus_map = {}
        for b in buses_data:
            bus, created = Bus.objects.get_or_create(
                bus_number=b["bus_number"],
                defaults={
                    "operator": op_map[b["operator"]],
                    "bus_name": b["bus_name"],
                    "bus_type": b["bus_type"],
                    "total_seats": b["total_seats"],
                    "manufacturing_year": b["manufacturing_year"],
                    "registration_number": b["registration_number"],
                    "has_ac": b["amenities"].get("has_ac", False),
                    "has_wifi": b["amenities"].get("has_wifi", False),
                    "has_charging_point": b["amenities"].get("has_charging_point", False),
                    "has_emergency_exit": True,
                    "has_first_aid": True,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(f"✓ Created bus: {bus.bus_number}")
            bus_map[bus.bus_number] = bus

        # Routes — deterministic 3 routes
        routes_spec = [
            {
                "bus_number": "KA-01-AB-1234",
                "route_name": "Bangalore to Chennai",
                "source": "Bangalore",
                "destination": "Chennai",
                "depart": time(22, 0),
                "arrive": time(6, 0),
                "duration_hours": Decimal("8.0"),
                "distance_km": Decimal("350.0"),
                "base_fare": Decimal("899.00"),
            },
            {
                "bus_number": "MH-12-XY-5678",
                "route_name": "Mumbai to Pune",
                "source": "Mumbai",
                "destination": "Pune",
                "depart": time(7, 30),
                "arrive": time(11, 30),
                "duration_hours": Decimal("4.0"),
                "distance_km": Decimal("150.0"),
                "base_fare": Decimal("499.00"),
            },
            {
                "bus_number": "MH-12-XY-5678",
                "route_name": "Delhi to Jaipur",
                "source": "Delhi",
                "destination": "Jaipur",
                "depart": time(6, 45),
                "arrive": time(12, 30),
                "duration_hours": Decimal("5.75"),
                "distance_km": Decimal("280.0"),
                "base_fare": Decimal("749.00"),
            },
        ]

        route_map = {}
        for r in routes_spec:
            route, created = BusRoute.objects.get_or_create(
                bus=bus_map[r["bus_number"]],
                route_name=r["route_name"],
                defaults={
                    "source_city": city_map[r["source"]],
                    "destination_city": city_map[r["destination"]],
                    "departure_time": r["depart"],
                    "arrival_time": r["arrive"],
                    "duration_hours": r["duration_hours"],
                    "distance_km": r["distance_km"],
                    "base_fare": r["base_fare"],
                    "is_active": True,
                    "operates_monday": True,
                    "operates_tuesday": True,
                    "operates_wednesday": True,
                    "operates_thursday": True,
                    "operates_friday": True,
                    "operates_saturday": True,
                    "operates_sunday": True,
                },
            )
            if created:
                self.stdout.write(f"✓ Created route: {route.route_name}")
            route_map[route.route_name] = route

        # Boarding/Dropping points (idempotent)
        for route in route_map.values():
            # Boarding
            BoardingPoint.objects.get_or_create(
                route=route,
                name=f"{route.source_city.name} Central Bus Stand",
                defaults={
                    "address": f"{route.source_city.name} Main Bus Stand",
                    "landmark": "City Center",
                    "city": route.source_city,
                    "pickup_time": route.departure_time,
                    "sequence_order": 1,
                    "is_active": True,
                },
            )
            # Dropping
            DroppingPoint.objects.get_or_create(
                route=route,
                name=f"{route.destination_city.name} Central Bus Station",
                defaults={
                    "address": f"{route.destination_city.name} Central",
                    "landmark": "City Center",
                    "city": route.destination_city,
                    "drop_time": route.arrival_time,
                    "sequence_order": 1,
                    "is_active": True,
                },
            )

        # Intermediate stops (one per long route)
        blr_maa = route_map.get("Bangalore to Chennai")
        if blr_maa:
            vellore, _ = City.objects.get_or_create(
                code="VLR",
                defaults={"name": "Vellore", "state": "Tamil Nadu", "country": "India", "is_popular": False},
            )
            BusStop.objects.get_or_create(
                route=blr_maa,
                stop_order=1,
                defaults={
                    "city": vellore,
                    "stop_name": "Vellore By-pass",
                    "arrival_time": time(2, 0),
                    "departure_time": time(2, 15),
                },
            )

        # Seat layout: deterministic 2x2 seater for each bus
        for bus in bus_map.values():
            if not SeatLayout.objects.filter(bus=bus).exists():
                rows = bus.total_seats // 4  # 2+2 layout
                labels = ["A", "B", "C", "D"]
                for row in range(1, rows + 1):
                    for col_idx, label in enumerate(labels, start=1):
                        seat_no = f"{row}{label}"
                        SeatLayout.objects.get_or_create(
                            bus=bus,
                            seat_number=seat_no,
                            defaults={
                                "seat_type": "seater",
                                "row": row,
                                "column": col_idx,
                                "deck": 1,
                                "reserved_for": "ladies" if row in (1, 2) and label in ("A", "D") else "general",
                            },
                        )

        # Schedules: next 7 days for each route
        start = date.today() + timedelta(days=1)
        for route in route_map.values():
            for i in range(7):
                d = start + timedelta(days=i)
                BusSchedule.objects.get_or_create(
                    route=route,
                    date=d,
                    defaults={
                        "available_seats": route.bus.total_seats,
                        "booked_seats": 0,
                        "fare": route.base_fare,
                        "is_active": True,
                        "is_cancelled": False,
                        "window_seat_charge": Decimal("50.00"),
                    },
                )

        self.stdout.write(self.style.SUCCESS("\n✓ Successfully seeded buses/routes"))
        self.stdout.write("  • Ensured operators, buses, routes")
        self.stdout.write("  • Added boarding/dropping points and a mid stop")
        self.stdout.write("  • Built 2x2 seat layouts with ladies' seats")
        self.stdout.write("  • Added 7-day schedules with base fares")
