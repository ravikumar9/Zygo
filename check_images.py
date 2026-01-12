#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.models import Hotel, HotelImage

print("Hotels:")
for hotel in Hotel.objects.all()[:3]:
    images = HotelImage.objects.filter(hotel=hotel)
    print(f"  {hotel.name}: {images.count()} images")
    for img in images[:2]:
        print(f"    - {img.id}: image={img.image.name if img.image else 'NO FILE'}")
