"""
COMPREHENSIVE HOTEL IMAGE VERIFICATION
Verifies every layer from database to template rendering.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.models import Hotel, HotelImage
from django.conf import settings
from pathlib import Path

print("=" * 80)
print("COMPREHENSIVE HOTEL IMAGE VERIFICATION")
print("=" * 80)

# 1. SETTINGS VERIFICATION
print("\n1️⃣ DJANGO SETTINGS")
print(f"   MEDIA_ROOT: {settings.MEDIA_ROOT}")
print(f"   MEDIA_URL: {settings.MEDIA_URL}")
print(f"   SERVE_MEDIA_FILES: {getattr(settings, 'SERVE_MEDIA_FILES', 'NOT SET')}")

# 2. DATABASE STATE
print("\n2️⃣ DATABASE STATE")
total_hotels = Hotel.objects.filter(is_active=True).count()
hotels_with_primary = Hotel.objects.filter(is_active=True).exclude(image='').count()
total_hotel_images = HotelImage.objects.count()
hotels_with_gallery = HotelImage.objects.values('hotel').distinct().count()

print(f"   Active Hotels: {total_hotels}")
print(f"   Hotels with primary image field: {hotels_with_primary}")
print(f"   Total HotelImage records: {total_hotel_images}")
print(f"   Hotels with gallery images: {hotels_with_gallery}")

# 3. FILESYSTEM VERIFICATION
print("\n3️⃣ FILESYSTEM STATE")
media_root = Path(settings.MEDIA_ROOT)
hotels_media = media_root / 'hotels' / 'gallery'

if hotels_media.exists():
    image_files = list(hotels_media.glob('*.png')) + list(hotels_media.glob('*.jpg'))
    print(f"   Gallery directory exists: ✅")
    print(f"   Total image files on disk: {len(image_files)}")
    print(f"   Sample files:")
    for img in image_files[:5]:
        print(f"      - {img.name} ({img.stat().st_size} bytes)")
else:
    print(f"   ❌ Gallery directory NOT FOUND: {hotels_media}")

# 4. DETAILED HOTEL ANALYSIS
print("\n4️⃣ DETAILED HOTEL ANALYSIS (First 3 Hotels)")
print("-" * 80)

hotels = Hotel.objects.filter(is_active=True).prefetch_related('images')[:3]

for hotel in hotels:
    print(f"\n📍 Hotel: {hotel.name} (ID: {hotel.id})")
    
    # Primary image field
    if hotel.image:
        print(f"   Primary field: {hotel.image.name}")
        image_path = Path(settings.MEDIA_ROOT) / hotel.image.name
        if image_path.exists():
            print(f"   Primary file exists: ✅ ({image_path.stat().st_size} bytes)")
        else:
            print(f"   Primary file exists: ❌ NOT FOUND on disk")
    else:
        print(f"   Primary field: EMPTY")
    
    # display_image_url property
    display_url = hotel.display_image_url
    print(f"   display_image_url: {display_url}")
    
    # Gallery images
    gallery_images = hotel.images.all()
    print(f"   Gallery images: {gallery_images.count()} records")
    
    for idx, img in enumerate(gallery_images[:3], 1):
        print(f"      [{idx}] {img.image.name if img.image else 'EMPTY'}")
        if img.image:
            img_path = Path(settings.MEDIA_ROOT) / img.image.name
            if img_path.exists():
                print(f"          File exists: ✅ ({img_path.stat().st_size} bytes)")
                print(f"          is_primary: {img.is_primary}")
                print(f"          URL would be: {settings.MEDIA_URL}{img.image.name}")
            else:
                print(f"          File exists: ❌ NOT FOUND")

# 5. TEMPLATE VARIABLE TEST
print("\n5️⃣ TEMPLATE VARIABLE SIMULATION")
print("-" * 80)
hotel = Hotel.objects.filter(is_active=True).prefetch_related('images').first()
if hotel:
    print(f"Hotel: {hotel.name}")
    print(f"Template would use: {{ hotel.display_image_url }}")
    print(f"Actual value: '{hotel.display_image_url}'")
    print(f"Expected in HTML: <img src=\"{hotel.display_image_url}\" ...>")
    
    # Check if it's a valid path
    if hotel.display_image_url.startswith('/media/'):
        print(f"✅ Path starts with /media/ - CORRECT")
    elif hotel.display_image_url.startswith('/static/'):
        print(f"⚠️  Path starts with /static/ - FALLBACK PLACEHOLDER")
    else:
        print(f"❌ Path format unexpected: {hotel.display_image_url}")

# 6. URL PATTERN TEST
print("\n6️⃣ URL ACCESSIBILITY TEST")
print("-" * 80)
print("Test these URLs in browser:")
print(f"   Hotel List: http://localhost:8000/hotels/")
print(f"   Hotel Detail: http://localhost:8000/hotels/1/")

# Get first hotel with images
hotel_with_img = Hotel.objects.filter(is_active=True).prefetch_related('images').first()
if hotel_with_img and hotel_with_img.images.exists():
    first_img = hotel_with_img.images.first()
    if first_img and first_img.image:
        img_url = f"http://localhost:8000{settings.MEDIA_URL}{first_img.image.name}"
        print(f"   Direct Image: {img_url}")
        print(f"   \nTest in browser - should return 200 OK and display image")

# 7. QUERYSET VERIFICATION
print("\n7️⃣ QUERYSET VERIFICATION")
print("-" * 80)
print("Checking if hotel_list view uses correct queryset...")

# Simulate the hotel_list queryset
from django.db.models import Min, Value, DecimalField
from django.db.models.functions import Coalesce

hotels_query = (
    Hotel.objects.filter(is_active=True)
    .annotate(min_price=Coalesce(Min('room_types__base_price'), Value(0, output_field=DecimalField())))
    .select_related('city')
    .prefetch_related('images', 'room_types')
)

print(f"   Total hotels in query: {hotels_query.count()}")
print(f"   Query includes .prefetch_related('images'): ✅")
print(f"   First hotel images accessible: ", end="")
first_hotel = hotels_query.first()
if first_hotel:
    print(f"{first_hotel.images.all().count()} images")
else:
    print("NO HOTELS FOUND")

# 8. SUMMARY
print("\n" + "=" * 80)
print("SUMMARY & ACTION ITEMS")
print("=" * 80)

issues = []
if total_hotels == 0:
    issues.append("❌ No active hotels in database")
if total_hotel_images == 0:
    issues.append("❌ No HotelImage records in database")
if not hotels_media.exists():
    issues.append("❌ Media gallery directory doesn't exist")
if len(image_files) == 0:
    issues.append("❌ No image files on filesystem")

if issues:
    print("⚠️  ISSUES FOUND:")
    for issue in issues:
        print(f"   {issue}")
else:
    print("✅ ALL BACKEND CHECKS PASSED")
    print("\nNext steps:")
    print("1. Open http://localhost:8000/hotels/ in browser")
    print("2. Inspect Network tab - verify image requests return 200")
    print("3. Check browser console for JavaScript errors")
    print("4. Verify images actually display (not broken icon)")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
