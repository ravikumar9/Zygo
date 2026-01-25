"""
Migration for PropertyApprovalRequest, PropertyApprovalChecklist, and PropertyApprovalAuditLog
"""

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('property_owners', '0001_initial'),  # Adjust based on your actual migrations
    ]

    operations = [
        migrations.CreateModel(
            name='PropertyApprovalRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('SUBMITTED', 'Submitted for Review'), ('UNDER_REVIEW', 'Under Review'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('REVOKED', 'Approval Revoked')], db_index=True, default='SUBMITTED', max_length=20)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('submission_data', models.JSONField(blank=True, default=dict, help_text='Snapshot of property data at submission time')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('decision', models.CharField(blank=True, choices=[('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], max_length=20, null=True)),
                ('approval_reason', models.TextField(blank=True, help_text='Why property was approved (optional)')),
                ('rejection_reason', models.TextField(blank=True, help_text='MANDATORY if decision=REJECTED. Visible to owner.')),
                ('admin_notes', models.TextField(blank=True, help_text='Internal admin notes (NOT visible to owner)')),
                ('approved_until', models.DateField(blank=True, help_text='Optional: auto-revoke approval on this date (for trial periods)', null=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('revocation_reason', models.TextField(blank=True)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_requests', to='property_owners.property')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='property_reviews', to='auth.user')),
                ('revoked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='property_revocations', to='auth.user')),
                ('submitted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='property_submissions', to='auth.user')),
            ],
            options={
                'ordering': ['-submitted_at'],
            },
        ),
        migrations.CreateModel(
            name='PropertyApprovalAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('action', models.CharField(choices=[('SUBMITTED', 'Property Submitted'), ('APPROVED', 'Property Approved'), ('REJECTED', 'Property Rejected'), ('REVOKED', 'Approval Revoked'), ('CHECKLIST_UPDATED', 'Checklist Item Updated'), ('NOTES_ADDED', 'Admin Notes Added')], max_length=50)),
                ('action_details', models.JSONField(blank=True, default=dict)),
                ('approval_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='property_owners.propertyapprovalrequest')),
                ('performed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='property_approval_actions', to='auth.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PropertyApprovalChecklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('items', models.JSONField(blank=True, default=dict, help_text='Dict mapping CHECKLIST_ITEMS to {status: PASS/FAIL/PENDING, notes: ""}')),
                ('all_passed', models.BooleanField(default=False)),
                ('last_reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('approval_request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='checklist', to='property_owners.propertyapprovalrequest')),
            ],
            options={
                'verbose_name_plural': 'Property Approval Checklists',
            },
        ),
        migrations.AddIndex(
            model_name='propertyapprovalrequest',
            index=models.Index(fields=['property', 'status'], name='property_ow_propert_idx'),
        ),
        migrations.AddIndex(
            model_name='propertyapprovalrequest',
            index=models.Index(fields=['status', 'submitted_at'], name='property_ow_status_idx'),
        ),
    ]
