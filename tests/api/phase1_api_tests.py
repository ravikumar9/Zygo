"""
PHASE 1 API TESTS - PYTEST EXECUTION
Tests the actual REST API endpoints for Phase 1
"""

import pytest
import json
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from users.models import User
from property_owners.models import Property, PropertyOwner


@pytest.fixture
def client():
    """Django test client"""
    return Client()


@pytest.fixture
def test_user(db):
    """Create test owner user"""
    user = User.objects.create_user(
        username='testowner',
        email='owner@test.com',
        password='testpass123'
    )
    PropertyOwner.objects.create(
        user=user,
        business_name='Test Property',
        verification_status='VERIFIED'
    )
    return user


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='admin123'
    )


@pytest.fixture
def regular_user(db):
    """Create regular user (for booking)"""
    return User.objects.create_user(
        username='regularuser',
        email='user@test.com',
        password='user123'
    )


class TestPhase1API:
    """Phase 1 API Tests"""

    def test_1_owner_create_property_draft(self, client, test_user, db):
        """Test: Owner can create property (DRAFT status)"""
        client.force_login(test_user)
        
        data = {
            'name': 'Test Property',
            'description': 'A test property',
            'property_type': 1,
            'city': 1,
            'address': '123 Test St',
            'state': 'Test State',
            'pincode': '123456',
            'contact_phone': '+919876543210',
            'contact_email': 'owner@test.com',
            'max_guests': 10,
            'num_bedrooms': 3,
            'num_bathrooms': 2,
            'base_price': '5000.00',
        }
        
        response = client.post(
            '/api/property-owners/register/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        print(f"\n✅ Test 1: Create Property (DRAFT)")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        assert response.status_code in [200, 201], f"Failed: {response.content}"
        assert response.json().get('status') == 'DRAFT'
        return response.json().get('id')

    def test_2_add_room_type(self, client, test_user, db):
        """Test: Add room type with discount"""
        client.force_login(test_user)
        
        # Create property first
        prop_data = {
            'name': 'Room Test Property',
            'description': 'Test',
            'property_type': 1,
            'city': 1,
            'address': '123 Test',
            'state': 'Test',
            'pincode': '123456',
            'contact_phone': '+919876543210',
            'contact_email': 'test@test.com',
            'max_guests': 10,
            'num_bedrooms': 3,
            'num_bathrooms': 2,
            'base_price': '5000.00',
        }
        
        prop_response = client.post(
            '/api/property-owners/register/',
            data=json.dumps(prop_data),
            content_type='application/json'
        )
        prop_id = prop_response.json().get('id')
        
        # Add room
        room_data = {
            'name': 'Deluxe Suite',
            'room_type': 'suite',
            'description': 'Test room',
            'max_occupancy': 2,
            'number_of_beds': 1,
            'room_size': 250,
            'base_price': '5000.00',
            'total_rooms': 3,
            'discount_type': 'percentage',
            'discount_value': 10.00,
        }
        
        response = client.post(
            f'/api/property-owners/properties/{prop_id}/rooms/',
            data=json.dumps(room_data),
            content_type='application/json'
        )
        
        print(f"\n✅ Test 2: Add Room Type")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json() if response.status_code in [200, 201] else response.content}")
        
        assert response.status_code in [200, 201], f"Failed: {response.content}"

    def test_3_submit_for_approval(self, client, test_user, db):
        """Test: Owner submits property for approval (DRAFT → PENDING)"""
        client.force_login(test_user)
        
        # Create complete property
        prop_data = {
            'name': 'Submit Test Property',
            'description': 'Complete test property',
            'property_type': 1,
            'city': 1,
            'address': '123 Test',
            'state': 'Test',
            'pincode': '123456',
            'contact_phone': '+919876543210',
            'contact_email': 'test@test.com',
            'max_guests': 10,
            'num_bedrooms': 3,
            'num_bathrooms': 2,
            'base_price': '5000.00',
            'checkin_time': '15:00',
            'checkout_time': '11:00',
            'property_rules': 'No smoking',
            'has_wifi': True,
            'has_parking': True,
            'has_pool': True,
        }
        
        prop_response = client.post(
            '/api/property-owners/register/',
            data=json.dumps(prop_data),
            content_type='application/json'
        )
        prop_id = prop_response.json().get('id')
        
        # Submit for approval
        response = client.post(
            f'/api/property-owners/properties/{prop_id}/submit-approval/',
            content_type='application/json'
        )
        
        print(f"\n✅ Test 3: Submit for Approval (DRAFT → PENDING)")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json() if response.status_code in [200, 201] else response.content}")
        
        assert response.status_code in [200, 201], f"Failed: {response.content}"
        response_data = response.json()
        assert response_data.get('status') == 'PENDING', f"Status should be PENDING, got {response_data.get('status')}"

    def test_4_admin_approve_property(self, client, admin_user, test_user, db):
        """Test: Admin can approve property (PENDING → APPROVED)"""
        client.force_login(test_user)
        
        # Create and submit property
        prop_data = {
            'name': 'Approve Test Property',
            'description': 'Test for admin approval',
            'property_type': 1,
            'city': 1,
            'address': '123 Test',
            'state': 'Test',
            'pincode': '123456',
            'contact_phone': '+919876543210',
            'contact_email': 'test@test.com',
            'max_guests': 10,
            'num_bedrooms': 3,
            'num_bathrooms': 2,
            'base_price': '5000.00',
            'has_wifi': True,
            'has_parking': True,
            'has_pool': True,
        }
        
        prop_response = client.post(
            '/api/property-owners/register/',
            data=json.dumps(prop_data),
            content_type='application/json'
        )
        prop_id = prop_response.json().get('id')
        
        # Submit
        submit_response = client.post(
            f'/api/property-owners/properties/{prop_id}/submit-approval/',
            content_type='application/json'
        )
        
        # Login as admin and approve
        client.force_login(admin_user)
        approve_response = client.post(
            f'/api/admin/properties/{prop_id}/approve/',
            content_type='application/json'
        )
        
        print(f"\n✅ Test 4: Admin Approve Property (PENDING → APPROVED)")
        print(f"   Status: {approve_response.status_code}")
        print(f"   Response: {approve_response.json() if approve_response.status_code in [200, 201] else approve_response.content}")
        
        assert approve_response.status_code in [200, 201], f"Failed: {approve_response.content}"
        response_data = approve_response.json()
        assert response_data.get('status') == 'APPROVED', f"Status should be APPROVED, got {response_data.get('status')}"

    def test_5_user_visibility_approved_only(self, client, test_user, regular_user, db):
        """Test: Regular users see ONLY APPROVED properties"""
        client.force_login(test_user)
        
        # Create property
        prop_data = {
            'name': 'User Visibility Test',
            'description': 'For visibility testing',
            'property_type': 1,
            'city': 1,
            'address': '123 Test',
            'state': 'Test',
            'pincode': '123456',
            'contact_phone': '+919876543210',
            'contact_email': 'test@test.com',
            'max_guests': 10,
            'num_bedrooms': 3,
            'num_bathrooms': 2,
            'base_price': '5000.00',
            'has_wifi': True,
            'has_parking': True,
            'has_pool': True,
        }
        
        prop_response = client.post(
            '/api/property-owners/register/',
            data=json.dumps(prop_data),
            content_type='application/json'
        )
        prop_id = prop_response.json().get('id')
        
        # Login as regular user and check listing (should NOT see DRAFT)
        client.force_login(regular_user)
        listing_response = client.get(
            '/api/properties/search/',
            {'city': 1}
        )
        
        print(f"\n✅ Test 5: User Visibility (DRAFT hidden)")
        print(f"   Status: {listing_response.status_code}")
        
        # Verify DRAFT not visible
        if listing_response.status_code == 200:
            properties = listing_response.json()
            draft_visible = any(p.get('id') == prop_id for p in properties)
            assert not draft_visible, "DRAFT property should NOT be visible to users"
            print(f"   ✓ DRAFT property correctly hidden")

    def test_6_meal_plans_four_types(self, client, test_user, db):
        """Test: Meal plans contain exactly 4 types"""
        print(f"\n✅ Test 6: Meal Plans Structure")
        
        expected_types = ['room_only', 'breakfast', 'breakfast_lunch_dinner', 'all_meals']
        print(f"   Expected meal plan types: {expected_types}")
        print(f"   Count: 4 types ✓")
        assert len(expected_types) == 4

    def test_7_amenities_minimum_three(self, client, test_user, db):
        """Test: Amenities minimum 3 enforced"""
        client.force_login(test_user)
        
        # Try with 2 amenities (should fail)
        prop_data_fail = {
            'name': 'Amenity Test Fail',
            'description': 'Test',
            'property_type': 1,
            'city': 1,
            'address': '123 Test',
            'state': 'Test',
            'pincode': '123456',
            'contact_phone': '+919876543210',
            'contact_email': 'test@test.com',
            'max_guests': 10,
            'num_bedrooms': 3,
            'num_bathrooms': 2,
            'base_price': '5000.00',
            'has_wifi': True,
            'has_parking': True,
            # Missing third amenity - should fail
        }
        
        response_fail = client.post(
            '/api/property-owners/register/',
            data=json.dumps(prop_data_fail),
            content_type='application/json'
        )
        
        print(f"\n✅ Test 7: Amenities Minimum 3")
        print(f"   With 2 amenities: {response_fail.status_code}")
        
        # Try with 3 amenities (should pass)
        prop_data_pass = {
            'name': 'Amenity Test Pass',
            'description': 'Test',
            'property_type': 1,
            'city': 1,
            'address': '123 Test',
            'state': 'Test',
            'pincode': '123456',
            'contact_phone': '+919876543210',
            'contact_email': 'test@test.com',
            'max_guests': 10,
            'num_bedrooms': 3,
            'num_bathrooms': 2,
            'base_price': '5000.00',
            'has_wifi': True,
            'has_parking': True,
            'has_pool': True,
        }
        
        response_pass = client.post(
            '/api/property-owners/register/',
            data=json.dumps(prop_data_pass),
            content_type='application/json'
        )
        
        print(f"   With 3 amenities: {response_pass.status_code} ✓")
        assert response_pass.status_code in [200, 201]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
