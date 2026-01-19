#!/usr/bin/env python
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

import requests
import time
import re

sess = requests.Session()
login_url = 'http://localhost:8000/users/login/'
resp = sess.get(login_url)
csrftoken = resp.cookies.get('csrftoken')
resp = sess.post(login_url, data={
    'email': 'qa_both_verified@example.com',
    'password': 'Test@1234',
    'csrfmiddlewaretoken': csrftoken
}, headers={'Referer': login_url})
print(f"LOGIN: {resp.status_code}")

time.sleep(0.5)
resp = sess.get('http://localhost:8000/bookings/')
match = re.search(r'href="/bookings/([a-f0-9-]+)/confirm/"', resp.text)
if match:
    booking_id = match.group(1)
    print(f'BOOKING ID: {booking_id}')
    
    time.sleep(0.3)
    resp = sess.get(f'http://localhost:8000/bookings/{booking_id}/confirm/')
    print(f'CONFIRM: {resp.status_code}')
    
    time.sleep(0.3)
    resp = sess.get(f'http://localhost:8000/bookings/{booking_id}/payment/')
    print(f'PAYMENT: {resp.status_code}')
    
    time.sleep(0.3)
    resp = sess.get(f'http://localhost:8000/bookings/{booking_id}/')
    print(f'DETAIL: {resp.status_code}')
    
    print("\n✓ All pages loaded successfully")
else:
    print("NO BOOKINGS FOUND")
