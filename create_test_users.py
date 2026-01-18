import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

test_users = [
    {
        'username': 'testuser1',
        'email': 'testuser1@test.com',
        'password': 'TestPass123',
        'first_name': 'Test',
        'last_name': 'User One',
        'phone': '+919876543210'
    },
    {
        'username': 'testuser2',
        'email': 'testuser2@test.com',
        'password': 'TestPass123',
        'first_name': 'Test',
        'last_name': 'User Two',
        'phone': ''  # No phone
    },
]

for user_data in test_users:
    username = user_data.pop('username')
    email = user_data.pop('email')
    password = user_data.pop('password')
    
    user, created = User.objects.get_or_create(username=username, defaults={'email': email})
    if created:
        user.set_password(password)
        for key, value in user_data.items():
            setattr(user, key, value)
        user.save()
        print(f"✅ Created: {username} ({email})")
    else:
        print(f"⚠️  Already exists: {username}")

print("\n✅ Test users ready")
