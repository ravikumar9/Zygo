"""
Create visible placeholder images for hotels with distinct colors and text.
Replaces blank 1KB PNGs with 50-100KB visible images.
"""
import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from PIL import Image, ImageDraw, ImageFont
from hotels.models import Hotel, HotelImage

# Configuration
MEDIA_ROOT = Path(__file__).parent / 'media'
GALLERY_DIR = MEDIA_ROOT / 'hotels' / 'gallery'
IMAGE_SIZE = (800, 600)  # Decent size for web
QUALITY = 85  # JPEG quality

# Color palette for different hotels (vibrant, distinct colors)
COLORS = [
    '#FF6B6B',  # Red
    '#4ECDC4',  # Teal
    '#45B7D1',  # Blue
    '#FFA07A',  # Orange
    '#98D8C8',  # Mint
    '#F7DC6F',  # Yellow
    '#BB8FCE',  # Purple
    '#85C1E2',  # Sky Blue
    '#F8B88B',  # Peach
    '#AAB7B8',  # Gray
    '#EC7063',  # Pink
    '#52BE80',  # Green
    '#5DADE2',  # Light Blue
    '#F39C12',  # Dark Orange
    '#8E44AD',  # Dark Purple
    '#16A085',  # Dark Teal
    '#E74C3C',  # Dark Red
    '#3498DB',  # Medium Blue
    '#2ECC71',  # Lime Green
    '#E67E22',  # Burnt Orange
    '#9B59B6',  # Violet
]

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_hotel_image(hotel_name, hotel_id, color, image_type='primary'):
    """Create a visible placeholder image with hotel name and color"""
    
    # Create image with colored background
    img = Image.new('RGB', IMAGE_SIZE, hex_to_rgb(color))
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fallback to default
    try:
        title_font = ImageFont.truetype("arial.ttf", 60)
        subtitle_font = ImageFont.truetype("arial.ttf", 30)
        label_font = ImageFont.truetype("arial.ttf", 24)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
    
    # Add decorative border
    border_width = 20
    border_color = (255, 255, 255)
    draw.rectangle(
        [(border_width, border_width), 
         (IMAGE_SIZE[0] - border_width, IMAGE_SIZE[1] - border_width)],
        outline=border_color,
        width=border_width
    )
    
    # Add hotel name (centered)
    text = hotel_name[:30]  # Limit length
    bbox = draw.textbbox((0, 0), text, font=title_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (IMAGE_SIZE[0] - text_width) // 2
    y = (IMAGE_SIZE[1] - text_height) // 2 - 50
    
    # Add text shadow for better readability
    shadow_offset = 3
    draw.text((x + shadow_offset, y + shadow_offset), text, font=title_font, fill=(0, 0, 0, 128))
    draw.text((x, y), text, font=title_font, fill=(255, 255, 255))
    
    # Add hotel ID
    id_text = f"Hotel ID: {hotel_id}"
    bbox = draw.textbbox((0, 0), id_text, font=subtitle_font)
    id_width = bbox[2] - bbox[0]
    id_x = (IMAGE_SIZE[0] - id_width) // 2
    id_y = y + text_height + 30
    draw.text((id_x, id_y), id_text, font=subtitle_font, fill=(255, 255, 255))
    
    # Add image type label at bottom
    type_text = f"Image Type: {image_type.upper()}"
    bbox = draw.textbbox((0, 0), type_text, font=label_font)
    type_width = bbox[2] - bbox[0]
    type_x = (IMAGE_SIZE[0] - type_width) // 2
    type_y = IMAGE_SIZE[1] - 80
    draw.text((type_x, type_y), type_text, font=label_font, fill=(255, 255, 255))
    
    return img

def main():
    print("=" * 80)
    print("CREATING VISIBLE HOTEL IMAGES")
    print("=" * 80)
    
    # Ensure gallery directory exists
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    
    hotels = Hotel.objects.filter(is_active=True).prefetch_related('images')
    print(f"\n📊 Processing {hotels.count()} active hotels...")
    
    total_created = 0
    total_size_kb = 0
    
    for idx, hotel in enumerate(hotels):
        color = COLORS[idx % len(COLORS)]
        hotel_images = hotel.images.all()
        
        print(f"\n🏨 Hotel: {hotel.name} (ID: {hotel.id})")
        print(f"   Color: {color}")
        print(f"   Images in DB: {hotel_images.count()}")
        
        for hotel_image in hotel_images:
            # Determine image type
            if hotel_image.is_primary:
                img_type = 'primary'
            elif hotel_image.caption:
                img_type = hotel_image.caption.lower().replace(' ', '_')
            else:
                img_type = f'gallery_{hotel_image.id}'
            
            # Get file path
            image_path = MEDIA_ROOT / hotel_image.image.name
            
            # Create visible image
            img = create_hotel_image(hotel.name, hotel.id, color, img_type)
            
            # Save as JPEG (better compression, visible size)
            img.save(image_path, 'PNG', quality=QUALITY, optimize=True)
            
            # Get file size
            file_size = image_path.stat().st_size
            file_size_kb = file_size / 1024
            total_size_kb += file_size_kb
            
            print(f"   ✅ Created: {image_path.name} ({file_size_kb:.1f} KB)")
            total_created += 1
    
    avg_size_kb = total_size_kb / total_created if total_created > 0 else 0
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Total images created: {total_created}")
    print(f"📦 Average image size: {avg_size_kb:.1f} KB")
    print(f"💾 Total size: {total_size_kb / 1024:.1f} MB")
    print(f"📁 Location: {GALLERY_DIR}")
    print("\n🎯 Images are now CLEARLY VISIBLE with:")
    print("   - Distinct colors per hotel")
    print("   - Hotel name displayed")
    print("   - Hotel ID shown")
    print("   - Image type labeled")
    print("   - White borders for visibility")
    print("\n✅ READY FOR BROWSER TESTING")

if __name__ == '__main__':
    main()
