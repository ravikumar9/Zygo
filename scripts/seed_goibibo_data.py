"""
Seed script for Goibibo-level data models
Creates default MealPlans and PolicyCategories for admin use
"""

from hotels.models import MealPlan, PolicyCategory


def run():
    """Create default meal plans and policy categories"""
    
    print("=" * 60)
    print("SEEDING GOIBIBO-LEVEL DATA")
    print("=" * 60)
    
    # ===== MEAL PLANS =====
    print("\n[1/2] Creating Meal Plans...")
    
    meal_plans_data = [
        {
            'name': 'Room Only',
            'plan_type': 'room_only',
            'description': 'Room accommodation only, no meals included',
            'inclusions': ['Room accommodation only'],
            'is_refundable': True,
            'display_order': 1
        },
        {
            'name': 'Breakfast Included',
            'plan_type': 'breakfast',
            'description': 'Complimentary breakfast for all guests',
            'inclusions': ['Daily breakfast for all guests', 'Room accommodation'],
            'is_refundable': True,
            'display_order': 2
        },
        {
            'name': 'Half Board',
            'plan_type': 'half_board',
            'description': 'Breakfast plus one main meal (lunch or dinner)',
            'inclusions': ['Daily breakfast', 'Lunch or Dinner (your choice)', 'Room accommodation'],
            'is_refundable': True,
            'display_order': 3
        },
        {
            'name': 'Full Board',
            'plan_type': 'full_board',
            'description': 'All three meals included daily',
            'inclusions': ['Daily breakfast', 'Daily lunch', 'Daily dinner', 'Room accommodation'],
            'is_refundable': True,
            'display_order': 4
        },
        {
            'name': 'All Inclusive',
            'plan_type': 'all_inclusive',
            'description': 'All meals, drinks, and selected activities included',
            'inclusions': [
                'All meals (breakfast, lunch, dinner)',
                'Unlimited drinks (alcoholic & non-alcoholic)',
                'Snacks throughout the day',
                'Selected activities and entertainment',
                'Room accommodation'
            ],
            'is_refundable': False,
            'display_order': 5
        }
    ]
    
    created_meals = 0
    for data in meal_plans_data:
        meal_plan, created = MealPlan.objects.get_or_create(
            plan_type=data['plan_type'],
            defaults={
                'name': data['name'],
                'description': data['description'],
                'inclusions': data['inclusions'],
                'is_refundable': data['is_refundable'],
                'display_order': data['display_order']
            }
        )
        if created:
            created_meals += 1
            print(f"   ✓ Created: {meal_plan.get_plan_type_display()}")
        else:
            print(f"   - Exists: {meal_plan.get_plan_type_display()}")
    
    print(f"\nMeal Plans: {created_meals} created, {len(meal_plans_data) - created_meals} already exist")
    
    # ===== POLICY CATEGORIES =====
    print("\n[2/2] Creating Policy Categories...")
    
    categories_data = [
        {
            'category_type': 'must_read',
            'icon_class': 'fas fa-star',
            'display_order': 1
        },
        {
            'category_type': 'guest_profile',
            'icon_class': 'fas fa-users',
            'display_order': 2
        },
        {
            'category_type': 'id_proof',
            'icon_class': 'fas fa-id-card',
            'display_order': 3
        },
        {
            'category_type': 'smoking',
            'icon_class': 'fas fa-smoking-ban',
            'display_order': 4
        },
        {
            'category_type': 'food',
            'icon_class': 'fas fa-utensils',
            'display_order': 5
        },
        {
            'category_type': 'pets',
            'icon_class': 'fas fa-paw',
            'display_order': 6
        },
        {
            'category_type': 'cancellation',
            'icon_class': 'fas fa-undo',
            'display_order': 7
        },
        {
            'category_type': 'checkin_checkout',
            'icon_class': 'fas fa-clock',
            'display_order': 8
        }
    ]
    
    created_cats = 0
    for data in categories_data:
        category, created = PolicyCategory.objects.get_or_create(
            category_type=data['category_type'],
            defaults={
                'icon_class': data['icon_class'],
                'display_order': data['display_order']
            }
        )
        if created:
            created_cats += 1
            print(f"   ✓ Created: {category.get_category_type_display()}")
        else:
            print(f"   - Exists: {category.get_category_type_display()}")
    
    print(f"\nPolicy Categories: {created_cats} created, {len(categories_data) - created_cats} already exist")
    
    print("\n" + "=" * 60)
    print("SEEDING COMPLETE")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Property owners can now select meal plans when adding RoomMealPlan entries")
    print("2. Property owners can create structured policies using the PolicyCategory framework")
    print("3. Admin can approve properties only when they have complete Goibibo-level data")
    print("=" * 60)
