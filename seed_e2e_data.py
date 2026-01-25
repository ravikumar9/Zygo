#!/usr/bin/env python
"""
Seed script for E2E test data
Creates properties, bookings, payouts, etc. for Playwright tests
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import timedelta

User = get_user_model()

from hotels.models import Hotel, RoomType, RoomImage, RoomMealPlan, MealPlan
from bookings.models import Booking, HotelBooking
from payments.models import Invoice
from finance.models import OwnerPayout
from property_owners.models import PropertyOwner, Property, PropertyType
from core.models import City

@transaction.atomic
def seed_data():
    print("\n🌱 Seeding E2E test data...\n")
    
    # 1. Create admin-visible properties
    print("📍 Creating test properties...")
    
    # Get or create city
    city, _ = City.objects.get_or_create(name='Delhi', defaults={'state': 'Delhi', 'country': 'India'})
    
    owner = User.objects.filter(email='owner@test.com').first()
    if not owner:
        owner = User.objects.create_user(
            username='owner_test',
            email='owner@test.com',
            password='ownerpass123'
        )
    owner.email_verified = True
    owner.email_verified_at = owner.email_verified_at or timezone.now()
    owner.is_active = True
    owner.save(update_fields=['email_verified', 'email_verified_at', 'is_active'])

    admin_user = User.objects.filter(email='admin@test.com').first()
    if not admin_user:
        admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='adminpass123'
        )
    else:
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password('adminpass123')
        admin_user.save()
    
    # Create PropertyOwner profile
    property_type = PropertyType.objects.first() or PropertyType.objects.create(name='homestay', description='Default')
    po, _ = PropertyOwner.objects.get_or_create(
        user=owner,
        defaults={
            'business_name': 'Test Hotel Owner',
            'verification_status': 'verified',
            'city': city,
            'property_type': property_type,
            'owner_name': 'Owner Test',
            'owner_phone': '9999999999',
            'owner_email': owner.email,
            'address': '123 Main St',
            'pincode': '110001',
        }
    )
    
    # Create approved hotel
    property_obj, _ = Property.objects.update_or_create(
        pk=1,
        defaults={
            'owner': po,
            'name': 'Cozy Delhi Apartment',
            'description': 'Seeded property for Playwright E2E',
            'property_type': property_type,
            'city': city,
            'address': '123 Test St, Test City',
            'contact_phone': '9999999999',
            'contact_email': owner.email,
            'base_price': Decimal('3000.00'),
            'status': 'APPROVED',
        }
    )

    hotel, _ = Hotel.objects.update_or_create(
        pk=1,
        defaults={
            'name': 'E2E Test Hotel',
            'city': city,
            'owner': owner,
            'description': 'Test hotel for Playwright E2E',
            'address': '123 Test St, Test City',
            'contact_phone': '9999999999',
            'contact_email': owner.email,
            'owner_property': property_obj,
            'hourly_stays_enabled': False,
        }
    )
    hotel.is_active = True
    hotel.save()
    print(f"  ✓ Hotel: {hotel.name} (active={hotel.is_active})")
    
    # Create room with images
    room, _ = RoomType.objects.update_or_create(
        pk=1,
        defaults={
                'hotel': hotel,
                'name': 'DELUXE',
                'base_price': Decimal('3000.00'),
            'description': 'Deluxe room with sea view',
            'room_type': 'deluxe',
            'max_adults': 2,
            'max_children': 0,
            'max_occupancy': 2,
            'bed_type': 'queen',
            'number_of_beds': 1,
            'room_size': 300,
            'supports_hourly': False,
        }
    )
    room.hotel = hotel
    room.save(update_fields=['hotel'])
    print(f"  ✓ RoomType: {room.name} (occupancy={room.max_occupancy})")
    
    # Create room image
    img, _ = RoomImage.objects.get_or_create(
        room_type=room,
        defaults={
            'image': 'room_placeholder.svg',
            'is_primary': True,
        }
    )
    print(f"  ✓ Room image: {img.image}")
    
    # Create meal plans
    meal_plans_config = [
        {'id': 1, 'name': 'Room Only', 'type': 'room_only', 'inclusions': []},
        {'id': 2, 'name': 'Breakfast', 'type': 'breakfast', 'inclusions': ['Breakfast']},
        {'id': 3, 'name': 'Half Board', 'type': 'half_board', 'inclusions': ['Breakfast', 'Dinner']},
        {'id': 4, 'name': 'Full Board', 'type': 'full_board', 'inclusions': ['Breakfast', 'Lunch', 'Dinner']},
    ]
    mp_list = []
    for cfg in meal_plans_config:
        mp, _ = MealPlan.objects.update_or_create(
            pk=cfg['id'],
            defaults={'name': cfg['name'], 'plan_type': cfg['type'], 'inclusions': cfg['inclusions']}
        )
        mp_list.append(mp)
        print(f"  ✓ Meal plan: {mp.name}")
    
    # Link meal plans to room
    for mp in mp_list:
        RoomMealPlan.objects.get_or_create(room_type=room, meal_plan=mp, defaults={'price_delta': Decimal('0')})
    
    # 2. Create test bookings and invoices for payout testing
    print("\n💰 Creating test bookings and invoices...")
    customer = User.objects.filter(email='customer_phase4@test.com').first()
    if not customer:
        customer = User.objects.create_user(
            username='customer_phase4',
            email='customer_phase4@test.com',
            password='TestPass123!@'
        )
    
    # Create multiple bookings
    for i in range(3):
        check_in = timezone.now().date() + timedelta(days=i+1)
        check_out = check_in + timedelta(days=2)

        booking, created = Booking.objects.get_or_create(
            booking_type='hotel',
            status='confirmed',
            booking_source='internal',
            user=customer,
            defaults={
                'total_amount': Decimal('5000.00'),
                'paid_amount': Decimal('5000.00'),
                'customer_name': 'Test Customer',
                'customer_email': customer.email,
                'customer_phone': '9999999999',
                'confirmed_at': timezone.now(),
                'total_amount': Decimal('5000.00'),
                'paid_amount': Decimal('5000.00'),
            }
        )
        # Ensure required fields if existing booking reused
        booking.total_amount = booking.total_amount or Decimal('5000.00')
        booking.paid_amount = booking.paid_amount or Decimal('5000.00')
        booking.customer_name = booking.customer_name or 'Test Customer'
        booking.customer_email = booking.customer_email or customer.email
        booking.customer_phone = booking.customer_phone or '9999999999'
        booking.status = 'confirmed'
        booking.booking_type = 'hotel'
        booking.booking_source = 'internal'
        booking.confirmed_at = booking.confirmed_at or timezone.now()
        booking.save()

        HotelBooking.objects.get_or_create(
            booking=booking,
            defaults={
                'room_type': room,
                'check_in': check_in,
                'check_out': check_out,
                'number_of_rooms': 1,
                'number_of_adults': 2,
                'number_of_children': 0,
                'total_nights': (check_out - check_in).days,
            }
        )

        if created:
            print(f"  ✓ Booking {i+1}: {booking.id} ({booking.status})")
        
        # Create invoice snapshot
        if not hasattr(booking, 'invoice'):
            invoice = Invoice.create_for_booking(booking)
            invoice.paid_amount = booking.paid_amount
            invoice.total_amount = booking.total_amount
            invoice.subtotal = booking.total_amount
            invoice.save()
            print(f"  ✓ Invoice: {invoice.invoice_number}")
        
        # Create payout
        OwnerPayout.objects.get_or_create(
            booking=booking,
            hotel=hotel,
            owner=owner,
            defaults={
                'gross_booking_value': booking.total_amount,
                'platform_service_fee': Decimal('250.00'),
                'refunds_issued': Decimal('0.00'),
                'penalties': Decimal('0.00'),
                'net_payable_to_owner': booking.total_amount - Decimal('250.00'),
                'booking_status': booking.status,
                'settlement_status': 'pending',
                'bank_account_name': 'Test Owner',
                'bank_account_number': '1234567890',
                'bank_ifsc': 'TEST0001',
            }
        )
        if created:
            print(f"  ✓ Payout seeded for booking {booking.id}")
    
    print("\n✅ Seed data created successfully!")
    print(f"  Hotels: {Hotel.objects.filter(is_active=True).count()}")
    print(f"  Bookings: {Booking.objects.count()}")
    print(f"  Invoices: {Invoice.objects.count()}")
    print(f"  Payouts: {OwnerPayout.objects.count()}\n")

if __name__ == '__main__':
    try:
        seed_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
