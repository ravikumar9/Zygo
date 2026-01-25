"""Convenience wrappers to seed canonical datasets during tests.
Uses unified `seed_all` command.
"""
from django.core.management import call_command


def seed_all_local(clear: bool = True):
    args = ["--env", "local"]
    if clear:
        args.append("--clear")
    call_command("seed_all", *args)
