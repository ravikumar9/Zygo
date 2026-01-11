"""
Alias command to seed wallets matching the requested CLI: `seed_wallets`.
Delegates to existing deterministic `seed_wallet_data` logic.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Seed wallet and cashback test data (alias for seed_wallet_data)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clearing not applicable; alias will just reseed deterministically",
        )

    def handle(self, *args, **options):
        # Existing command is deterministic/idempotent; rerun is safe.
        call_command("seed_wallet_data")
        self.stdout.write(self.style.SUCCESS("✓ Wallets seeded via alias (seed_wallet_data)"))
