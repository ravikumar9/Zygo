import os
from datetime import date

# Configure Django before importing other Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')

import django
django.setup()

from django.test import Client, RequestFactory
from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth import get_user_model
from bs4 import BeautifulSoup

from hotels.models import Hotel
from bookings.models import Booking
from bookings.admin import BookingAdmin

User = get_user_model()

TEST_PASSWORD = 'TestPassword123!'
EMAIL_VERIFIED_USERNAME = 'qa_email_verified'
BOTH_VERIFIED_USERNAME = 'qa_both_verified'
EMAIL_VERIFIED_EMAIL = 'qa_email_verified@example.com'

results = {}


def login_as(username):
    client = Client()
    ok = client.login(username=username, password=TEST_PASSWORD)
    return client, ok


def check_wallet(client):
    resp = client.get('/payments/wallet/')
    content = resp.content.decode('utf-8', errors='ignore')
    soup = BeautifulSoup(content, 'html.parser')
    has_balance = 'Balance' in content
    has_history = ('Transaction' in content) or ('History' in content)
    broken_url = 'bookings:list' in content
    results['wallet'] = {
        'http_status': resp.status_code,
        'content_type': resp.get('Content-Type', ''),
        'has_balance': has_balance,
        'has_history': has_history,
        'broken_url': broken_url,
    }
    return resp.status_code == 200 and 'text/html' in resp.get('Content-Type', '') and has_balance and has_history and not broken_url


def check_hotels(client):
    list_resp = client.get('/hotels/')
    list_content = list_resp.content.decode('utf-8', errors='ignore')
    list_soup = BeautifulSoup(list_content, 'html.parser')
    has_unavailable_text = ('unavailable' in list_content.lower())
    placeholder_found = 'hotel_placeholder' in list_content

    # Detail page
    detail_status = None
    detail_has_placeholder = False
    detail_unavailable = False
    hotel = Hotel.objects.first()
    if hotel:
        detail_resp = client.get(f'/hotels/{hotel.pk}/')
        detail_status = detail_resp.status_code
        detail_content = detail_resp.content.decode('utf-8', errors='ignore')
        detail_has_placeholder = 'hotel_placeholder' in detail_content
        detail_unavailable = 'unavailable' in detail_content.lower()
    results['hotels'] = {
        'list_status': list_resp.status_code,
        'list_has_unavailable_text': has_unavailable_text,
        'list_has_placeholder': placeholder_found,
        'detail_status': detail_status,
        'detail_has_placeholder': detail_has_placeholder,
        'detail_has_unavailable_text': detail_unavailable,
        'hotel_checked': hotel.pk if hotel else None,
    }
    ok = (
        list_resp.status_code == 200
        and not has_unavailable_text
        and placeholder_found
        and detail_status == 200
        and detail_has_placeholder
        and not detail_unavailable
    )
    return ok


def check_date_picker(client):
    today = date.today().isoformat()
    resp = client.get('/hotels/')
    soup = BeautifulSoup(resp.content.decode('utf-8', errors='ignore'), 'html.parser')
    date_inputs = soup.find_all('input', {'type': 'date'})
    min_ok = False
    for inp in date_inputs:
        min_val = inp.get('min')
        if min_val and min_val >= today:
            min_ok = True
            break
    # Detail page
    detail_ok = False
    hotel = Hotel.objects.first()
    if hotel:
        dresp = client.get(f'/hotels/{hotel.pk}/')
        dsoup = BeautifulSoup(dresp.content.decode('utf-8', errors='ignore'), 'html.parser')
        for inp in dsoup.find_all('input', {'type': 'date'}):
            min_val = inp.get('min')
            if min_val and min_val >= today:
                detail_ok = True
                break
    results['date_picker'] = {
        'list_has_min_today_or_future': min_ok,
        'detail_has_min_today_or_future': detail_ok,
        'today': today,
    }
    return min_ok and detail_ok


def check_login_flow():
    client = Client()
    resp = client.post('/users/login/', {
        'email': EMAIL_VERIFIED_EMAIL,
        'password': TEST_PASSWORD,
    }, follow=True)
    final_url = resp.redirect_chain[-1][0] if resp.redirect_chain else resp.request.get('PATH_INFO', '')
    status_ok = resp.status_code == 200
    to_register = '/users/register' in final_url
    authed = bool(client.session.get('_auth_user_id'))
    results['login_flow'] = {
        'status': resp.status_code,
        'final_url': final_url,
        'redirects_to_register': to_register,
        'authenticated': authed,
    }
    return status_ok and authed and not to_register


def check_admin_rollback():
    admin_user, _ = User.objects.get_or_create(
        username='qa_admin_temp',
        defaults={
            'email': 'qa_admin_temp@example.com',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    if not admin_user.check_password(TEST_PASSWORD):
        admin_user.set_password(TEST_PASSWORD)
        admin_user.save()

    booking = Booking.objects.create(
        user=admin_user,
        booking_type='hotel',
        status='confirmed',
        total_amount=1000,
        paid_amount=1000,
        customer_name='Admin Test',
        customer_email='admin@test.com',
        customer_phone='9999999999',
    )

    factory = RequestFactory()
    req = factory.post('/admin/bookings/booking/')
    req.user = admin_user
    req.session = {}
    messages = FallbackStorage(req)
    setattr(req, '_messages', messages)

    admin_instance = BookingAdmin(Booking, admin.site)
    admin_instance.soft_delete_action(req, Booking.objects.filter(pk=booking.pk))
    deleted = Booking.objects.get(pk=booking.pk)
    admin_instance.restore_deleted_bookings(req, Booking.objects.filter(pk=booking.pk))
    restored = Booking.objects.get(pk=booking.pk)

    results['admin_rollback'] = {
        'soft_deleted': deleted.is_deleted,
        'restored': not restored.is_deleted,
        'final_status': restored.status,
    }
    return deleted.is_deleted and not restored.is_deleted


if __name__ == '__main__':
    # Wallet with both-verified user
    client, login_ok = login_as(BOTH_VERIFIED_USERNAME)
    wallet_ok = login_ok and check_wallet(client)

    # Hotel checks using logged-in client
    hotels_ok = check_hotels(client)

    # Date picker
    date_picker_ok = check_date_picker(client)

    # Login flow using login view (email-verified only user)
    login_flow_ok = check_login_flow()

    # Admin rollback simulation via admin actions
    admin_rollback_ok = check_admin_rollback()

    print("LOCAL UI CHECK RESULTS (seeded data)")
    print({
        'wallet': wallet_ok,
        'hotels': hotels_ok,
        'date_picker': date_picker_ok,
        'login_flow': login_flow_ok,
        'admin_rollback': admin_rollback_ok,
        'details': results,
    })
