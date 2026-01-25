import os
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
import django

django.setup()

from core.models import City, PromoCode
from users.models import User
from payments.models import Wallet
from hotels.models import Hotel, RoomType, RoomMealPlan, MealPlan, RoomAvailability, HotelImage, RoomImage
from django.utils import timezone


def get_or_create_city(name='Bengaluru', state='Karnataka', code='BLR'):
    city, _ = City.objects.get_or_create(
        code=code,
        defaults={'name': name, 'state': state, 'country': 'India'}
    )
    return city


def create_meal_plans():
    plans = [
        ('Room Only', 'room_only', []),
        ('Breakfast Included', 'breakfast', ['Breakfast']),
        ('Half Board', 'half_board', ['Breakfast', 'Lunch/Dinner']),
        ('Full Board', 'full_board', ['Breakfast', 'Lunch', 'Dinner']),
    ]
    created = {}
    order = 0
    for name, code, inclusions in plans:
        mp, _ = MealPlan.objects.get_or_create(
            plan_type=code,
            defaults={'name': name, 'inclusions': inclusions, 'display_order': order, 'is_active': True}
        )
        created[code] = mp
        order += 1
    return created


def create_hotel_with_rooms(city, name, hourly_enabled=False):
    hotel, _ = Hotel.objects.get_or_create(
        name=name,
        city=city,
        defaults={
            'description': 'Trusted property with clean rooms and great service.',
            'address': 'MG Road, Bengaluru',
            'star_rating': 4,
            'review_rating': Decimal('4.3'),
            'review_count': 128,
            'has_wifi': True,
            'has_parking': True,
            'has_restaurant': True,
            'has_ac': True,
            'is_active': True,
            'hourly_stays_enabled': hourly_enabled,
        }
    )
    hotel.hourly_stays_enabled = hourly_enabled
    hotel.save(update_fields=['hourly_stays_enabled'])

    # Budget room
    budget, _ = RoomType.objects.get_or_create(
        hotel=hotel,
        name='Smart Room',
        defaults={
            'room_type': 'standard',
            'description': 'Comfortable room ideal for solo travellers.',
            'max_adults': 2,
            'max_children': 0,
            'max_occupancy': 2,
            'bed_type': 'queen',
            'number_of_beds': 1,
            'room_size': 220,
            'base_price': Decimal('6500'),
            'is_refundable': True,
            'status': 'READY',
            'total_rooms': 5,
            'is_available': True,
            'supports_hourly': hourly_enabled,
            'hourly_price_6h': Decimal('1800') if hourly_enabled else None,
            'hourly_price_12h': Decimal('3200') if hourly_enabled else None,
            'hourly_price_24h': Decimal('6000') if hourly_enabled else None,
        }
    )

    # Premium room
    premium, _ = RoomType.objects.get_or_create(
        hotel=hotel,
        name='Executive Suite',
        defaults={
            'room_type': 'suite',
            'description': 'Spacious suite with living area and premium amenities.',
            'max_adults': 3,
            'max_children': 1,
            'max_occupancy': 4,
            'bed_type': 'king',
            'number_of_beds': 1,
            'room_size': 450,
            'base_price': Decimal('18000'),
            'is_refundable': True,
            'status': 'READY',
            'total_rooms': 2,
            'is_available': True,
            'supports_hourly': hourly_enabled,
            'hourly_price_6h': Decimal('4500') if hourly_enabled else None,
            'hourly_price_12h': Decimal('8000') if hourly_enabled else None,
            'hourly_price_24h': Decimal('16000') if hourly_enabled else None,
        }
    )

    return hotel, budget, premium


def attach_meal_plans(room: RoomType, plans):
    # Room Only
    RoomMealPlan.objects.get_or_create(
        room_type=room,
        meal_plan=plans['room_only'],
        defaults={'price_delta': Decimal('0'), 'is_default': True, 'is_active': True}
    )
    # Breakfast
    RoomMealPlan.objects.get_or_create(
        room_type=room,
        meal_plan=plans['breakfast'],
        defaults={'price_delta': Decimal('400'), 'is_default': False, 'is_active': True}
    )
    # Half Board
    RoomMealPlan.objects.get_or_create(
        room_type=room,
        meal_plan=plans['half_board'],
        defaults={'price_delta': Decimal('1000'), 'is_default': False, 'is_active': True}
    )
    # Full Board
    RoomMealPlan.objects.get_or_create(
        room_type=room,
        meal_plan=plans['full_board'],
        defaults={'price_delta': Decimal('1700'), 'is_default': False, 'is_active': True}
    )


def seed_availability(room: RoomType, low_stock=False, sold_out=False):
    today = date.today()
    rooms = 2 if low_stock else (0 if sold_out else room.total_rooms)
    price = room.base_price
    RoomAvailability.objects.update_or_create(
        room_type=room,
        date=today,
        defaults={'available_rooms': rooms, 'price': price}
    )


def seed_images(hotel: Hotel, rooms: list[RoomType]):
    # Hotel property images
    for i in range(1, 21):
        HotelImage.objects.get_or_create(
            hotel=hotel,
            display_order=i,
            defaults={
                'caption': f'{hotel.name} Property {i}',
                'is_primary': True if i == 1 else False,
                'category': 'property',
                # Note: In this environment, file upload may not be configured; keep record without actual file
            }
        )
    # Room images
    order = 1
    for rt in rooms:
        for j in range(1, 6):
            RoomImage.objects.get_or_create(
                room_type=rt,
                display_order=j,
                defaults={
                    'is_primary': True if j == 1 else False,
                }
            )


def seed_promo_codes():
    now = timezone.now()
    valid_until = now + timedelta(days=60)
    # Valid code
    PromoCode.objects.update_or_create(
        code='SAVE20',
        defaults={
            'description': '20% OFF up to ₹1000',
            'discount_type': 'percentage',
            'discount_value': Decimal('20'),
            'max_discount_amount': Decimal('1000'),
            'min_booking_amount': Decimal('2000'),
            'applicable_to': 'hotel',
            'valid_from': now,
            'valid_until': valid_until,
            'is_active': True,
        }
    )
    # Invalid code (expired)
    PromoCode.objects.update_or_create(
        code='EXPIRED50',
        defaults={
            'description': 'Expired code',
            'discount_type': 'percentage',
            'discount_value': Decimal('50'),
            'applicable_to': 'hotel',
            'valid_from': now - timedelta(days=90),
            'valid_until': now - timedelta(days=30),
            'is_active': False,
        }
    )


def seed_users_with_wallets():
    # Low balance user
    low_user, _ = User.objects.get_or_create(
        email='low@example.com',
        defaults={'username': 'lowuser'}
    )
    Wallet.objects.update_or_create(
        user=low_user,
        defaults={'balance': Decimal('3000'), 'is_active': True}
    )
    # High balance user
    high_user, _ = User.objects.get_or_create(
        email='high@example.com',
        defaults={'username': 'highuser'}
    )
    Wallet.objects.update_or_create(
        user=high_user,
        defaults={'balance': Decimal('50000'), 'is_active': True}
    )


def main():
    city = get_or_create_city()
    plans = create_meal_plans()

    hotel_hourly, b1, p1 = create_hotel_with_rooms(city, 'GoExplorer Downtown', hourly_enabled=True)
    attach_meal_plans(b1, plans)
    attach_meal_plans(p1, plans)
    seed_availability(b1, low_stock=True)
    seed_availability(p1, sold_out=True)
    seed_images(hotel_hourly, [b1, p1])

    hotel_overnight, b2, p2 = create_hotel_with_rooms(city, 'GoExplorer Lakeside', hourly_enabled=False)
    attach_meal_plans(b2, plans)
    attach_meal_plans(p2, plans)
    seed_availability(b2)
    seed_availability(p2)
    seed_images(hotel_overnight, [b2, p2])

    seed_promo_codes()
    seed_users_with_wallets()

    print('Deterministic UI data seeded successfully.')


if __name__ == '__main__':
    main()
