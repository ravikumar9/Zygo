import os, sys
# Ensure project root on sys.path
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from bookings.models import Booking

User = get_user_model()
client = Client()
# Prefer testuser for wallet/cashback
logged_in = client.login(username='testuser', password='testpass123')
print('logged_in:', logged_in)
user = User.objects.filter(username='testuser').first()
booking = Booking.objects.filter(user=user).first()
if not booking and user:
    # Create a minimal booking for payment page rendering
    from decimal import Decimal
    booking = Booking.objects.create(
        user=user,
        booking_type='hotel',
        total_amount=Decimal('2500.00'),
        customer_name='Test User',
        customer_email='testuser@goexplorer.com',
        customer_phone='9876543210',
        status='pending',
    )
print('booking_id:', booking.booking_id if booking else None)
if booking:
    resp = client.get(f'/bookings/{booking.booking_id}/payment/')
    print('status_code:', resp.status_code)
    html = resp.content.decode('utf-8')
    import re
    wallet_match = re.search(r'Wallet Balance[^₹]+₹\s*([0-9,]+\.?[0-9]*)', html)
    cashback_match = re.search(r'Cashback[^₹]+₹\s*([0-9,]+\.?[0-9]*)', html)
    print('wallet_display:', wallet_match.group(1) if wallet_match else 'not found')
    print('cashback_display:', cashback_match.group(1) if cashback_match else 'not found')
else:
    print('No admin booking found')
