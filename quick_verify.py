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

# Login and test wallet
client = Client()
login_ok = client.login(username=user.email, password='TestPass123!')
print(f"Login successful: {login_ok}")

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
    with open(placeholder_path, 'r') as f:
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
        with open(template, 'r') as f:
            content = f.read()
        if 'min=' in content or ('setAttribute' in content and 'min' in content):
            has_min_date = True
            print(f"{template.split('/')[-1]}: Has min-date validation")
print(f"\nDATE PICKER TEST: {'PASS' if has_min_date else 'FAIL'}")

# Test bus seats
print(f"\n[TEST 4] BUS SEAT LAYOUT")
bus_template = 'templates/buses/bus_detail.html'
if os.path.exists(bus_template):
    with open(bus_template, 'r') as f:
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
response = client.post('/users/login/', {
    'username': user.email,
    'password': 'TestPass123!'
}, follow=True)
final_url = response.redirect_chain[-1][0] if response.redirect_chain else ''
print(f"Final URL: {final_url}")
print(f"Goes to register: {'/users/register' in final_url}")
login_pass = '/users/register' not in final_url
print(f"\nLOGIN REDIRECT TEST: {'PASS' if login_pass else 'FAIL'}")

print(f"\n{'=' * 60}")
print(f"LOCAL VERIFICATION COMPLETE")
print(f"{'=' * 60}")
print(f"\nNEXT STEPS:")
print(f"1. Commit changes to git")
print(f"2. Push to DEV server")
print(f"3. Run migrations on DEV")
print(f"4. Test in real browser with screenshots:")
print(f"   - https://goexplorer-dev.cloud/payments/wallet/")
print(f"   - https://goexplorer-dev.cloud/hotels/")
print(f"   - https://goexplorer-dev.cloud/buses/")
print(f"5. Run seed_data_clean.py on DEV")
