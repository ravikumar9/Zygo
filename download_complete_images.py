"""Download complete image set for all hotels and rooms"""
import requests
from pathlib import Path
import time

# Image URLs from Unsplash (hotel/hospitality themed)
ROOM_IMAGE_URLS = [
    "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1584132967334-10e028bd69f7?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1591088398332-8a7791972843?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1596701062351-8c2c14d1fdd0?w=800&h=600&fit=crop",
]

def download_image(url, filepath):
    """Download image from URL to filepath"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return True
    except:
        pass
    return False

def main():
    base_dir = Path(__file__).parent / 'media'
    rooms_dir = base_dir / 'rooms'
    hotels_dir = base_dir / 'hotels'
    
    # Download room images for room IDs 1-80 (cycle through URLs)
    print("Downloading room images...")
    room_count = 0
    for room_id in range(1, 81):
        for img_num in range(2):  # 2 images per room
            url = ROOM_IMAGE_URLS[(room_id + img_num) % len(ROOM_IMAGE_URLS)]
            filepath = rooms_dir / f'room_{room_id}_{img_num}.jpg'
            if not filepath.exists():
                if download_image(url, filepath):
                    room_count += 1
                    print(f"✓ room_{room_id}_{img_num}.jpg")
                time.sleep(0.1)  # Rate limiting
    
    # Download hotel images for hotel IDs 1-10
    print("\nDownloading hotel images...")
    hotel_count = 0
    for hotel_id in range(1, 11):
        for img_num in range(3):  # 3 images per hotel
            url = ROOM_IMAGE_URLS[(hotel_id + img_num) % len(ROOM_IMAGE_URLS)]
            filepath = hotels_dir / f'hotel_{hotel_id}_{img_num}.jpg'
            if not filepath.exists():
                if download_image(url, filepath):
                    hotel_count += 1
                    print(f"✓ hotel_{hotel_id}_{img_num}.jpg")
                time.sleep(0.1)
    
    print(f"\n✅ Downloaded {room_count} room images and {hotel_count} hotel images")

if __name__ == '__main__':
    main()
