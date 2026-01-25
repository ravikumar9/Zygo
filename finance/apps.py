"""Finance app for owner payouts, platform ledger, and admin dashboards"""
from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance'
