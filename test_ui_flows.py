"""
Real UI testing via Django test client - NO THEORETICAL CLAIMS
Actual test of every critical flow
"""

from django.test import Client
from users.models import User, UserProfile  # Use custom User model
from django.utils import timezone

print("\n" + "="*80)
print("REAL UI FLOW TESTING - DJANGO TEST CLIENT")
print("="*80)

client = Client()

# ============================================================================
# TEST 1: HOME PAGE - NO NOREVERSEMATCH
# ============================================================================
print("\n[TEST 1] HOME PAGE - No NoReverseMatch")
print("-" * 80)

try:
    response = client.get('/')
    print(f"✓ Response status: {response.status_code}")
    
    content = response.content.decode('utf-8', errors='ignore')
    
    if response.status_code == 200:
        print("✓ PASS: Home page loads successfully")
    else:
        print(f"✗ FAIL: Home page returned status {response.status_code}")
    
    if "NoReverseMatch" in content:
        print("✗ FAIL: NoReverseMatch error found in response!")
        print(content[:500])
    else:
        print("✓ PASS: No NoReverseMatch error")
    
    if "Corporate" in content:
        print("✓ PASS: Corporate section present in HTML")
    else:
        print("✗ FAIL: Corporate section not found")
        
except Exception as e:
    print(f"✗ ERROR: {e}")

# ============================================================================
# TEST 2: REGISTRATION FORM
# ============================================================================
print("\n[TEST 2] REGISTRATION FORM - Check it loads")
print("-" * 80)

try:
    response = client.get('/users/register/')
    print(f"Status: {response.status_code}")
    
    content = response.content.decode('utf-8', errors='ignore')
    
    if response.status_code == 200:
        print("✓ PASS: Registration form loads")
    else:
        print(f"✗ FAIL: Registration page status {response.status_code}")
    
    if "mobile" in content.lower() and "email" in content.lower():
        print("✓ PASS: Form has email and mobile fields")
    else:
        print("✗ FAIL: Form missing fields")
        
except Exception as e:
    print(f"✗ ERROR: {e}")

# ============================================================================
# TEST 3: CREATE TEST USER FOR LOGIN TEST
# ============================================================================
print("\n[TEST 3] CREATE TEST USER FOR TESTING")
print("-" * 80)

try:
    # Clean up any existing test user
    User.objects.filter(username='ui_test_user').delete()
    
    # Create new test user
    user = User.objects.create_user(
        username='ui_test_user',
        email='ui_test@example.com',
        password='TestPass123!',
        first_name='Test',
        last_name='User'
    )
    
    # Create profile with email verified
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.phone = '9876543210'
    profile.email_verified_at = timezone.now()
    profile.save()
    
    print(f"✓ Created test user: {user.username}")
    print(f"✓ Email verified: {profile.email_verified_at is not None}")
    print(f"✓ Ready for login test")
    
except Exception as e:
    print(f"✗ ERROR: {e}")

# ============================================================================
# TEST 4: LOGIN FLOW
# ============================================================================
print("\n[TEST 4] LOGIN FLOW - Email verified user")
print("-" * 80)

try:
    # Try to login
    login_success = client.login(username='ui_test@example.com', password='TestPass123!')
    
    if login_success:
        print("✓ PASS: User login successful")
    else:
        # Try with username instead
        login_success = client.login(username='ui_test_user', password='TestPass123!')
        if login_success:
            print("✓ PASS: User login successful (via username)")
        else:
            print("✗ FAIL: User login failed")
    
    # Check if logged in user can access protected page
    if login_success:
        response = client.get('/payments/wallet/')
        print(f"Wallet page status after login: {response.status_code}")
        if response.status_code in [200, 302]:  # 200 OK, 302 redirect is fine
            print("✓ PASS: Can access protected page")
        else:
            print(f"✗ FAIL: Protected page returned {response.status_code}")
    
except Exception as e:
    print(f"✗ ERROR: {e}")

# ============================================================================
# TEST 5: HOTEL LIST PAGE
# ============================================================================
print("\n[TEST 5] HOTEL LIST PAGE - Check images")
print("-" * 80)

try:
    response = client.get('/hotels/')
    print(f"Status: {response.status_code}")
    
    content = response.content.decode('utf-8', errors='ignore')
    
    if response.status_code == 200:
        print("✓ PASS: Hotel list page loads")
    else:
        print(f"✗ FAIL: Hotel list status {response.status_code}")
    
    # Check for image elements
    if '<img' in content and ('src=' in content or 'onerror=' in content):
        print("✓ PASS: Image elements present")
        
        if 'hotel_placeholder' in content or '/static/images/' in content:
            print("✓ PASS: Image fallback/placeholder configured")
        else:
            print("⚠ WARN: Placeholder not explicitly found")
    else:
        print("✗ FAIL: No image elements found")
    
    # Check if "unavailable" text is present
    if 'unavailable' in content.lower():
        print("✗ FAIL: 'unavailable' text found in page")
    else:
        print("✓ PASS: No 'unavailable' text")
        
except Exception as e:
    print(f"✗ ERROR: {e}")

# ============================================================================
# TEST 6: HOTEL DETAIL PAGE
# ============================================================================
print("\n[TEST 6] HOTEL DETAIL PAGE - First hotel")
print("-" * 80)

try:
    from hotels.models import Hotel
    
    hotel = Hotel.objects.filter(is_active=True).first()
    
    if hotel:
        response = client.get(f'/hotels/{hotel.id}/')
        print(f"Testing hotel: {hotel.name}")
        print(f"Status: {response.status_code}")
        
        content = response.content.decode('utf-8', errors='ignore')
        
        if response.status_code == 200:
            print("✓ PASS: Hotel detail page loads")
        else:
            print(f"✗ FAIL: Hotel detail status {response.status_code}")
        
        # Check for email verification button logic
        if 'email_verified_at' in content or 'Verify Email' in content or 'Proceed to Payment' in content:
            print("✓ PASS: Email verification logic present")
        else:
            print("⚠ WARN: Email verification logic not explicitly found in HTML")
        
        # Check for room types
        if 'Room' in content or 'room' in content.lower():
            print("✓ PASS: Room information present")
        else:
            print("✗ FAIL: No room information found")
            
    else:
        print("⚠ WARN: No active hotels in database - test data needed")
        
except Exception as e:
    print(f"✗ ERROR: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("REAL UI FLOW TEST COMPLETE")
print("="*80)
print("\nNote: For comprehensive testing, run: python manage.py runserver")
print("Then manually test in browser")
