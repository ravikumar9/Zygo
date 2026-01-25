"""
Pytest configuration for Phase-3 E2E tests
Sets up test database and users before Playwright tests run
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_users(django_db_blocker):
    """
    Create test users for E2E tests before any tests run
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    print("\n[SETUP] Creating test users for Playwright E2E tests...")
    
    with django_db_blocker.unblock():
        TEST_USERS = {
            'superadmin_user': {
                'password': 'TestPass123!@',
                'role': 'SUPER_ADMIN',
                'email': 'superadmin_user@test.com',
            },
            'finance_user': {
                'password': 'TestPass123!@',
                'role': 'FINANCE_ADMIN',
                'email': 'finance_user@test.com',
            },
            'property_admin_user': {
                'password': 'TestPass123!@',
                'role': 'PROPERTY_ADMIN',
                'email': 'property_admin_user@test.com',
            },
            'support_user': {
                'password': 'TestPass123!@',
                'role': 'SUPPORT_ADMIN',
                'email': 'support_user@test.com',
            },
            'owner_user': {
                'password': 'TestPass123!@',
                'role': 'OWNER',
                'email': 'owner_user@test.com',
            },
        }
        
        created_count = 0
        for username, creds in TEST_USERS.items():
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                print(f"  [SKIP] User '{username}' already exists")
                continue
            
            try:
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=creds['email'],
                    password=creds['password'],
                    is_staff=True,
                    is_active=True,
                )
                
                print(f"  [OK] Created user '{username}' with role '{creds['role']}'")
                created_count += 1
                
            except Exception as e:
                print(f"  [ERROR] Failed to create '{username}': {e}")
        
        print(f"\n[SETUP] Test setup complete: {created_count} users created")


@pytest.fixture(scope="session", autouse=True)
def django_db_setup():
    """
    Ensure Django database is available for tests
    """
    from django.core.management import call_command
    
    # Run migrations to ensure schema is up to date
    try:
        call_command('migrate', '--run-syncdb', verbosity=0)
        print("[SETUP] Database migrations complete")
    except Exception as e:
        print(f"[WARNING] Migration issue: {e}")
    
    # Setup admin roles
    try:
        call_command('setup_admin_roles', verbosity=0)
        print("[SETUP] Admin roles setup complete")
    except Exception as e:
        print(f"[WARNING] Admin roles setup: {e}")

