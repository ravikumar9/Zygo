"""
Property Approval System - Goibibo-grade admin-driven workflow

Enforces STRICT approval controls:
1. Owner submits property (with rooms, images, pricing, meal plans)
2. Admin reviews and approves/rejects
3. ONLY approved properties visible to users
4. Admin can revoke approval
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.models import TimeStampedModel
from .models import Property
import json


class PropertyApprovalRequest(TimeStampedModel):
    """
    Tracks all approval requests for properties
    
    Workflow:
    DRAFT → SUBMITTED → APPROVED/REJECTED
    Rejected properties can be resubmitted as new request
    """
    
    REQUEST_STATUS = [
        ('SUBMITTED', 'Submitted for Review'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REVOKED', 'Approval Revoked'),
    ]
    
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='approval_requests'
    )
    
    # Current status
    status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS,
        default='SUBMITTED',
        db_index=True
    )
    
    # Submission details
    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='property_submissions'
    )
    
    # Submission data snapshot (for audit trail)
    submission_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of property data at submission time"
    )
    
    # Admin review
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='property_reviews'
    )
    
    # Decision
    decision = models.CharField(
        max_length=20,
        choices=[
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
        ],
        null=True,
        blank=True
    )
    
    approval_reason = models.TextField(
        blank=True,
        help_text="Why property was approved (optional)"
    )
    
    rejection_reason = models.TextField(
        blank=True,
        help_text="MANDATORY if decision=REJECTED. Visible to owner."
    )
    
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal admin notes (NOT visible to owner)"
    )
    
    # Approval validity
    approved_until = models.DateField(
        null=True,
        blank=True,
        help_text="Optional: auto-revoke approval on this date (for trial periods)"
    )
    
    # Revocation (if approval is revoked later)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='property_revocations'
    )
    revocation_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['property', 'status']),
            models.Index(fields=['status', 'submitted_at']),
        ]
    
    def __str__(self):
        return f"Property {self.property.id} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # Validate rejection reason if rejected
        if self.decision == 'REJECTED' and not self.rejection_reason.strip():
            raise ValidationError("Rejection reason is mandatory")
        
        super().save(*args, **kwargs)
    
    def approve(self, admin_user, approval_reason='', approved_until=None):
        """Admin approves this request"""
        if self.status in ['APPROVED', 'REVOKED']:
            raise ValidationError(f"Cannot approve {self.status} request")
        
        self.status = 'APPROVED'
        self.decision = 'APPROVED'
        self.approval_reason = approval_reason
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.approved_until = approved_until
        
        self.save()
        
        # Update property status
        self.property.status = 'APPROVED'
        self.property.approved_at = timezone.now()
        self.property.approved_by = admin_user
        self.property.save(update_fields=['status', 'approved_at', 'approved_by'])
        
        # Trigger approval signal
        from django.dispatch import Signal
        property_approved = Signal()
        property_approved.send(sender=self.__class__, property=self.property, admin_user=admin_user)
    
    def reject(self, admin_user, rejection_reason):
        """Admin rejects this request"""
        if not rejection_reason.strip():
            raise ValidationError("Rejection reason is mandatory")
        
        if self.status in ['REJECTED', 'REVOKED']:
            raise ValidationError(f"Cannot reject {self.status} request")
        
        self.status = 'REJECTED'
        self.decision = 'REJECTED'
        self.rejection_reason = rejection_reason
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        
        self.save()
        
        # Update property status
        self.property.status = 'REJECTED'
        self.property.save(update_fields=['status'])
        
        # Trigger rejection signal
        from django.dispatch import Signal
        property_rejected = Signal()
        property_rejected.send(sender=self.__class__, property=self.property, admin_user=admin_user)
    
    def revoke_approval(self, admin_user, revocation_reason=''):
        """Admin revokes a previously approved property"""
        if self.status != 'APPROVED':
            raise ValidationError("Can only revoke APPROVED properties")
        
        self.status = 'REVOKED'
        self.revoked_by = admin_user
        self.revoked_at = timezone.now()
        self.revocation_reason = revocation_reason
        
        self.save()
        
        # Update property status
        self.property.status = 'REJECTED'
        self.property.save(update_fields=['status'])
    
    def is_approval_valid(self):
        """Check if approval is still valid (not expired)"""
        if self.status != 'APPROVED':
            return False
        if self.approved_until and timezone.now().date() > self.approved_until:
            return False
        return True


class PropertyApprovalChecklist(TimeStampedModel):
    """
    Admin checklist for property approval
    Ensures property meets Goibibo-grade quality standards
    """
    
    CHECKLIST_ITEMS = [
        ('PROPERTY_INFO', 'Property Information Complete'),
        ('IMAGES_QUALITY', 'Images Quality Check (min 3 high-res)'),
        ('PRICING_VALID', 'Base Pricing Valid (> ₹0)'),
        ('MEAL_PLANS', 'Meal Plans Configured (min 1)'),
        ('ROOMS_COMPLETE', 'All Rooms Complete & Ready'),
        ('POLICIES_SET', 'Cancellation Policies Set'),
        ('LOCATION_VERIFIED', 'Location Verified'),
        ('OWNER_VERIFIED', 'Owner Verified'),
        ('GST_COMPLIANCE', 'GST Compliance Check'),
        ('TERMS_ACCEPTED', 'Terms & Conditions Accepted'),
    ]
    
    approval_request = models.OneToOneField(
        PropertyApprovalRequest,
        on_delete=models.CASCADE,
        related_name='checklist'
    )
    
    # Checklist status
    items = models.JSONField(
        default=dict,
        help_text="Dict mapping CHECKLIST_ITEMS to {status: PASS/FAIL/PENDING, notes: ''}"
    )
    
    all_passed = models.BooleanField(default=False)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Property Approval Checklists"
    
    def __str__(self):
        return f"Checklist for {self.approval_request.property.name}"
    
    def initialize_checklist(self):
        """Create default checklist structure"""
        self.items = {item_id: {'status': 'PENDING', 'notes': ''} for item_id, _ in self.CHECKLIST_ITEMS}
        self.save()
    
    def mark_item(self, item_id, status, notes=''):
        """Mark checklist item as PASS/FAIL/PENDING"""
        if item_id not in dict(self.CHECKLIST_ITEMS):
            raise ValidationError(f"Unknown checklist item: {item_id}")
        
        self.items[item_id] = {'status': status, 'notes': notes}
        
        # Check if all passed
        self.all_passed = all(
            item['status'] == 'PASS'
            for item in self.items.values()
        )
        
        self.last_reviewed_at = timezone.now()
        self.save()
    
    def is_ready_for_approval(self):
        """Check if all items are PASS"""
        return self.all_passed and all(item['status'] == 'PASS' for item in self.items.values())


class PropertyApprovalAuditLog(TimeStampedModel):
    """
    Audit log for all property approval actions
    For compliance and audit trails
    """
    
    ACTION_TYPES = [
        ('SUBMITTED', 'Property Submitted'),
        ('APPROVED', 'Property Approved'),
        ('REJECTED', 'Property Rejected'),
        ('REVOKED', 'Approval Revoked'),
        ('CHECKLIST_UPDATED', 'Checklist Item Updated'),
        ('NOTES_ADDED', 'Admin Notes Added'),
    ]
    
    approval_request = models.ForeignKey(
        PropertyApprovalRequest,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    
    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='property_approval_actions'
    )
    
    action_details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.approval_request.property.name} - {self.get_action_display()}"
