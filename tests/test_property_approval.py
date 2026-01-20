import os
import django
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from core.models import City
from property_owners.models import PropertyOwner, Property, PropertyRoomType

User = get_user_model()

class PropertyApprovalWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', email='owner@example.com', password='pass')
        self.city = City.objects.create(name='Shimla', state='Himachal Pradesh')
        self.owner = PropertyOwner.objects.create(
            user=self.user,
            business_name='Test Biz',
            owner_name='Owner',
            owner_phone='1234567890',
            owner_email='owner@example.com',
            city=self.city,
            address='Address',
            pincode='171001',
            description='Desc'
        )
        self.property = Property.objects.create(
            owner=self.owner,
            name='Prop',
            description='Desc',
            city=self.city,
            address='Address',
            pincode='171001',
            contact_phone='9876543210',
            contact_email='prop@example.com',
            property_rules='Rules',
            base_price=Decimal('1000.00'),
            max_guests=2,
            num_bedrooms=1,
            num_bathrooms=1,
            status='DRAFT'
        )
        PropertyRoomType.objects.create(
            property=self.property,
            name='Deluxe',
            room_type='deluxe',
            base_price=Decimal('2000.00'),
            total_rooms=2
        )

    def test_owner_draft_isolation(self):
        # DRAFT exists but not visible via guard
        self.assertEqual(self.property.status, 'DRAFT')
        self.assertTrue(PropertyRoomType.objects.filter(property=self.property).exists())
        self.assertFalse(PropertyRoomType.objects.visible().filter(property=self.property).exists())

    def test_approval_promotion(self):
        # DRAFT -> PENDING -> APPROVED
        self.property.submit_for_approval()
        self.assertEqual(self.property.status, 'PENDING')
        # Approve
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.property.approve(admin_user=admin)
        self.assertEqual(self.property.status, 'APPROVED')
        # Visible via guard
        self.assertTrue(PropertyRoomType.objects.visible().filter(property=self.property).exists())

    def test_rejection_flow(self):
        # Reject with reason
        self.property.submit_for_approval()
        self.property.reject('Incomplete documentation')
        self.assertEqual(self.property.status, 'REJECTED')
        self.assertEqual(self.property.rejection_reason, 'Incomplete documentation')
        # Hidden
        self.assertFalse(PropertyRoomType.objects.visible().filter(property=self.property).exists())

    def test_post_approval_edit_moves_pending(self):
        # Approve first
        admin = User.objects.create_superuser('admin2', 'admin2@example.com', 'pass')
        self.property.submit_for_approval()
        self.property.approve(admin_user=admin)
        self.assertEqual(self.property.status, 'APPROVED')
        # Owner edits room type -> mark property pending
        rt = self.property.room_types.first()
        rt.base_price = Decimal('2500.00')
        rt.save()
        # Explicitly mark pending on edit (enforced in view, simulate here)
        self.property.mark_pending_on_edit(actor_id=self.owner.user.id)
        self.assertEqual(self.property.status, 'PENDING')
        # Hidden from guard
        self.assertFalse(PropertyRoomType.objects.visible().filter(property=self.property).exists())

    def test_booking_guard(self):
        # Attempt booking on non-approved property: should be blocked by guard
        # While real booking engine uses hotels.RoomType, guard here enforces approved property visibility
        self.assertEqual(PropertyRoomType.objects.visible().count(), 0)
        # Approve property and verify visibility
        admin = User.objects.create_superuser('admin3', 'admin3@example.com', 'pass')
        self.property.submit_for_approval()
        self.property.approve(admin_user=admin)
        self.assertGreater(PropertyRoomType.objects.visible().count(), 0)
