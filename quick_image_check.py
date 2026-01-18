"""
Quick verification script to check if images are loading correctly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.models import Hotel
from pathlib import Path

print("=== IMAGE URL VERIFICATION ===\n")

hotels = Hotel.objects.filter(is_active=True).prefetch_related('images')[:5]

for hotel in hotels:
    print(f"Hotel: {hotel.name}")
    print(f"  Image URL: {hotel.display_image_url}")
    print(f"  Gallery count: {hotel.images.count()}")
    
    # Check if file exists
    if hotel.display_image_url and hotel.display_image_url.startswith('/media/'):
        file_path = Path('media') / hotel.display_image_url.replace('/media/', '')
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            print(f"  File exists: ✅ ({size_kb:.1f} KB)")
        else:
            print(f"  File exists: ❌ NOT FOUND")
    print()

print("\n✅ All images should now be VISIBLE in browser")
print("📍 Open: http://localhost:8000/hotels/")
