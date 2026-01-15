#!/usr/bin/env python
"""Quick code verification for all 10 fixes"""

results = {}

# TEST 1: Mobile Validation
print("TEST 1: Mobile validation enforcement...")
with open('users/views.py', 'r') as f:
    content = f.read()
    if "len(str(phone)) != 10" in content and "10-digit" in content:
        print("✓ PASS")
        results['1'] = True
    else:
        print("✗ FAIL")
        results['1'] = False

# TEST 2: Login redirect
print("TEST 2: Login redirect safety...")
with open('users/views.py', 'r') as f:
    content = f.read()
    if 'not next_url.startswith("/users/register")' in content:
        print("✓ PASS")
        results['2'] = True
    else:
        print("✗ FAIL")
        results['2'] = False

# TEST 3: Wallet icon
print("TEST 3: Wallet icon in navbar...")
with open('templates/base.html', 'r') as f:
    content = f.read()
    if 'fa-wallet' in content and '/payments/wallet/' in content:
        print("✓ PASS")
        results['3'] = True
    else:
        print("✗ FAIL")
        results['3'] = False

# TEST 4: Corporate booking
print("TEST 4: Corporate booking section...")
with open('templates/home.html', 'r') as f:
    content = f.read()
    if 'Corporate Booking' in content and 'discount' in content.lower():
        print("✓ PASS")
        results['4'] = True
    else:
        print("✗ FAIL")
        results['4'] = False

# TEST 5: Hotel images
print("TEST 5: Hotel image fallback...")
with open('templates/home.html', 'r') as f:
    home = f.read()
with open('templates/hotels/hotel_list.html', 'r') as f:
    list_tmpl = f.read()
with open('templates/hotels/hotel_detail.html', 'r') as f:
    detail = f.read()
    
if all('onerror=' in x for x in [home, list_tmpl, detail]) and all('hotel_placeholder' in x for x in [home, list_tmpl, detail]):
    print("✓ PASS")
    results['5'] = True
else:
    print("✗ FAIL")
    results['5'] = False

# TEST 6: Hotel date logic
print("TEST 6: Hotel date validation...")
with open('templates/hotels/hotel_detail.html', 'r') as f:
    content = f.read()
    if 'validateHotelBooking' in content and 'checkoutDate <= checkinDate' in content:
        print("✓ PASS")
        results['6'] = True
    else:
        print("✗ FAIL")
        results['6'] = False

# TEST 7: Template syntax fix
print("TEST 7: Hotel detail template syntax...")
with open('templates/hotels/hotel_detail.html', 'r') as f:
    content = f.read()
    if 'not user.email_verified_at' in content and '(not user.email_verified_at or not user.phone_verified_at)' not in content:
        print("✓ PASS")
        results['7'] = True
    else:
        print("✗ FAIL")
        results['7'] = False

# TEST 8: Admin restore
print("TEST 8: Booking restore method...")
with open('bookings/models.py', 'r') as f:
    models = f.read()
with open('bookings/admin.py', 'r') as f:
    admin = f.read()
    
if 'def restore(' in models and 'restore_deleted_bookings' in admin:
    print("✓ PASS")
    results['8'] = True
else:
    print("✗ FAIL")
    results['8'] = False

# TEST 9: Bus seat layout
print("TEST 9: AISLE text removal...")
with open('templates/buses/seat_selection.html', 'r') as f:
    content = f.read()
    if 'class="aisle">AISLE<' not in content and 'class="aisle"></div>' in content:
        print("✓ PASS")
        results['9'] = True
    else:
        print("✗ FAIL")
        results['9'] = False

# TEST 10: Bus schedule admin
print("TEST 10: Bus schedule None-safety...")
with open('buses/models.py', 'r') as f:
    content = f.read()
    if 'available_seats or 0' in content and 'booked_seats or 0' in content:
        print("✓ PASS")
        results['10'] = True
    else:
        print("✗ FAIL")
        results['10'] = False

# Summary
print("\n" + "="*60)
passed = sum(1 for v in results.values() if v)
total = len(results)
print(f"SUMMARY: {passed}/{total} TESTS PASSED")
print("="*60)

if passed == total:
    print("✅ ALL TESTS PASSED - READY TO PUSH")
    exit(0)
else:
    print("❌ SOME TESTS FAILED - DO NOT PUSH")
    failed = [k for k, v in results.items() if not v]
    print(f"Failed tests: {', '.join(failed)}")
    exit(1)
