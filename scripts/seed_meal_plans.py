#!/usr/bin/env python
"""
Seed meal plans for all existing room types.
Creates 4 meal plan options for each room type with appropriate pricing.
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from decimal import Decimal
from hotels.models import RoomType, RoomMealPlan


def create_meal_plans():
    """Create meal plans for all room types"""
    room_types = RoomType.objects.all()
    
    if not room_types.exists():
        print("❌ No room types found. Please seed hotels first.")
        return
    
    created_count = 0
    skipped_count = 0
    
    for room_type in room_types:
        base_price = room_type.base_price
        
        # Define meal plan configurations
        # Pricing: Room Only = base, Breakfast = +500, Half Board = +1000, Full Board = +1500
        meal_configs = [
            {
                'plan_type': 'room_only',
                'name': 'Room Only',
                'description': 'Accommodation only, no meals included',
                'price_per_night': base_price,
                'display_order': 1,
            },
            {
                'plan_type': 'room_breakfast',
                'name': 'Room + Breakfast',
                'description': 'Includes complimentary breakfast',
                'price_per_night': base_price + Decimal('500.00'),
                'display_order': 2,
            },
            {
                'plan_type': 'room_half_board',
                'name': 'Room + Breakfast + Dinner',
                'description': 'Includes breakfast and dinner',
                'price_per_night': base_price + Decimal('1000.00'),
                'display_order': 3,
            },
            {
                'plan_type': 'room_full_board',
                'name': 'Room + All Meals',
                'description': 'Includes breakfast, lunch, and dinner',
                'price_per_night': base_price + Decimal('1500.00'),
                'display_order': 4,
            },
        ]
        
        for config in meal_configs:
            # Check if meal plan already exists
            existing = RoomMealPlan.objects.filter(
                room_type=room_type,
                plan_type=config['plan_type']
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            meal_plan = RoomMealPlan.objects.create(
                room_type=room_type,
                **config
            )
            created_count += 1
            print(f"✅ Created: {meal_plan} - ₹{meal_plan.price_per_night}/night")
    
    print(f"\n{'='*60}")
    print(f"✅ Created {created_count} meal plans")
    print(f"⏭️  Skipped {skipped_count} existing meal plans")
    print(f"📊 Total room types: {room_types.count()}")
    print(f"{'='*60}")


if __name__ == '__main__':
    print("🌱 Seeding meal plans for room types...\n")
    create_meal_plans()
