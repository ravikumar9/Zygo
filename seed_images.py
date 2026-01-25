"""Seed hotel and room images for E2E testing"""

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from hotels.models import Hotel, RoomType, HotelImage, RoomImage

def seed_images():
    print("Seeding hotel and room images...")
    
    hotels = Hotel.objects.filter(is_active=True)
    total_hotel_images = 0
    total_room_images = 0
    
    for hotel in hotels:
        # Create hotel images (using static placeholder paths)
        for i in range(3):
            obj, created = HotelImage.objects.get_or_create(
                hotel=hotel,
                display_order=i,
                defaults={
                    'image': f'hotels/hotel_{hotel.id}_{i}.jpg',  # Static path
                    'is_primary': (i == 0),
                    'alt_text': f'{hotel.name} - Image {i+1}',
                    'caption': f'Hotel view {i+1}'
                }
            )
            if created:
                total_hotel_images += 1
        print(f"✅ Hotel images for {hotel.name}: {HotelImage.objects.filter(hotel=hotel).count()}")
        
        # Create room images
        for room in hotel.room_types.all():
            for i in range(2):
                obj, created = RoomImage.objects.get_or_create(
                    room_type=room,
                    display_order=i,
                    defaults={
                        'image': f'rooms/room_{room.id}_{i}.jpg',  # Static path
                        'is_primary': (i == 0)
                    }
                )
                if created:
                    total_room_images += 1
            print(f"  ✅ Room images for {room.name}: {RoomImage.objects.filter(room_type=room).count()}")
    
    print(f"\n✅ Seeding complete!")
    print(f"   Total hotel images: {total_hotel_images}")
    print(f"   Total room images: {total_room_images}")

if __name__ == '__main__':
    seed_images()
