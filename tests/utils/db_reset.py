"""Deterministic DB reset + seed helpers for tests.
Run programmatically in CI or local test setup.
"""
from django.core.management import call_command


def reset_and_seed(env: str = "local", clear: bool = True) -> None:
    """Flush DB, run migrations, and seed canonical data.

    env: "local" or "server" (passed to unified seed command)
    clear: whether to clear domain tables before seeding
    """
    # Remove all data
    call_command("flush", interactive=False)
    # Recreate schema
    call_command("migrate", interactive=False)
    # Seed deterministic dataset (hotels, buses, packages, wallets)
    args = ["--env", env]
    if clear:
        args.append("--clear")
    call_command("seed_all", *args)
