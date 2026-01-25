#!/usr/bin/env python
"""
BUS BOOKING SNAPSHOT POPULATION
Fix existing bookings that have empty snapshot fields
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from bookings.models import BusBooking
from buses.models import BusSchedule

print("=" * 80)
print("POPULATING BUS BOOKING SNAPSHOTS")
print("=" * 80)

bus_bookings = BusBooking.objects.all()
print(f"\nTotal bus bookings: {bus_bookings.count()}")

# Find empty snapshots
empty_snapshots = bus_bookings.filter(operator_name='')
print(f"Bus bookings with empty snapshots: {empty_snapshots.count()}")

if empty_snapshots.exists():
    print("\nPopulating snapshots...")
    updated_count = 0
    
    for bb in empty_snapshots:
        try:
            schedule = bb.bus_schedule
            operator = schedule.route.bus.operator if schedule.route.bus.operator else None
            
            # Extract snapshot data
            operator_name = operator.name if operator else 'Unknown'
            contact_phone = operator.contact_phone if operator else ''
            bus_name = schedule.route.bus.bus_number
            route = schedule.route
            route_name = f"{route.source_city.name} to {route.destination_city.name}"
            departure_time_snapshot = route.departure_time.strftime('%H:%M') if route.departure_time else ''
            
            # Update the booking
            bb.operator_name = operator_name
            bb.contact_phone = contact_phone
            bb.bus_name = bus_name
            bb.route_name = route_name
            bb.departure_time_snapshot = departure_time_snapshot
            bb.save()
            
            updated_count += 1
            print(f"  Updated BusBooking {bb.id}: {bus_name} ({operator_name})")
        except Exception as e:
            print(f"  ERROR updating BusBooking {bb.id}: {str(e)}")
    
    print(f"\nUpdated {updated_count} / {empty_snapshots.count()} bookings")
else:
    print("  All snapshots already populated")

print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

bus_bookings = BusBooking.objects.all()
for bb in bus_bookings:
    print(f"BusBooking {bb.id}: {bb.bus_name} ({bb.operator_name}) -> {bb.route_name}")

print("\nDONE")
