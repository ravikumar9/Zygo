#!/usr/bin/env python
"""
REAL BROWSER BEHAVIOR TESTING - Parse actual HTML responses
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

import requests
from bs4 import BeautifulSoup
import time
import re

# Setup session
sess = requests.Session()
sess.headers.update({'User-Agent': 'Mozilla/5.0 Chrome/120.0'})

BASE_URL = 'http://localhost:8000'
email = 'qa_both_verified@example.com'
password = 'Test@1234'

print("=" * 70)
print("REAL UI BEHAVIOR TESTING - HTML RESPONSE VERIFICATION")
print("=" * 70)

# Login
print("\n[STEP 1] LOGIN")
resp = sess.get(f'{BASE_URL}/users/login/')
soup = BeautifulSoup(resp.text, 'html.parser')
csrf = soup.find('input', {'name': 'csrfmiddlewaretoken'})
csrf_token = csrf['value'] if csrf else None

resp = sess.post(f'{BASE_URL}/users/login/', data={
    'email': email,
    'password': password,
    'csrfmiddlewaretoken': csrf_token
}, headers={'Referer': f'{BASE_URL}/users/login/'})
print(f"✓ Login: {resp.status_code}")

# Get bookings
print("\n[STEP 2] GET BOOKING ID")
resp = sess.get(f'{BASE_URL}/bookings/')
soup = BeautifulSoup(resp.text, 'html.parser')
booking_link = soup.find('a', {'href': re.compile(r'/bookings/[a-f0-9-]+/confirm/')})
booking_id = None
if booking_link:
    match = re.search(r'/bookings/([a-f0-9-]+)/confirm/', booking_link['href'])
    booking_id = match.group(1)
    print(f"✓ Found booking: {booking_id}")
else:
    print("❌ NO BOOKINGS FOUND")
    exit(1)

# Test CONFIRMATION PAGE
print(f"\n[STEP 3] CONFIRMATION PAGE")
resp = sess.get(f'{BASE_URL}/bookings/{booking_id}/confirm/')
print(f"HTTP: {resp.status_code}")

if resp.status_code != 200:
    print(f"❌ FAILED: {resp.status_code}")
    if "error" in resp.text.lower():
        soup = BeautifulSoup(resp.text, 'html.parser')
        error = soup.find(class_='error') or soup.find(class_='alert-danger')
        if error:
            print(f"ERROR: {error.get_text()}")
    exit(1)

soup = BeautifulSoup(resp.text, 'html.parser')

# Extract pricing from HTML
def extract_price(soup, label_text):
    """Extract price value from HTML table"""
    for td in soup.find_all('td'):
        if label_text in td.get_text():
            # Next td should have the value
            parent_row = td.parent
            values = parent_row.find_all('td')
            if len(values) >= 2:
                price_text = values[-1].get_text().strip()
                match = re.search(r'₹([\d,]+\.?\d*)', price_text)
                if match:
                    return float(match.group(1).replace(',', ''))
    return None

base = extract_price(soup, 'Base Amount')
gst = extract_price(soup, 'GST')
total = extract_price(soup, 'Total Payable')

print(f"✓ CONFIRMATION PAGE PRICING:")
print(f"  Base: ₹{base}")
print(f"  GST: ₹{gst}")
print(f"  Total: ₹{total}")

# Check for promo form
promo_form = soup.find('input', {'name': 'promo_code'})
print(f"✓ Promo input: {'YES' if promo_form else 'NO'}")

# Check for wallet
wallet_text = soup.find(text=re.compile(r'Wallet.*Balance'))
print(f"✓ Wallet display: {'YES' if wallet_text else 'NO'}")

# Test PAYMENT PAGE  
print(f"\n[STEP 4] PAYMENT PAGE")
time.sleep(0.5)
resp = sess.get(f'{BASE_URL}/bookings/{booking_id}/payment/')
print(f"HTTP: {resp.status_code}")

if resp.status_code == 403:
    print("✓ 403 Forbidden (correct for certain statuses)")
elif resp.status_code != 200:
    print(f"❌ FAILED: {resp.status_code}")
    soup = BeautifulSoup(resp.text, 'html.parser')
    error = soup.find(class_='error') or soup.find(class_='alert-danger')
    if error:
        print(f"ERROR: {error.get_text()}")
    exit(1)
else:
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    base_p = extract_price(soup, 'Base Amount')
    gst_p = extract_price(soup, 'GST')
    total_p = extract_price(soup, 'Total Payable')
    
    print(f"✓ PAYMENT PAGE PRICING:")
    print(f"  Base: ₹{base_p}")
    print(f"  GST: ₹{gst_p}")
    print(f"  Total: ₹{total_p}")
    
    # Check wallet checkbox
    wallet_check = soup.find('input', {'id': 'useWalletCheck', 'type': 'checkbox'})
    print(f"✓ Wallet checkbox: {'YES' if wallet_check else 'NO'}")
    
    # Check payment button text
    pay_btn = soup.find('span', {'id': 'payment-button-text'})
    if pay_btn:
        btn_text = pay_btn.get_text().strip()
        print(f"✓ Button text: {btn_text}")
    
    # Verify cross-page consistency
    if base == base_p and gst == gst_p and total == total_p:
        print("✅ PRICES MATCH CONFIRM PAGE")
    else:
        print(f"❌ PRICE MISMATCH:")
        print(f"  CONFIRM: Base={base}, GST={gst}, Total={total}")
        print(f"  PAYMENT: Base={base_p}, GST={gst_p}, Total={total_p}")

# Test DETAIL PAGE
print(f"\n[STEP 5] DETAIL PAGE")
time.sleep(0.5)
resp = sess.get(f'{BASE_URL}/bookings/{booking_id}/')
print(f"HTTP: {resp.status_code}")

if resp.status_code != 200:
    print(f"❌ FAILED: {resp.status_code}")
    soup = BeautifulSoup(resp.text, 'html.parser')
    error = soup.find(class_='error') or soup.find(class_='alert-danger')
    if error:
        print(f"ERROR: {error.get_text()}")
    exit(1)

soup = BeautifulSoup(resp.text, 'html.parser')

base_d = extract_price(soup, 'Base Amount')
gst_d = extract_price(soup, 'GST')
total_d = extract_price(soup, 'Total Payable')

print(f"✓ DETAIL PAGE PRICING:")
print(f"  Base: ₹{base_d}")
print(f"  GST: ₹{gst_d}")
print(f"  Total: ₹{total_d}")

# Verify all 3 match
if base == base_p == base_d and gst == gst_p == gst_d and total == total_p == total_d:
    print("✅ ALL 3 PAGES MATCH")
else:
    print(f"❌ MISMATCH ACROSS PAGES")
    print(f"  CONFIRM: Base={base}, GST={gst}, Total={total}")
    print(f"  PAYMENT: Base={base_p}, GST={gst_p}, Total={total_p}")
    print(f"  DETAIL:  Base={base_d}, GST={gst_d}, Total={total_d}")

print("\n" + "=" * 70)
print("✅ UI BEHAVIOR VERIFICATION COMPLETE")
print("=" * 70)
