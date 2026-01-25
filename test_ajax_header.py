#!/usr/bin/env python
"""Quick test to check is_ajax detection"""

import os
import sys
import django
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

client = Client()

# Create test user
user, _ = User.objects.get_or_create(
    username='testuser_debug',
    defaults={
        'email': 'test@example.com',
        'email_verified_at': django.utils.timezone.now()
    }
)
if not user.email_verified_at:
    user.email_verified_at = django.utils.timezone.now()
    user.save()

client.force_login(user)

# Make request to first hotel
from hotels.models import Hotel
hotel = Hotel.objects.filter(is_active=True).first()

if hotel:
    print(f"\nTesting POST to /hotels/{hotel.id}/book/ with AJAX header")
    response = client.post(
        f'/hotels/{hotel.id}/book/',
        data={'checkin_date': '2025-06-01'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    print(f"Response Content-Type: {response.get('Content-Type')}")
    print(f"Response Status: {response.status_code}")
    print(f"First 200 bytes: {response.content[:200]}")
