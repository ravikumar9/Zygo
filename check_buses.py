#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from buses.models import Bus, BusOperator

print("Buses:")
for b in Bus.objects.all():
    print(f"  {b.id}: {b.bus_number} - {b.bus_name}")
print(f"\nTotal Buses: {Bus.objects.count()}")

print("\nOperators:")
for op in BusOperator.objects.all():
    print(f"  {op.id}: {op.name}")
print(f"\nTotal Operators: {BusOperator.objects.count()}")
