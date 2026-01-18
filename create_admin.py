import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Check if admin exists
admin = User.objects.filter(username='admin').first()

if admin and admin.is_superuser:
    print(f"✅ Superuser already exists: {admin.username}")
else:
    # Create superuser
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='admin123'
    )
    print(f"✅ Created superuser: {admin.username}")
    print(f"   Email: admin@test.com")
    print(f"   Password: admin123")
    print(f"   Access at: http://127.0.0.1:8000/admin/")
