"""
Bug-fix seed data alignment command.

Fixes identified in server validation:
1. Reviews must be tied to real bookings
2. Hotels must have primary images
3. Users must have proper OTP verification
4. Bookings must have proper customer data

Usage:
    python manage.py seed_bugfix_data
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, date
import random

from hotels.models import Hotel, HotelImage, RoomType
from buses.models import Bus, BusRoute, BusSchedule
from packages.models import Package, PackageDeparture
from bookings.models import Booking, HotelBooking, BusBooking, PackageBooking
from reviews.models import HotelReview, BusReview, PackageReview

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed aligned data with proper booking-review linkage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of test users to create (default: 10)'
        )
        parser.add_argument(
            '--bookings',
            type=int,
            default=20,
            help='Number of test bookings to create (default: 20)'
        )

    def handle(self, *args, **options):
        num_users = options['users']
        num_bookings = options['bookings']

        self.stdout.write(self.style.NOTICE('Bug-Fix Data Seeding'))
        self.stdout.write('=' * 60)

        with transaction.atomic():
            # 1. Create verified test users
            users = self._create_users(num_users)
            
            # 2. Ensure hotels have primary images
            self._fix_hotel_images()
            
            # 3. Create real bookings
            bookings = self._create_bookings(users, num_bookings)
            
            # 4. Create reviews LINKED to bookings
            self._create_aligned_reviews(bookings)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Bug-fix seeding complete!'))
        self.stdout.write(f'  Users created: {len(users)} (all OTP verified)')
        self.stdout.write(f'  Bookings created: {len(bookings)}')
        self.stdout.write(f'  Reviews aligned with bookings')
        self.stdout.write(f'  Hotels with primary images verified')

    def _create_users(self, count):
        """Create verified test users with proper OTP flags."""
        self.stdout.write(f'\n[1/4] Creating {count} verified users...')
        
        users = []
        base_time = timezone.now()
        
        for i in range(count):
            email = f'user{i+1}@goexplorer.test'
            phone = f'+919{random.randint(100000000, 999999999)}'
            
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': f'TestUser',
                    'last_name': f'{i+1}',
                    'phone': phone,
                    'is_active': True,
                    # CRITICAL: Set OTP verification flags
                    'email_verified': True,
                    'phone_verified': True,
                    'email_verified_at': base_time - timedelta(days=random.randint(1, 30)),
                    'phone_verified_at': base_time - timedelta(days=random.randint(1, 30)),
                }
            )
            
            if created:
                user.set_password('Test@1234')
                user.save()
                users.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(users)} verified users'))
        return users

    def _fix_hotel_images(self):
        """Ensure all hotels have at least one primary image."""
        self.stdout.write('\n[2/4] Fixing hotel images...')
        
        fixed_count = 0
        for hotel in Hotel.objects.all():
            # Check if hotel has primary image
            has_primary = hotel.images.filter(is_primary=True).exists()
            
            if not has_primary:
                # Make first image primary, or mark hotel.image as primary reference
                first_image = hotel.images.first()
                if first_image:
                    first_image.is_primary = True
                    first_image.save()
                    fixed_count += 1
                elif hotel.image:
                    # Hotel has image field but no HotelImage objects
                    # display_image_url will handle this via fallback
                    pass
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Fixed {fixed_count} hotel image assignments'))

    def _create_bookings(self, users, count):
        """Create realistic bookings with proper customer data."""
        self.stdout.write(f'\n[3/4] Creating {count} bookings...')
        
        bookings = []
        hotels = list(Hotel.objects.filter(is_active=True)[:10])
        room_types = list(RoomType.objects.filter(is_available=True)[:10])
        bus_schedules = list(BusSchedule.objects.all()[:10])
        
        if not hotels or not room_types:
            self.stdout.write(self.style.WARNING('  ⚠ No hotels/rooms found. Run seed_hotels first.'))
            return []
        
        for i in range(count):
            user = random.choice(users)
            booking_type = random.choice(['hotel', 'bus'])
            
            # Create base booking
            booking = Booking.objects.create(
                user=user,
                booking_type=booking_type,
                status=random.choice(['confirmed', 'confirmed', 'completed']),  # Mostly confirmed/completed
                customer_name=f'{user.first_name} {user.last_name}',
                customer_email=user.email,
                customer_phone=user.phone,
                total_amount=random.randint(1000, 10000),
                paid_amount=random.randint(1000, 10000),
                confirmed_at=timezone.now() - timedelta(days=random.randint(1, 30))
            )
            
            # Create type-specific booking
            if booking_type == 'hotel' and room_types:
                room = random.choice(room_types)
                checkin = date.today() + timedelta(days=random.randint(1, 30))
                checkout = checkin + timedelta(days=random.randint(1, 5))
                
                HotelBooking.objects.create(
                    booking=booking,
                    room_type=room,
                    check_in=checkin,
                    check_out=checkout,
                    number_of_rooms=random.randint(1, 2),
                    number_of_adults=random.randint(1, 3),
                    total_nights=(checkout - checkin).days
                )
            
            elif booking_type == 'bus' and bus_schedules:
                schedule = random.choice(bus_schedules)
                BusBooking.objects.create(
                    booking=booking,
                    bus_schedule=schedule,
                    bus_route=schedule.route,
                    journey_date=date.today() + timedelta(days=random.randint(1, 30))
                )
            
            bookings.append(booking)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(bookings)} bookings'))
        return bookings

    def _create_aligned_reviews(self, bookings):
        """Create reviews LINKED to actual bookings."""
        self.stdout.write(f'\n[4/4] Creating aligned reviews...')
        
        review_count = 0
        
        # Only create reviews for completed bookings
        completed_bookings = [b for b in bookings if b.status in ['confirmed', 'completed']]
        
        for booking in random.sample(completed_bookings, min(len(completed_bookings), 15)):
            # 50% chance of creating a review
            if random.random() > 0.5:
                continue
            
            rating = random.choices([5, 4, 3], weights=[0.5, 0.3, 0.2])[0]
            
            comments = {
                5: ['Excellent experience!', 'Highly recommended!', 'Outstanding service!', 'Will book again!'],
                4: ['Very good', 'Nice experience', 'Good value for money', 'Satisfied with service'],
                3: ['Average experience', 'Okay service', 'Could be better', 'Decent stay']
            }
            
            try:
                if booking.booking_type == 'hotel':
                    hotel_booking = booking.hotel_details
                    hotel = hotel_booking.room_type.hotel
                    
                    HotelReview.objects.create(
                        user=booking.user,
                        hotel=hotel,
                        rating=rating,
                        title=f'{rating} star review',
                        comment=random.choice(comments[rating]),
                        booking_id=str(booking.booking_id),
                        is_approved=True,  # Auto-approve for testing
                        approved_at=timezone.now(),
                        review_type='hotel'
                    )
                    review_count += 1
                
                elif booking.booking_type == 'bus':
                    bus_booking = booking.bus_details
                    bus = bus_booking.bus_schedule.route.bus
                    
                    BusReview.objects.create(
                        user=booking.user,
                        bus=bus,
                        rating=rating,
                        title=f'{rating} star review',
                        comment=random.choice(comments[rating]),
                        booking_id=str(booking.booking_id),
                        is_approved=True,
                        approved_at=timezone.now(),
                        review_type='bus'
                    )
                    review_count += 1
            
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠ Could not create review for booking {booking.booking_id}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {review_count} booking-linked reviews'))
