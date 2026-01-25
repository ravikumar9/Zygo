"""
Pytest configuration and fixtures for E2E tests
"""
import pytest
from django.contrib.auth.models import Group
from users.models import User
from property_owners.models import PropertyOwner
from core.models import City

@pytest.fixture
def admin_users(db):
    """Create admin users with appropriate roles"""
    users = {}
    
    # Create Django Groups if they don't exist
    groups_config = {
        'SUPER_ADMIN': 'SUPER_ADMIN',
        'FINANCE_ADMIN': 'FINANCE_ADMIN',
        'PROPERTY_ADMIN': 'PROPERTY_ADMIN',
        'SUPPORT_ADMIN': 'SUPPORT_ADMIN'
    }
    
    for group_name, role in groups_config.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        
        # Create user
        username = group_name.lower()
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
                'first_name': group_name
            }
        )
        user.set_password('test123')
        user.save()
        user.groups.add(group)
        
        users[role] = {
            'username': username,
            'password': 'test123',
            'user': user
        }
    
    return users


@pytest.fixture
def owner_user(db):
    """Create property owner user"""
    # Create city
    city, _ = City.objects.get_or_create(
        name='TestCity',
        defaults={'state': 'TestState', 'country': 'India'}
    )
    
    # Create user
    owner_user = User.objects.create_user(
        username='hotelowner',
        email='owner@test.com',
        password='test123'
    )
    
    # Create PropertyOwner
    property_owner, _ = PropertyOwner.objects.get_or_create(
        user=owner_user,
        defaults={
            'business_name': 'Test Hotel Inc',
            'city': city,
            'owner_name': 'Test Owner',
            'owner_phone': '1234567890',
            'owner_email': 'owner@test.com',
            'address': 'Test Address',
            'pincode': '123456'
        }
    )
    
    return {
        'username': 'hotelowner',
        'password': 'test123',
        'user': owner_user,
        'property_owner': property_owner
    }


@pytest.fixture
def all_test_users(db, admin_users, owner_user):
    """All test users combined"""
    test_users = {
        "SUPER_ADMIN": admin_users['SUPER_ADMIN'],
        "FINANCE_ADMIN": admin_users['FINANCE_ADMIN'],
        "PROPERTY_ADMIN": admin_users['PROPERTY_ADMIN'],
        "SUPPORT_ADMIN": admin_users['SUPPORT_ADMIN'],
        "OWNER": owner_user
    }
    return test_users
