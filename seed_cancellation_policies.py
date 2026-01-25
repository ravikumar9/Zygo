#!/usr/bin/env python
"""
Seed room-level cancellation policies for testing FIX-4.
Creates 3 policies per hotel: FREE, PARTIAL, NON_REFUNDABLE
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.models import RoomType, RoomCancellationPolicy
from django.utils import timezone
from datetime import datetime, timedelta

def seed_policies():
    """Create sample cancellation policies for each room type"""
    
    rooms = RoomType.objects.all()
    
    if not rooms.exists():
        print("❌ No room types found. Please seed hotels and rooms first.")
        return
    
    print(f"📍 Found {rooms.count()} room types. Creating policies...")
    
    policy_count = 0
    
    for idx, room in enumerate(rooms, 1):
        # Skip if policies already exist
        if room.cancellation_policies.exists():
            print(f"  ⊘ Room {room.id} ({room.name}) already has policies, skipping")
            continue
        
        # Determine which policy type based on room index (rotate through 3 types)
        policy_type = ['FREE', 'PARTIAL', 'NON_REFUNDABLE'][idx % 3]
        
        if policy_type == 'FREE':
            policy = RoomCancellationPolicy.objects.create(
                room_type=room,
                policy_type='FREE',
                free_cancel_until=timezone.now() + timedelta(days=365),  # Always free
                refund_percentage=100,
                policy_text='Free cancellation until check-in. 100% refund if cancelled before your arrival.',
                is_active=True
            )
            print(f"  ✅ [{idx}] {room.name}: FREE cancellation (refund_until={policy.free_cancel_until.date()})")
            
        elif policy_type == 'PARTIAL':
            policy = RoomCancellationPolicy.objects.create(
                room_type=room,
                policy_type='PARTIAL',
                free_cancel_until=timezone.now() + timedelta(days=2),  # 48 hours
                refund_percentage=50,
                policy_text='Free cancellation until 48 hours before check-in. After that, 50% refund is applicable.',
                is_active=True
            )
            print(f"  ✅ [{idx}] {room.name}: PARTIAL refund (50% until {policy.free_cancel_until.date()})")
            
        else:  # NON_REFUNDABLE
            policy = RoomCancellationPolicy.objects.create(
                room_type=room,
                policy_type='NON_REFUNDABLE',
                free_cancel_until=None,
                refund_percentage=0,
                policy_text='This is a non-refundable booking. Cancellations are not allowed. No refund will be issued.',
                is_active=True
            )
            print(f"  ✅ [{idx}] {room.name}: NON-REFUNDABLE (0% refund)")
        
        policy_count += 1
    
    print(f"\n✨ Seeded {policy_count} cancellation policies successfully!")
    print("\nSample Policies Created:")
    print("  - Free Cancellation: 100% refund until check-in")
    print("  - Partial Refund: 50% refund until 48h before check-in")
    print("  - Non-Refundable: 0% refund, no cancellations allowed")

if __name__ == '__main__':
    seed_policies()
