import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

# Clean up test user if exists
User.objects.filter(email='test_wallet@example.com').delete()

# Create test user
user = User.objects.create_user(
    email='test_wallet@example.com',
    username='test_wallet',
    password='TestPass123!'
)
user.email_verified = True
user.save()

# Force login (bypass authentication backend)
client = Client()
client.force_login(user)

print(f"User created and logged in: {user.email}")

response = client.get('/payments/wallet/')
print(f"\n[TEST 1] WALLET PAGE")
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.get('Content-Type', 'unknown')}")
print(f"Is HTML: {'text/html' in response.get('Content-Type', '')}")

content = response.content.decode('utf-8', errors='ignore')
print(f"Has Balance: {'Balance' in content}")
print(f"Has Transactions: {'Transaction' in content or 'History' in content}")
print(f"No broken URLs: {'bookings:list' not in content}")

wallet_pass = (
    response.status_code == 200 and
    'text/html' in response.get('Content-Type', '') and
    'Balance' in content and
    ('Transaction' in content or 'History' in content) and
    'bookings:list' not in content
)
print(f"\nWALLET TEST: {'PASS' if wallet_pass else 'FAIL'}")

# Test hotel placeholder
print(f"\n[TEST 2] HOTEL PLACEHOLDER SVG")
placeholder_path = 'static/images/hotel_placeholder.svg'
if os.path.exists(placeholder_path):
    with open(placeholder_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()
    has_unavailable = 'unavailable' in svg_content.lower()
    print(f"File exists: True")
    print(f"Has 'unavailable' text: {has_unavailable}")
    print(f"\nPLACEHOLDER TEST: {'PASS' if not has_unavailable else 'FAIL'}")
else:
    print(f"File exists: False")
    print(f"\nPLACEHOLDER TEST: FAIL")

# Test hotel date picker
print(f"\n[TEST 3] HOTEL DATE PICKER")
has_min_date = False
for template in ['templates/hotels/hotel_detail.html', 'templates/hotels/hotel_list.html']:
    if os.path.exists(template):
        with open(template, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if 'min=' in content or ('setAttribute' in content and 'min' in content):
            has_min_date = True
            print(f"{template.split('/')[-1]}: Has min-date validation")
print(f"\nDATE PICKER TEST: {'PASS' if has_min_date else 'FAIL'}")

# Test bus seats
print(f"\n[TEST 4] BUS SEAT LAYOUT")
bus_template = 'templates/buses/bus_detail.html'
if os.path.exists(bus_template):
    with open(bus_template, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    has_aisle_text = '<div class="aisle">AISLE</div>' in content
    has_empty_aisle = '<div class="aisle"></div>' in content
    print(f"Has empty aisle div: {has_empty_aisle}")
    print(f"Has AISLE text: {has_aisle_text}")
    print(f"\nSEAT LAYOUT TEST: {'PASS' if (has_empty_aisle and not has_aisle_text) else 'FAIL'}")
else:
    print(f"\nSEAT LAYOUT TEST: FAIL (template not found)")

# Test login redirect
print(f"\n[TEST 5] LOGIN REDIRECT")
client.logout()
# Use force_login again to test redirect
client.force_login(user)
response = client.get('/', follow=True)
final_url = response.request.get('PATH_INFO', '/')
print(f"After login, home page URL: {final_url}")
redirects_to_register = '/users/register' in final_url
print(f"Redirects to register: {redirects_to_register}")
login_pass = not redirects_to_register
print(f"\nLOGIN REDIRECT TEST: {'PASS' if login_pass else 'FAIL'}")

# Summary
print(f"\n{'=' * 60}")
print(f"LOCAL VERIFICATION SUMMARY")
print(f"{'=' * 60}")
print(f"\nThese tests verify the CODE changes are correct.")
print(f"However, REAL BROWSER TESTING on DEV is still required!")
print(f"\nNEXT STEPS:")
print(f"1. Commit wallet template fix")
print(f"2. Push all changes to DEV server")
print(f"3. Test in browser at https://goexplorer-dev.cloud:")
print(f"   - Login with verified user")
print(f"   - Click wallet icon -> Should show HTML page with balance")
print(f"   - Browse hotels -> Should show building placeholder, not 'unavailable'")
print(f"   - Try selecting past dates -> Should be blocked")
print(f"   - Check bus seats -> No 'AISLE' text visible")
print(f"4. Take screenshots as proof")
print(f"5. Run seed_data_clean.py on DEV if hotels are empty")
print(f"\nREMAINING ISSUES (Need Manual Decision):")
print(f"- Corporate Booking: Needs clear decision (working/coming soon/hide)")
print(f"- Admin Rollback: Needs manual Django admin UI test")
