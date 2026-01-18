"""
Session 3 Integration Tests - Bus Operator Registration & Admin Approval
Test coverage: Registration workflow, validation, admin approval, search filtering
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal
from buses.models import BusOperator
from core.models import City
import json

User = get_user_model()


class OperatorRegistrationWorkflowTest(TestCase):
    """Test bus operator registration and approval workflow"""
    
    def setUp(self):
        """Setup test data"""
        self.client = Client()
        
        # Create test users
        self.operator_user = User.objects.create_user(
            username='operator1',
            email='operator1@test.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )
        
        # Create or get test cities with unique codes
        self.city1, _ = City.objects.get_or_create(
            code='DLI',
            defaults={'name': 'Delhi'}
        )
        self.city2, _ = City.objects.get_or_create(
            code='MUM',
            defaults={'name': 'Mumbai'}
        )
        
        # Login operator
        self.client.login(username='operator1', password='testpass123')
    
    def test_operator_draft_creation(self):
        """Test creating an operator in DRAFT status"""
        response = self.client.get(reverse('buses:operator_register'))
        self.assertEqual(response.status_code, 200)
        
        # Submit partial data (should be saved as draft)
        data = {
            'company_legal_name': 'ABC Tours Pvt Ltd',
            'name': 'ABC Express',
            'contact_phone': '+91-9876543210',
            'contact_email': 'abc@example.com',
            'operator_office_address': 'New Delhi, 110001, India',
            'gst_number': '27AABCT1234A1Z5',
            'bus_type': 'ac_seater',
            'total_seats_per_bus': '45',
            'fleet_size': '5',
            'primary_source_city': self.city1.id,
            'primary_destination_city': self.city2.id,
            'routes_description': 'Delhi to Mumbai express route with intermediate stops at Indore, Bhopal',
            'base_fare_per_seat': '500.00',
            'gst_percentage': '5',
            'refund_percentage': '100',
            'cancellation_policy': 'Full refund if cancelled 24 hours before departure',
            'cancellation_cutoff_hours': '24',
            'has_ac': True,
        }
        
        response = self.client.post(reverse('buses:operator_register'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after save
        
        # Verify operator was created in DRAFT status
        operator = BusOperator.objects.get(user=self.operator_user)
        self.assertEqual(operator.approval_status, 'draft')
        self.assertEqual(operator.company_legal_name, 'ABC Tours Pvt Ltd')
    
    def test_mandatory_field_validation(self):
        """Test that form validates all mandatory fields"""
        # Try to submit with missing fields
        incomplete_data = {
            'company_legal_name': 'ABC Tours Pvt Ltd',
            'name': 'ABC Express',
            # Missing other required fields
        }
        
        response = self.client.post(reverse('buses:operator_register'), incomplete_data)
        # Should re-render form due to validation errors
        self.assertEqual(response.status_code, 200)
        # Form should have errors
        self.assertTrue(response.context['form'].errors)
    
    def test_gst_format_validation(self):
        """Test GST number format validation"""
        data = {
            'company_legal_name': 'ABC Tours Pvt Ltd',
            'name': 'ABC Express',
            'contact_phone': '+91-9876543210',
            'contact_email': 'abc@example.com',
            'operator_office_address': 'New Delhi, 110001, India',
            'gst_number': 'INVALID',  # Invalid format
            'bus_type': 'ac_seater',
            'total_seats_per_bus': '45',
            'fleet_size': '5',
            'primary_source_city': self.city1.id,
            'primary_destination_city': self.city2.id,
            'routes_description': 'Delhi to Mumbai express route',
            'base_fare_per_seat': '500.00',
            'gst_percentage': '5',
            'refund_percentage': '100',
            'cancellation_policy': 'Full refund if cancelled 24 hours before departure',
            'cancellation_cutoff_hours': '24',
        }
        
        response = self.client.post(reverse('buses:operator_register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('gst_number', response.context['form'].errors)
    
    def test_operator_submission_changes_status(self):
        """Test submitting a draft changes status to PENDING_VERIFICATION"""
        # Create draft operator
        operator = BusOperator.objects.create(
            user=self.operator_user,
            company_legal_name='ABC Tours Pvt Ltd',
            name='ABC Express',
            contact_phone='+91-9876543210',
            contact_email='abc@example.com',
            operator_office_address='New Delhi, 110001, India',
            gst_number='27AABCT1234A1Z5',
            bus_type='ac_seater',
            total_seats_per_bus=45,
            fleet_size=5,
            primary_source_city=self.city1,
            primary_destination_city=self.city2,
            routes_description='Delhi to Mumbai express route',
            base_fare_per_seat=Decimal('500.00'),
            cancellation_policy='Full refund if cancelled 24 hours before departure',
            cancellation_cutoff_hours=24,
            approval_status='draft'
        )
        
        # Submit for approval
        response = self.client.post(reverse('buses:operator_submit', args=[operator.pk]))
        self.assertEqual(response.status_code, 302)
        
        # Verify status changed
        operator.refresh_from_db()
        self.assertEqual(operator.approval_status, 'pending_verification')
        self.assertIsNotNone(operator.submitted_at)
    
    def test_admin_approval_action(self):
        """Test admin can approve operator registration"""
        # Create pending operator
        operator = BusOperator.objects.create(
            user=self.operator_user,
            company_legal_name='ABC Tours Pvt Ltd',
            name='ABC Express',
            contact_phone='+91-9876543210',
            contact_email='abc@example.com',
            operator_office_address='New Delhi, 110001, India',
            gst_number='27AABCT1234A1Z5',
            bus_type='ac_seater',
            total_seats_per_bus=45,
            fleet_size=5,
            primary_source_city=self.city1,
            primary_destination_city=self.city2,
            routes_description='Delhi to Mumbai express route',
            base_fare_per_seat=Decimal('500.00'),
            cancellation_policy='Full refund if cancelled 24 hours before departure',
            cancellation_cutoff_hours=24,
            approval_status='pending_verification',
            submitted_at=timezone.now()
        )
        
        # Login as admin
        self.client.logout()
        self.client.login(username='admin', password='adminpass123')
        
        # Approve operator via admin
        operator.approval_status = 'approved'
        operator.approved_at = timezone.now()
        operator.approved_by = self.admin_user
        operator.save()
        
        # Verify operator is now approved
        operator.refresh_from_db()
        self.assertEqual(operator.approval_status, 'approved')
        self.assertIsNotNone(operator.approved_at)
        self.assertEqual(operator.approved_by, self.admin_user)
    
    def test_only_approved_operators_visible_in_search(self):
        """Test that only APPROVED operators appear in bus search"""
        from buses.models import Bus, BusRoute
        
        # Create two operators - one draft, one approved
        draft_op = BusOperator.objects.create(
            user=self.operator_user,
            company_legal_name='Draft Tours',
            name='Draft Express',
            contact_phone='+91-9876543210',
            contact_email='draft@example.com',
            operator_office_address='New Delhi, 110001, India',
            gst_number='27AABCT1234A1Z5',
            bus_type='ac_seater',
            total_seats_per_bus=45,
            fleet_size=5,
            primary_source_city=self.city1,
            primary_destination_city=self.city2,
            routes_description='Route',
            base_fare_per_seat=Decimal('500.00'),
            cancellation_policy='Policy',
            cancellation_cutoff_hours=24,
            approval_status='draft'
        )
        
        admin_user2 = User.objects.create_user(
            username='admin2',
            email='admin2@test.com',
            password='adminpass123'
        )
        
        approved_op = BusOperator.objects.create(
            user=admin_user2,
            company_legal_name='Approved Tours',
            name='Approved Express',
            contact_phone='+91-9876543210',
            contact_email='approved@example.com',
            operator_office_address='New Delhi, 110001, India',
            gst_number='27AABCT1234A1Z5',
            bus_type='ac_seater',
            total_seats_per_bus=45,
            fleet_size=5,
            primary_source_city=self.city1,
            primary_destination_city=self.city2,
            routes_description='Route',
            base_fare_per_seat=Decimal('500.00'),
            cancellation_policy='Policy',
            cancellation_cutoff_hours=24,
            approval_status='approved',
            approved_at=timezone.now(),
            approved_by=self.admin_user
        )
        
        # Create buses for both operators
        draft_bus = Bus.objects.create(
            operator=draft_op,
            bus_number='DRAFT01',
            bus_name='Draft Bus',
            bus_type='ac_seater',
            total_seats=45
        )
        
        approved_bus = Bus.objects.create(
            operator=approved_op,
            bus_number='APPROVED01',
            bus_name='Approved Bus',
            bus_type='ac_seater',
            total_seats=45
        )
        
        # Create routes
        BusRoute.objects.create(
            bus=draft_bus,
            source_city=self.city1,
            destination_city=self.city2,
            base_fare=Decimal('500.00')
        )
        
        BusRoute.objects.create(
            bus=approved_bus,
            source_city=self.city1,
            destination_city=self.city2,
            base_fare=Decimal('500.00')
        )
        
        # Logout operator and check bus list
        self.client.logout()
        response = self.client.get(reverse('buses:bus_list'))
        
        # Only approved bus should appear
        self.assertIn(approved_bus.bus_name, str(response.content))
        self.assertNotIn(draft_bus.bus_name, str(response.content))
    
    def test_completion_percentage_calculation(self):
        """Test completion percentage is correctly calculated"""
        operator = BusOperator.objects.create(
            user=self.operator_user,
            approval_status='draft'
        )
        
        # Should be 0% initially
        self.assertEqual(operator.completion_percentage, 0)
        
        # Add some fields
        operator.company_legal_name = 'ABC Tours'
        operator.name = 'ABC Express'
        operator.contact_phone = '+91-9876543210'
        operator.contact_email = 'abc@example.com'
        operator.operator_office_address = 'New Delhi'
        operator.save()
        
        # Should be around 50% now (6 out of ~12 fields)
        self.assertGreater(operator.completion_percentage, 0)
        self.assertLess(operator.completion_percentage, 100)
        
        # Add remaining fields
        operator.gst_number = '27AABCT1234A1Z5'
        operator.bus_type = 'ac_seater'
        operator.total_seats_per_bus = 45
        operator.fleet_size = 5
        operator.primary_source_city = self.city1
        operator.primary_destination_city = self.city2
        operator.routes_description = 'Delhi to Mumbai'
        operator.base_fare_per_seat = Decimal('500.00')
        operator.cancellation_policy = 'Full refund 24h before'
        operator.cancellation_cutoff_hours = 24
        operator.save()
        
        # Should be 100% now
        self.assertEqual(operator.completion_percentage, 100)
    
    def test_draft_can_be_edited_but_pending_cannot(self):
        """Test draft operators can edit but pending cannot"""
        # Create draft operator
        operator = BusOperator.objects.create(
            user=self.operator_user,
            company_legal_name='ABC Tours',
            approval_status='draft'
        )
        
        # Should allow editing draft
        response = self.client.get(reverse('buses:operator_register'))
        self.assertEqual(response.status_code, 200)
        
        # Change to pending
        operator.approval_status = 'pending_verification'
        operator.submitted_at = timezone.now()
        operator.save()
        
        # Try to access edit page - should redirect to detail
        response = self.client.get(reverse('buses:operator_register'))
        self.assertEqual(response.status_code, 302)
    
    def test_has_required_fields_validation(self):
        """Test has_required_fields validation method"""
        operator = BusOperator.objects.create(user=self.operator_user)
        
        checks, has_all = operator.has_required_fields()
        
        # Should have all checks as dictionary
        self.assertIn('identity', checks)
        self.assertIn('bus_details', checks)
        self.assertIn('routes', checks)
        self.assertIn('pricing', checks)
        self.assertIn('policies', checks)
        
        # Should not have all fields
        self.assertFalse(has_all)
        
        # Add all required fields
        operator.company_legal_name = 'ABC Tours Pvt Ltd'
        operator.operator_office_address = 'New Delhi, 110001, India'
        operator.contact_phone = '+91-9876543210'
        operator.contact_email = 'abc@example.com'
        operator.bus_type = 'ac_seater'
        operator.total_seats_per_bus = 45
        operator.fleet_size = 5
        operator.primary_source_city = self.city1
        operator.primary_destination_city = self.city2
        operator.routes_description = 'Delhi to Mumbai'
        operator.base_fare_per_seat = Decimal('500.00')
        operator.cancellation_policy = 'Full refund 24h before'
        operator.cancellation_cutoff_hours = 24
        operator.save()
        
        checks, has_all = operator.has_required_fields()
        self.assertTrue(has_all)
