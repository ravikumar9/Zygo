#!/usr/bin/env python
import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.conf import settings
from hotels.models import HotelImage
from PIL import Image
from io import BytesIO

# Create media/hotels directory if it doesn't exist
media_root = Path(settings.MEDIA_ROOT)
hotels_dir = media_root / 'hotels'
hotels_dir.mkdir(parents=True, exist_ok=True)

print(f"Creating placeholder images in: {hotels_dir}\n")

# Get all HotelImages with missing files
missing_images = HotelImage.objects.filter(image='')

print(f"Total HotelImages with missing files: {missing_images.count()}\n")

# Create placeholder image for each
from django.core.files.base import ContentFile
for hotel_image in missing_images:
    # Generate a simple colored placeholder image
    img = Image.new('RGB', (300, 200), color=(73, 109, 137))  # Blue-grey
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Set image name based on hotel_id and is_primary
    prefix = 'primary' if hotel_image.is_primary else 'gallery'
    filename = f"hotel_{hotel_image.hotel_id}_{prefix}_{hotel_image.id}.png"
    
    # Save to model
    hotel_image.image.save(
        filename,
        ContentFile(img_bytes.getvalue()),
        save=True
    )
    
    print(f"✓ {filename} created for Hotel {hotel_image.hotel_id}")

print(f"\n✓ All {missing_images.count()} images created successfully")

# Verify
hotels_with_images = HotelImage.objects.exclude(image='').count()
print(f"✓ HotelImages with files: {hotels_with_images}")
