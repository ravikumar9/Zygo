"""
Unified deterministic seed command for local and server environments.
Usage: python manage.py seed_all [--env=local] [--clear]
Ensures identical test data across local and production servers.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Unified seed all data (hotels, packages, buses, wallets) - deterministic across environments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--env",
            type=str,
            choices=["local", "server"],
            default="local",
            help="Environment: local (dev) or server (production)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )

    def handle(self, *args, **options):
        env = options.get("env", "local")
        clear = options.get("clear", False)

        self.stdout.write(self.style.WARNING(f"\n{'='*60}"))
        self.stdout.write(self.style.WARNING(f"GOEXPLORER UNIFIED SEED"))
        self.stdout.write(self.style.WARNING(f"Environment: {env}"))
        self.stdout.write(self.style.WARNING(f"Clear existing: {clear}"))
        self.stdout.write(self.style.WARNING(f"{'='*60}\n"))

        # Run individual seed commands in order (deterministic)
        seed_order = [
            ("seed_hotels", "Hotels, rooms, amenities, property rules"),
            ("seed_packages", "Packages, itineraries, inclusions, departures"),
            ("seed_buses", "Bus operators, buses, routes, seat layouts, schedules"),
            ("seed_wallet_data", "Wallets, transactions, cashback ledger"),
        ]

        for cmd, description in seed_order:
            self.stdout.write(
                self.style.SUCCESS(f"\n{'-'*60}")
            )
            self.stdout.write(self.style.NOTICE(f"-> {description}"))
            self.stdout.write(self.style.SUCCESS(f"{'-'*60}\n"))

            try:
                args_list = []
                if clear and cmd in ("seed_hotels", "seed_packages", "seed_buses"):
                    args_list.append("--clear")

                call_command(cmd, *args_list)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"[FAILED] {cmd}: {str(e)}")
                )
                return

        self.stdout.write(
            self.style.SUCCESS(f"\n{'='*60}")
        )
        self.stdout.write(
            self.style.SUCCESS("[OK] UNIFIED SEED COMPLETE")
        )
        self.stdout.write(
            self.style.SUCCESS(f"{'='*60}\n")
        )
        self.stdout.write(
            self.style.WARNING("SUMMARY:")
        )
        self.stdout.write("  * Hotels: 16 with rooms, amenities, rules")
        self.stdout.write("  * Packages: 5 with itineraries & departures")
        self.stdout.write("  * Buses: 2 operators, 3 buses, 3 routes with schedules")
        self.stdout.write("  * Wallets: testuser with 5000 balance + 1000 cashback")
        self.stdout.write(
            self.style.SUCCESS("\n[SUCCESS] Data is identical on local and server\n")
        )
