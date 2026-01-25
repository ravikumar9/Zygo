"""Fetch real images from internet for hotels and rooms"""
import os
import requests
from pathlib import Path
import time


def download_image(url, save_path):
    """Download image from URL to local path"""
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def seed_hotel_images():
    """Seed real hotel images from internet"""
    base_dir = Path(__file__).resolve().parent
    media_dir = base_dir / 'media'
    hotels_dir = media_dir / 'hotels'
    hotels_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample hotel images from Unsplash (public domain)
    hotel_image_urls = [
        # Luxury hotels
        'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=800&h=600&fit=crop',
        # Modern hotels
        'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1582719508461-905c673771fd?w=800&h=600&fit=crop',
        # Budget hotels
        'https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1584132967334-10e028bd69f7?w=800&h=600&fit=crop',
    ]
    
    image_id = 0
    for hotel_id in range(1, 11):  # Hotels 1-10
        for img_num in range(3):  # 3 images per hotel
            if image_id < len(hotel_image_urls):
                url = hotel_image_urls[image_id]
                save_path = hotels_dir / f'hotel_{hotel_id}_{img_num}.jpg'
                
                print(f"Downloading hotel_{hotel_id}_{img_num}.jpg...")
                if download_image(url, save_path):
                    print(f"✓ Saved to {save_path}")
                else:
                    print(f"✗ Failed to download hotel_{hotel_id}_{img_num}.jpg")
                
                image_id += 1
                time.sleep(0.5)  # Rate limiting


def seed_room_images():
    """Seed real room images from internet"""
    base_dir = Path(__file__).resolve().parent
    media_dir = base_dir / 'media'
    rooms_dir = media_dir / 'rooms'
    rooms_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample room images from Unsplash (public domain)
    room_image_urls = [
        # Luxury rooms
        'https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1594560913095-8cf34bda897b?w=800&h=600&fit=crop',
        # Deluxe rooms
        'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1611874102049-6f2d8c1a9a48?w=800&h=600&fit=crop',
        # Standard rooms
        'https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1598928506311-c55ded91a20c?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1560448204-603b3fc33ddc?w=800&h=600&fit=crop',
        # Budget rooms
        'https://images.unsplash.com/photo-1617104678098-de229db51175?w=800&h=600&fit=crop',
        'https://images.unsplash.com/photo-1595432930244-5c69c291ecad?w=800&h=600&fit=crop',
    ]
    
    image_id = 0
    for room_id in range(1, 100):  # Rooms 1-99
        for img_num in range(2):  # 2 images per room
            if image_id < len(room_image_urls):
                url = room_image_urls[image_id % len(room_image_urls)]
                save_path = rooms_dir / f'room_{room_id}_{img_num}.jpg'
                
                if not save_path.exists():
                    print(f"Downloading room_{room_id}_{img_num}.jpg...")
                    if download_image(url, save_path):
                        print(f"✓ Saved to {save_path}")
                    else:
                        print(f"✗ Failed to download room_{room_id}_{img_num}.jpg")
                    
                    image_id += 1
                    time.sleep(0.3)  # Rate limiting
                else:
                    image_id += 1


if __name__ == '__main__':
    print("=" * 60)
    print("SEEDING REAL IMAGES FROM INTERNET")
    print("=" * 60)
    
    print("\n[1/2] Downloading hotel images...")
    seed_hotel_images()
    
    print("\n[2/2] Downloading room images...")
    seed_room_images()
    
    print("\n" + "=" * 60)
    print("✓ IMAGE SEEDING COMPLETE")
    print("=" * 60)
