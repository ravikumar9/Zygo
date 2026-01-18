"""
Integration tests for Property Owner Registration + Admin Approval Workflow
Tests the complete flow:  DRAFT → PENDING_VERIFICATION → APPROVED/REJECTED → VISIBLE/INVISIBLE
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import date

from property_owners.models import PropertyOwner, Property, PropertyType
from core.models import City

User = get_user_model()


class PropertyApprovalWorkflowTestCase(TestCase):
    """Test suite for property approval workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create test users
        self.owner_user = User.objects.create_user(
            username='propertyowner',
            email='owner@example.com',
            password='testpass123'
        )
        
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create property owner profile
        self.city = City.objects.create(
            name='Bangalore',
            state='Karnataka',
            country='India',
            code='BLR'
        )
        self.property_type = PropertyType.objects.create(name='homestay')
        
        self.owner = PropertyOwner.objects.create(
            user=self.owner_user,
            business_name='My Properties',
            property_type=self.property_type,
            description='Property rental business',
            owner_name='John Doe',
            owner_phone='+919876543210',
            owner_email='owner@example.com',
            city=self.city,
            address='123 Main St',
            pincode='560001',
            verification_status='verified'
        )
    
    def test_property_creation_as_draft(self):
        """Test creating property in draft state"""
        self.client.login(username='propertyowner', password='testpass123')
        
        data = {
            'name': 'Ocean View Villa',
            'description': 'Beautiful seaside property',
            'property_type': self.property_type.id,
            'city': self.city.id,
            'address': '456 Beach Road',
            'state': 'Karnataka',
            'pincode': '560001',
            'contact_phone': '+919876543210',
            'contact_email': 'contact@property.com',
            'checkin_time': '14:00:00',
            'checkout_time': '11:00:00',
            'property_rules': 'No pets, No smoking',
            'cancellation_policy': 'Free cancellation up to 7 days',
            'cancellation_type': 'until_checkin',
            'max_guests': '4',
            'num_bedrooms': '2',
            'num_bathrooms': '1',
            'base_price': '5000.00',
            'gst_percentage': '18',
            'currency': 'INR',
            'refund_percentage': '100',
            'amenities_list': ['wifi', 'parking'],
        }
        
        response = self.client.post(reverse('property_owners:create_property'), data)
        
        # Should redirect after creating draft
        self.assertEqual(response.status_code, 302)
        
        # Property should be created in draft status
        property_obj = Property.objects.get(name='Ocean View Villa')
        self.assertEqual(property_obj.approval_status, 'draft')
        self.assertIsNone(property_obj.submitted_at)
        self.assertEqual(property_obj.owner, self.owner)
    
    def test_incomplete_property_cannot_be_submitted(self):
        """Test that incomplete properties cannot be submitted"""
        self.client.login(username='propertyowner', password='testpass123')
        
        # Create incomplete property
        incomplete_data = {
            'name': 'Test Property',
            'description': 'Test',
            'property_type': self.property_type.id,
            'city': self.city.id,
            'address': '',  # Missing address
            'state': 'Karnataka',
            'pincode': '560001',
            # Missing other required fields
        }
        
        response = self.client.post(
            reverse('property_owners:create_property'),
            {**incomplete_data, 'submit_for_approval': 'true'}
        )
        
        # Should not create property (form validation fails)
        # Check that error messages exist
        self.assertIn(b'Please fix the errors', response.content)
    
    def test_complete_property_submission_to_pending(self):
        """Test submitting complete property for verification"""
        self.client.login(username='propertyowner', password='testpass123')
        
        complete_data = {
            'name': 'Complete Property',
            'description': 'A complete property with all fields',
            'property_type': self.property_type.id,
            'city': self.city.id,
            'address': '789 Main Street',
            'state': 'Karnataka',
            'pincode': '560001',
            'contact_phone': '+919876543210',
            'contact_email': 'contact@example.com',
            'checkin_time': '14:00:00',
            'checkout_time': '11:00:00',
            'property_rules': 'House rules',
            'cancellation_policy': 'Free cancellation policy',
            'cancellation_type': 'until_checkin',
            'max_guests': '2',
            'num_bedrooms': '1',
            'num_bathrooms': '1',
            'base_price': '5000.00',
            'gst_percentage': '18',
            'currency': 'INR',
            'refund_percentage': '100',
            'amenities_list': ['wifi'],
            'submit_for_approval': 'true'
        }
        
        response = self.client.post(reverse('property_owners:create_property'), complete_data)
        
        # Should redirect after submission
        self.assertEqual(response.status_code, 302)
        
        # Property should be in pending_verification state
        property_obj = Property.objects.get(name='Complete Property')
        self.assertEqual(property_obj.approval_status, 'pending_verification')
        self.assertIsNotNone(property_obj.submitted_at)
    
    def test_pending_property_not_editable_by_owner(self):
        """Test that pending properties cannot be edited by owner"""
        # Create pending property
        property_obj = Property.objects.create(
            owner=self.owner,
            name='Pending Property',
            description='Test',
            property_type=self.property_type,
            city=self.city,
            address='Test Address',
            state='Karnataka',
            pincode='560001',
            contact_phone='+919876543210',
            contact_email='test@example.com',
            property_rules='Rules',
            cancellation_policy='Policy',
            cancellation_type='until_checkin',
            max_guests=2,
            num_bedrooms=1,
            num_bathrooms=1,
            base_price=5000,
            approval_status='pending_verification',
            submitted_at=timezone.now()
        )
        
        self.client.login(username='propertyowner', password='testpass123')
        
        # Try to view property
        response = self.client.get(reverse('property_owners:property_detail', args=[property_obj.id]))
        self.assertEqual(response.status_code, 200)
        
        # Response should indicate property is not editable
        self.assertIn(b'pending', response.content.lower() or b'review', response.content.lower())
    
    def test_admin_can_approve_property(self):
        """Test admin approving a pending property"""
        # Create pending property
        property_obj = Property.objects.create(
            owner=self.owner,
            name='Property to Approve',
            description='Test',
            property_type=self.property_type,
            city=self.city,
            address='Test Address',
            state='Karnataka',
            pincode='560001',
            contact_phone='+919876543210',
            contact_email='test@example.com',
            property_rules='Rules',
            cancellation_policy='Policy',
            cancellation_type='until_checkin',
            max_guests=2,
            num_bedrooms=1,
            num_bathrooms=1,
            base_price=5000,
            approval_status='pending_verification',
            submitted_at=timezone.now()
        )
        
        self.client.login(username='admin', password='adminpass123')
        
        # Access admin property change page
        url = reverse('admin:property_owners_property_change', args=[property_obj.id])
        
        # Approve the property using the action
        approve_data = {'_approve_properties': 'Approve'}
        response = self.client.post(url, approve_data)
        
        # Refresh property from DB
        property_obj.refresh_from_db()
        
        # Should be approved
        self.assertEqual(property_obj.approval_status, 'approved')
        self.assertIsNotNone(property_obj.approved_at)
        self.assertEqual(property_obj.approved_by, self.admin_user)
    
    def test_admin_can_reject_property(self):
        """Test admin rejecting a property with reason"""
        property_obj = Property.objects.create(
            owner=self.owner,
            name='Property to Reject',
            description='Incomplete description',
            property_type=self.property_type,
            city=self.city,
            address='Test Address',
            state='Karnataka',
            pincode='560001',
            contact_phone='+919876543210',
            contact_email='test@example.com',
            property_rules='Rules',
            cancellation_policy='Policy',
            cancellation_type='until_checkin',
            max_guests=2,
            num_bedrooms=1,
            num_bathrooms=1,
            base_price=5000,
            approval_status='pending_verification',
            submitted_at=timezone.now()
        )
        
        self.client.login(username='admin', password='adminpass123')
        
        # Admin rejects with reason
        rejection_reason = 'Property images are required'
        rejection_data = {
            'approval_status': 'rejected',
            'rejection_reason': rejection_reason,
        }
        
        url = reverse('admin:property_owners_property_change', args=[property_obj.id])
        response = self.client.post(url, {**rejection_data, '_save': 'Save'})
        
        # Refresh property
        property_obj.refresh_from_db()
        
        # Should be rejected
        self.assertEqual(property_obj.approval_status, 'rejected')
        self.assertEqual(property_obj.rejection_reason, rejection_reason)
    
    def test_rejected_property_editable_by_owner(self):
        """Test that rejected properties can be edited and resubmitted"""
        property_obj = Property.objects.create(
            owner=self.owner,
            name='Rejected Property',
            description='Test',
            property_type=self.property_type,
            city=self.city,
            address='Test Address',
            state='Karnataka',
            pincode='560001',
            contact_phone='+919876543210',
            contact_email='test@example.com',
            property_rules='Rules',
            cancellation_policy='Policy',
            cancellation_type='until_checkin',
            max_guests=2,
            num_bedrooms=1,
            num_bathrooms=1,
            base_price=5000,
            approval_status='rejected',
            rejection_reason='Missing property images'
        )
        
        self.client.login(username='propertyowner', password='testpass123')
        
        # View detail should indicate editable
        response = self.client.get(reverse('property_owners:property_detail', args=[property_obj.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Resubmit', response.content)
    
    def test_approved_property_is_approved_property(self):
        """Test that approved property returns is_approved=True"""
        property_obj = Property.objects.create(
            owner=self.owner,
            name='Approved Property',
            description='Test',
            property_type=self.property_type,
            city=self.city,
            address='Test Address',
            state='Karnataka',
            pincode='560001',
            contact_phone='+919876543210',
            contact_email='test@example.com',
            property_rules='Rules',
            cancellation_policy='Policy',
            cancellation_type='until_checkin',
            max_guests=2,
            num_bedrooms=1,
            num_bathrooms=1,
            base_price=5000,
            approval_status='approved',
            approved_at=timezone.now(),
            approved_by=self.admin_user,
            is_active=True
        )
        
        self.assertTrue(property_obj.is_approved)
    
    def test_non_approved_property_not_visible(self):
        """Test that non-approved properties return is_approved=False"""
        for status in ['draft', 'pending_verification', 'rejected']:
            property_obj = Property.objects.create(
                owner=self.owner,
                name=f'{status.title()} Property',
                description='Test',
                property_type=self.property_type,
                city=self.city,
                address='Test Address',
                state='Karnataka',
                pincode='560001',
                contact_phone='+919876543210',
                contact_email='test@example.com',
                property_rules='Rules',
                cancellation_policy='Policy',
                cancellation_type='until_checkin',
                max_guests=2,
                num_bedrooms=1,
                num_bathrooms=1,
                base_price=5000,
                approval_status=status,
                is_active=True
            )
            
            self.assertFalse(property_obj.is_approved)
    
    def test_owner_dashboard_groups_properties_by_status(self):
        """Test that owner dashboard shows properties grouped by approval status"""
        # Create properties in different statuses
        Property.objects.create(
            owner=self.owner, name='Approved', approval_status='approved',
            description='', property_type=self.property_type, city=self.city,
            address='Addr', state='KA', pincode='560001', contact_phone='+91', contact_email='a@a.com',
            property_rules='', cancellation_policy='', cancellation_type='until_checkin',
            max_guests=1, num_bedrooms=1, num_bathrooms=1, base_price=1000, is_active=True
        )
        Property.objects.create(
            owner=self.owner, name='Pending', approval_status='pending_verification',
            submitted_at=timezone.now(), description='', property_type=self.property_type,
            city=self.city, address='Addr', state='KA', pincode='560001', contact_phone='+91',
            contact_email='a@a.com', property_rules='', cancellation_policy='', 
            cancellation_type='until_checkin', max_guests=1, num_bedrooms=1, num_bathrooms=1,
            base_price=1000, is_active=True
        )
        Property.objects.create(
            owner=self.owner, name='Draft', approval_status='draft',
            description='', property_type=self.property_type, city=self.city,
            address='Addr', state='KA', pincode='560001', contact_phone='+91', contact_email='a@a.com',
            property_rules='', cancellation_policy='', cancellation_type='until_checkin',
            max_guests=1, num_bedrooms=1, num_bathrooms=1, base_price=1000, is_active=True
        )
        
        self.client.login(username='propertyowner', password='testpass123')
        response = self.client.get(reverse('property_owners:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        # Check all statuses are shown in context
        self.assertIn('approved_properties', response.context)
        self.assertIn('pending_properties', response.context)
        self.assertIn('draft_properties', response.context)
        
        self.assertEqual(response.context['approved_properties'].count(), 1)
        self.assertEqual(response.context['pending_properties'].count(), 1)
        self.assertEqual(response.context['draft_properties'].count(), 1)
    
    def test_property_completion_percentage(self):
        """Test property completion percentage calculation"""
        property_obj = Property.objects.create(
            owner=self.owner, name='Partial Property',
            description='',  # Missing description
            property_type=self.property_type,
            city=self.city,
            address='',  # Missing address
            state='',  # Missing state
            pincode='560001',
            contact_phone='',  # Missing phone
            contact_email='test@example.com',
            property_rules='',  # Missing rules
            cancellation_policy='',  # Missing policy
            cancellation_type='',  # Missing type
            max_guests=0,  # Missing guests
            num_bedrooms=1,
            num_bathrooms=1,
            base_price=0  # Missing price
        )
        
        # Should be < 100% (not all fields filled)
        self.assertLess(property_obj.completion_percentage, 100)
    
    def test_has_required_fields_validation(self):
        """Test has_required_fields validation method"""
        property_obj = Property.objects.create(
            owner=self.owner,
            name='Test Property',
            description='Test description',
            property_type=self.property_type,
            city=self.city,
            address='123 Test St',
            state='Karnataka',
            pincode='560001',
            contact_phone='+919876543210',
            contact_email='test@example.com',
            property_rules='Test rules',
            cancellation_policy='Test policy',
            cancellation_type='until_checkin',
            max_guests=2,
            num_bedrooms=1,
            num_bathrooms=1,
            base_price=5000,
            has_wifi=True  # At least one amenity
        )
        
        checks, is_complete = property_obj.has_required_fields()
        
        # Should have checks dict and boolean
        self.assertIsInstance(checks, dict)
        self.assertIsInstance(is_complete, bool)


class PropertyFormTestCase(TestCase):
    """Test property registration form"""
    
    def setUp(self):
        self.city = City.objects.create(name='Test City')
        self.property_type = PropertyType.objects.create(name='homestay')
    
    def test_form_requires_all_fields(self):
        """Test that form validates all required fields"""
        from property_owners.forms import PropertyRegistrationForm
        
        incomplete_data = {
            'name': 'Test Property',
            # Missing other required fields
        }
        
        form = PropertyRegistrationForm(data=incomplete_data)
        self.assertFalse(form.is_valid())
        # Should have errors for missing fields
        self.assertTrue(len(form.errors) > 0)
