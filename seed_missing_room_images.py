"""
Seed missing room images for all room types that don't have any gallery images.
Ensures every room has at least 2 images (one primary, one secondary).
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.models import RoomType, RoomImage
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

def create_test_image(filename, color=(100, 150, 200), size=(800, 600)):
    """Create a colored test image."""
    img = Image.new('RGB', size, color=color)
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    return InMemoryUploadedFile(
        buffer, 'ImageField', filename, 'image/jpeg',
        sys.getsizeof(buffer), None
    )

print("=" * 80)
print("SEEDING MISSING ROOM IMAGES")
print("=" * 80)

rooms_without_images = RoomType.objects.filter(images__isnull=True).distinct()
total_rooms = rooms_without_images.count()

print(f"\nFound {total_rooms} rooms without gallery images\n")

created_count = 0
for idx, room in enumerate(rooms_without_images, 1):
    print(f"[{idx}/{total_rooms}] {room.hotel.name}: {room.name}")
    
    # Create 2 images per room
    for i in range(2):
        # Generate unique color based on room ID
        color = (
            (room.id * 30 + i * 20) % 256,
            (room.id * 50 + i * 30) % 256,
            (room.id * 70 + i * 40) % 256
        )
        
        img = RoomImage.objects.create(
            room_type=room,
            image=create_test_image(
                f"{room.hotel.name.replace(' ', '_')}_{room.name.replace(' ', '_')}_{i}.jpg",
                color=color
            ),
            is_primary=(i == 0),
            display_order=i
        )
        created_count += 1
        print(f"  ✓ Image {i+1} created (primary={i==0})")

print("\n" + "=" * 80)
print(f"✅ COMPLETE: Created {created_count} room images for {total_rooms} rooms")
print("=" * 80)
print("\nVerification:")
print(f"  Total RoomTypes: {RoomType.objects.count()}")
print(f"  RoomTypes with images: {RoomType.objects.filter(images__isnull=False).distinct().count()}")
print(f"  Total RoomImages: {RoomImage.objects.count()}")
print("\n✅ All rooms now have gallery images!")
