"""
Seed realistic multi-image and review data for Phase 3: UI Data Quality & Trust

Creates:
- 5-8 images per hotel (with captions, alt text, display order, exactly 1 primary)
- 3-5 images per bus (exteriors, interiors, seats, amenities)
- 4-6 images per package (destinations, activities)
- Mixed reviews (approved/pending, verified/unverified, various ratings)
- Realistic user verification mix
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from hotels.models import Hotel, HotelImage
from buses.models import Bus, BusImage
from packages.models import Package, PackageImage
from reviews.models import HotelReview, BusReview, PackageReview
import random
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Phase 3: Seed realistic multi-image and review data with moderation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing images and reviews before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing Phase 3 data...')
            HotelImage.objects.all().delete()
            BusImage.objects.all().delete()
            PackageImage.objects.all().delete()
            HotelReview.objects.all().delete()
            BusReview.objects.all().delete()
            PackageReview.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('[OK] Cleared'))

        self.stdout.write('Seeding Phase 3: Multi-image & Reviews...')

        # Create realistic users with mixed verification
        users = self.create_realistic_users()
        
        # Create admin for approvals
        admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                email='admin@goexplorer.com',
                username='admin',
                password='admin123',
                phone='+919876543210'
            )
            admin_user.email_verified = True
            admin_user.phone_verified = True
            admin_user.save()

        # Seed hotel images and reviews
        self.seed_hotel_images_and_reviews(users, admin_user)
        
        # Seed bus images and reviews
        self.seed_bus_images_and_reviews(users, admin_user)
        
        # Seed package images and reviews
        self.seed_package_images_and_reviews(users, admin_user)

        self.stdout.write(self.style.SUCCESS('\n✅ Phase 3 seeding complete!'))

    def create_realistic_users(self):
        """Create mix of verified and unverified users"""
        self.stdout.write('  Creating realistic users...')
        users = []
        
        user_data = [
            {'email': 'john.verified@gmail.com', 'name': 'John Smith', 'phone': '+919876543201', 'email_verified': True, 'phone_verified': True},
            {'email': 'sarah.email@gmail.com', 'name': 'Sarah Johnson', 'phone': '+919876543202', 'email_verified': True, 'phone_verified': False},
            {'email': 'mike.phone@gmail.com', 'name': 'Mike Brown', 'phone': '+919876543203', 'email_verified': False, 'phone_verified': True},
            {'email': 'lisa.none@gmail.com', 'name': 'Lisa Davis', 'phone': '+919876543204', 'email_verified': False, 'phone_verified': False},
            {'email': 'david.verified@gmail.com', 'name': 'David Wilson', 'phone': '+919876543205', 'email_verified': True, 'phone_verified': True},
            {'email': 'emma.email@gmail.com', 'name': 'Emma Taylor', 'phone': '+919876543206', 'email_verified': True, 'phone_verified': False},
        ]
        
        for data in user_data:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'username': data['email'].split('@')[0],
                    'phone': data['phone']
                }
            )
            if created:
                user.set_password('test123')
            user.email_verified = data['email_verified']
            user.phone_verified = data['phone_verified']
            if data['email_verified']:
                user.email_verified_at = timezone.now() - timedelta(days=random.randint(1, 90))
            if data['phone_verified']:
                user.phone_verified_at = timezone.now() - timedelta(days=random.randint(1, 60))
            user.save()
            users.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'    [OK] Created {len(users)} users'))
        return users

    def seed_hotel_images_and_reviews(self, users, admin_user):
        """Seed 5-8 images per hotel + reviews"""
        self.stdout.write('  Seeding hotel images and reviews...')
        
        hotels = Hotel.objects.all()[:10]  # First 10 hotels
        
        hotel_image_captions = [
            ('Exterior view', 'Front view of the hotel building'),
            ('Lobby area', 'Spacious hotel lobby with modern furniture'),
            ('Swimming pool', 'Outdoor swimming pool with sun loungers'),
            ('Deluxe room', 'Luxurious bedroom with king-size bed'),
            ('Restaurant', 'Fine dining restaurant interior'),
            ('Gym facilities', 'Modern fitness center with equipment'),
            ('Spa area', 'Relaxing spa and wellness center'),
            ('Conference hall', 'Professional meeting and conference room'),
        ]
        
        image_count = 0
        review_count = 0
        
        # Import image creation tools
        from django.core.files.base import ContentFile
        from PIL import Image as PILImage
        from io import BytesIO
        
        for hotel in hotels:
            # Create 5-8 images
            num_images = random.randint(5, 8)
            selected_captions = random.sample(hotel_image_captions, num_images)
            
            for i, (caption, alt_text) in enumerate(selected_captions):
                # Create actual image file
                img = PILImage.new('RGB', (400, 300), color=(73, 109, 137))
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                
                filename = f"hotel_{hotel.id}_{'primary' if i == 0 else 'gallery'}_{i}.png"
                
                hotel_image = HotelImage.objects.create(
                    hotel=hotel,
                    caption=caption,
                    alt_text=alt_text,
                    display_order=i,
                    is_primary=(i == 0)  # First image is primary
                )
                
                # Save image file
                hotel_image.image.save(
                    filename,
                    ContentFile(img_bytes.getvalue()),
                    save=True
                )
                image_count += 1
            
            # Create 3-6 reviews with mixed approval status
            num_reviews = random.randint(3, 6)
            for _ in range(num_reviews):
                user = random.choice(users)
                rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 20, 35, 30])[0]  # Weighted towards higher
                
                review = HotelReview.objects.create(
                    hotel=hotel,
                    user=user,
                    review_type='hotel',
                    rating=rating,
                    title=self.get_review_title(rating),
                    comment=self.get_review_comment(rating, 'hotel'),
                    booking=None,  # No booking object for seed data
                    helpful_count=random.randint(0, 25)
                )
                
                # 70% approved, 30% pending
                if random.random() > 0.3:
                    review.is_approved = True
                    review.approved_at = timezone.now() - timedelta(days=random.randint(1, 30))
                    review.approved_by = admin_user
                    review.save(update_fields=['is_approved', 'approved_at', 'approved_by'])
                
                review_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'    [OK] {image_count} hotel images, {review_count} reviews'))

    def seed_bus_images_and_reviews(self, users, admin_user):
        """Seed 3-5 images per bus + reviews"""
        self.stdout.write('  Seeding bus images and reviews...')
        
        buses = Bus.objects.all()[:10]
        
        bus_image_captions = [
            ('Front view', 'Exterior front view of the bus'),
            ('Side view', 'Full side view showing bus branding'),
            ('Seats interior', 'Comfortable seating arrangement'),
            ('AC vents', 'Air conditioning and ventilation'),
            ('Entertainment', 'LED TV and entertainment system'),
        ]
        
        image_count = 0
        review_count = 0
        
        for bus in buses:
            num_images = random.randint(3, 5)
            selected_captions = random.sample(bus_image_captions, num_images)
            
            for i, (caption, alt_text) in enumerate(selected_captions):
                BusImage.objects.create(
                    bus=bus,
                    caption=caption,
                    alt_text=alt_text,
                    display_order=i,
                    is_primary=(i == 0)
                )
                image_count += 1
            
            # Create 2-5 reviews
            num_reviews = random.randint(2, 5)
            for _ in range(num_reviews):
                user = random.choice(users)
                rating = random.choices([1, 2, 3, 4, 5], weights=[10, 10, 25, 30, 25])[0]
                
                review = BusReview.objects.create(
                    bus=bus,
                    user=user,
                    review_type='bus',
                    rating=rating,
                    title=self.get_review_title(rating),
                    comment=self.get_review_comment(rating, 'bus'),
                    booking=None,  # No booking object for seed data
                    helpful_count=random.randint(0, 15)
                )
                
                if random.random() > 0.35:  # 65% approved
                    review.is_approved = True
                    review.approved_at = timezone.now() - timedelta(days=random.randint(1, 45))
                    review.approved_by = admin_user
                    review.save(update_fields=['is_approved', 'approved_at', 'approved_by'])
                
                review_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'    [OK] {image_count} bus images, {review_count} reviews'))

    def seed_package_images_and_reviews(self, users, admin_user):
        """Seed 4-6 images per package + reviews"""
        self.stdout.write('  Seeding package images and reviews...')
        
        packages = Package.objects.all()[:10]
        
        package_image_captions = [
            ('Destination view', 'Scenic view of the main destination'),
            ('Activities', 'Fun activities and experiences'),
            ('Accommodation', 'Comfortable stay arrangements'),
            ('Local cuisine', 'Delicious local food experience'),
            ('Group photo', 'Happy travelers enjoying the trip'),
            ('Landmarks', 'Famous landmarks and attractions'),
        ]
        
        image_count = 0
        review_count = 0
        
        for package in packages:
            num_images = random.randint(4, 6)
            selected_captions = random.sample(package_image_captions, num_images)
            
            for i, (caption, alt_text) in enumerate(selected_captions):
                PackageImage.objects.create(
                    package=package,
                    caption=caption,
                    alt_text=alt_text,
                    display_order=i,
                    is_primary=(i == 0)
                )
                image_count += 1
            
            # Create 2-4 reviews
            num_reviews = random.randint(2, 4)
            for _ in range(num_reviews):
                user = random.choice(users)
                rating = random.choices([1, 2, 3, 4, 5], weights=[5, 5, 15, 40, 35])[0]
                
                review = PackageReview.objects.create(
                    package=package,
                    user=user,
                    review_type='package',
                    rating=rating,
                    title=self.get_review_title(rating),
                    comment=self.get_review_comment(rating, 'package'),
                    booking=None,  # No booking object for seed data
                    helpful_count=random.randint(0, 30)
                )
                
                if random.random() > 0.25:  # 75% approved
                    review.is_approved = True
                    review.approved_at = timezone.now() - timedelta(days=random.randint(1, 60))
                    review.approved_by = admin_user
                    review.save(update_fields=['is_approved', 'approved_at', 'approved_by'])
                
                review_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'    [OK] {image_count} package images, {review_count} reviews'))

    def get_review_title(self, rating):
        """Generate realistic review title based on rating"""
        titles = {
            5: ['Excellent experience!', 'Highly recommended!', 'Perfect stay!', 'Amazing service!'],
            4: ['Very good', 'Great experience', 'Good value for money', 'Comfortable stay'],
            3: ['Decent', 'Average experience', 'Okay for the price', 'Could be better'],
            2: ['Disappointing', 'Not as expected', 'Below average', 'Needs improvement'],
            1: ['Terrible', 'Worst experience', 'Do not book', 'Very poor service']
        }
        return random.choice(titles.get(rating, ['Review']))

    def get_review_comment(self, rating, entity_type):
        """Generate realistic review comment"""
        comments = {
            5: {
                'hotel': 'Absolutely wonderful stay! The staff was incredibly friendly and helpful. Rooms were spotless and very comfortable. The amenities exceeded our expectations. Will definitely return!',
                'bus': 'Excellent bus service! Clean seats, smooth ride, and punctual. The driver was professional and courteous. AC worked perfectly throughout the journey.',
                'package': 'Amazing tour package! Well-organized itinerary, knowledgeable guide, and beautiful destinations. Every day was filled with memorable experiences. Highly recommend!'
            },
            4: {
                'hotel': 'Good hotel with nice facilities. Room was clean and spacious. Staff was helpful. Location is convenient. Minor issues with breakfast timing but overall satisfied.',
                'bus': 'Comfortable journey. Bus was on time and in good condition. Seats were comfortable. Only minor issue was the temperature control.',
                'package': 'Great package with good value. Most activities were excellent. Accommodations were comfortable. Would have liked more free time for exploring on our own.'
            },
            3: {
                'hotel': 'Average stay. Room was okay but could use some maintenance. Service was acceptable. Good for a short stay but nothing special.',
                'bus': 'Decent bus service. Journey was okay overall. Some seats were worn out. Reached on time which was good.',
                'package': 'Okay package but felt rushed. Some destinations were great while others were just so-so. Guide was knowledgeable but not very engaging.'
            },
            2: {
                'hotel': 'Disappointed with the stay. Room cleanliness was poor. Staff was not very responsive. Amenities were not as advertised. Expected much better.',
                'bus': 'Not satisfied with the service. Bus was old and seats uncomfortable. AC was not working properly. Delayed departure.',
                'package': 'Below expectations. Itinerary was poorly planned. Several promised activities were cancelled. Accommodations were substandard.'
            },
            1: {
                'hotel': 'Terrible experience! Room was dirty and had maintenance issues. Staff was rude and unhelpful. Very noisy. Complete waste of money!',
                'bus': 'Worst bus journey ever! Extremely uncomfortable seats, no AC, delayed by hours. Driver was reckless. Avoid at all costs!',
                'package': 'Horrible package! Completely disorganized, guide was unprofessional, accommodations were terrible. Nothing matched the description. Total scam!'
            }
        }
        
        return comments.get(rating, {}).get(entity_type, 'No comment')
