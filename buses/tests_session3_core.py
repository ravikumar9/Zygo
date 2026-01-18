"""
Session 3 Fast Tests - Core Functionality 
Tests the critical backend logic without requiring templates
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from buses.models import BusOperator
from core.models import City

User = get_user_model()


class OperatorApprovalWorkflowTest(TestCase):
    """Test operator approval workflow FSM"""
    
    def setUp(self):
        """Setup test data"""
        self.operator_user = User.objects.create_user(
            username='op1',
            email='op1@test.com',
            password='pass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='pass123'
        )
        self.city1, _ = City.objects.get_or_create(
            code='DL',
            defaults={'name': 'Delhi'}
        )
        self.city2, _ = City.objects.get_or_create(
            code='MB',
            defaults={'name': 'Mumbai'}
        )
    
    def test_operator_starts_in_draft(self):
        """Operators start in DRAFT status"""
        op = BusOperator.objects.create(
            user=self.operator_user,
            name='Test Bus',
        )
        self.assertEqual(op.approval_status, 'draft')
    
    def test_draft_to_pending_transition(self):
        """Draft can transition to PENDING_VERIFICATION"""
        op = BusOperator.objects.create(
            user=self.operator_user,
            name='Test',
            approval_status='draft'
        )
        # Simulate submission
        op.approval_status = 'pending_verification'
        op.submitted_at = timezone.now()
        op.save()
        
        self.assertEqual(op.approval_status, 'pending_verification')
        self.assertIsNotNone(op.submitted_at)
    
    def test_pending_to_approved_transition(self):
        """PENDING can transition to APPROVED"""
        op = BusOperator.objects.create(
            user=self.operator_user,
            name='Test',
            approval_status='pending_verification',
            submitted_at=timezone.now()
        )
        # Simulate admin approval
        op.approval_status = 'approved'
        op.approved_at = timezone.now()
        op.approved_by = self.admin_user
        op.save()
        
        self.assertEqual(op.approval_status, 'approved')
        self.assertIsNotNone(op.approved_at)
        self.assertEqual(op.approved_by, self.admin_user)
    
    def test_pending_to_rejected_transition(self):
        """PENDING can transition to REJECTED"""
        op = BusOperator.objects.create(
            user=self.operator_user,
            name='Test',
            approval_status='pending_verification'
        )
        # Simulate admin rejection
        op.approval_status = 'rejected'
        op.rejection_reason = 'Missing documentation'
        op.save()
        
        self.assertEqual(op.approval_status, 'rejected')
        self.assertEqual(op.rejection_reason, 'Missing documentation')
    
    def test_is_approved_property(self):
        """is_approved property checks approval and is_active"""
        op = BusOperator.objects.create(
            user=self.operator_user,
            name='Test',
            approval_status='approved',
            is_active=True
        )
        self.assertTrue(op.is_approved)
        
        # Not approved if not approved status
        op.approval_status = 'draft'
        self.assertFalse(op.is_approved)
        
        # Not approved if not active
        op.approval_status = 'approved'
        op.is_active = False
        self.assertFalse(op.is_approved)
    
    def test_has_required_fields_validation(self):
        """has_required_fields correctly validates all sections"""
        op = BusOperator.objects.create(user=self.operator_user)
        
        checks, has_all = op.has_required_fields()
        
        # Should have all sections
        self.assertIn('identity', checks)
        self.assertIn('bus_details', checks)
        self.assertIn('routes', checks)
        self.assertIn('pricing', checks)
        self.assertIn('policies', checks)
        
        # All should be False initially
        self.assertFalse(has_all)
        
        # Add identity fields
        op.company_legal_name = 'ABC Tours Pvt Ltd'
        op.operator_office_address = 'New Delhi, 110001'
        op.contact_phone = '+91-9876543210'
        op.contact_email = 'abc@example.com'
        checks, has_all = op.has_required_fields()
        self.assertTrue(checks['identity'])
        
        # Add bus fields
        op.bus_type = 'ac_seater'
        op.total_seats_per_bus = 45
        op.fleet_size = 5
        checks, has_all = op.has_required_fields()
        self.assertTrue(checks['bus_details'])
        
        # Add route fields
        op.primary_source_city = self.city1
        op.primary_destination_city = self.city2
        op.routes_description = 'Delhi to Mumbai route'
        checks, has_all = op.has_required_fields()
        self.assertTrue(checks['routes'])
        
        # Add pricing
        op.base_fare_per_seat = Decimal('500.00')
        checks, has_all = op.has_required_fields()
        self.assertTrue(checks['pricing'])
        
        # Add policies
        op.cancellation_policy = 'Full refund 24h before'
        op.cancellation_cutoff_hours = 24
        op.save()
        checks, has_all = op.has_required_fields()
        self.assertTrue(checks['policies'])
        self.assertTrue(has_all)
    
    def test_completion_percentage(self):
        """Completion percentage tracks registration progress"""
        op = BusOperator.objects.create(user=self.operator_user)
        
        # Partial registration
        op.company_legal_name = 'ABC Tours'
        op.name = 'ABC'
        op.contact_phone = '9876543210'
        op.contact_email = 'abc@test.com'
        op.save()
        
        # Should show partial completion
        pct = op.completion_percentage
        self.assertGreater(pct, 0)
        self.assertLess(pct, 100)
        
        # Full registration
        op.operator_office_address = 'Delhi'
        op.gst_number = '27AABCT1234A1Z5'
        op.bus_type = 'ac_seater'
        op.total_seats_per_bus = 45
        op.fleet_size = 5
        op.primary_source_city = self.city1
        op.primary_destination_city = self.city2
        op.routes_description = 'Delhi to Mumbai'
        op.base_fare_per_seat = Decimal('500.00')
        op.cancellation_policy = 'Full refund'
        op.cancellation_cutoff_hours = 24
        op.save()
        
        self.assertEqual(op.completion_percentage, 100)
    
    def test_mandatory_fields_in_model(self):
        """All mandatory fields exist in model"""
        op = BusOperator()
        
        # Check identity fields exist
        self.assertTrue(hasattr(op, 'company_legal_name'))
        self.assertTrue(hasattr(op, 'operator_office_address'))
        
        # Check bus fields exist
        self.assertTrue(hasattr(op, 'bus_type'))
        self.assertTrue(hasattr(op, 'total_seats_per_bus'))
        self.assertTrue(hasattr(op, 'fleet_size'))
        
        # Check route fields exist
        self.assertTrue(hasattr(op, 'primary_source_city'))
        self.assertTrue(hasattr(op, 'primary_destination_city'))
        self.assertTrue(hasattr(op, 'routes_description'))
        
        # Check pricing fields exist
        self.assertTrue(hasattr(op, 'base_fare_per_seat'))
        self.assertTrue(hasattr(op, 'gst_percentage'))
        
        # Check policy fields exist
        self.assertTrue(hasattr(op, 'cancellation_policy'))
        self.assertTrue(hasattr(op, 'cancellation_cutoff_hours'))
        
        # Check approval workflow fields exist
        self.assertTrue(hasattr(op, 'approval_status'))
        self.assertTrue(hasattr(op, 'submitted_at'))
        self.assertTrue(hasattr(op, 'approved_at'))
        self.assertTrue(hasattr(op, 'approved_by'))
        self.assertTrue(hasattr(op, 'rejection_reason'))
