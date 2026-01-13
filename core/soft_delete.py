"""
Soft delete mixin for Django models.
Prevents permanent data loss by marking records as deleted instead of removing them.
"""
from django.db import models
from django.utils import timezone


class SoftDeleteMixin(models.Model):
    """
    Mixin to add soft delete functionality to any model.
    
    Usage:
        class MyModel(SoftDeleteMixin, TimeStampedModel):
            name = models.CharField(max_length=100)
    
    Then in admin or views:
        obj.soft_delete()  # Mark as deleted
        obj.restore()      # Restore
    """
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Soft delete flag - if True, record is logically deleted'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when record was soft deleted'
    )
    deleted_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted',
        help_text='User who soft deleted this record'
    )
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user=None):
        """
        Soft delete this record.
        
        Args:
            user: User performing the deletion (optional)
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def restore(self):
        """Restore a soft-deleted record"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    @property
    def deletion_info(self):
        """Get formatted deletion info"""
        if self.is_deleted and self.deleted_at:
            info = f"Deleted on {self.deleted_at.strftime('%Y-%m-%d %H:%M')}"
            if self.deleted_by:
                info += f" by {self.deleted_by.get_full_name() or self.deleted_by.email}"
            return info
        return "Active"


class SoftDeleteManager(models.Manager):
    """
    Manager that excludes soft-deleted records by default.
    
    Usage:
        class MyModel(SoftDeleteMixin, models.Model):
            objects = SoftDeleteManager()
            all_objects = models.Manager()  # To access deleted records
    
    Then:
        MyModel.objects.all()      # Returns only active records
        MyModel.all_objects.all()  # Returns all records (including deleted)
    """
    def get_queryset(self):
        """Override to exclude soft-deleted records"""
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """
    Manager that includes all records (including soft-deleted).
    """
    def get_queryset(self):
        """Return all records"""
        return super().get_queryset()
    
    def deleted(self):
        """Return only soft-deleted records"""
        return self.get_queryset().filter(is_deleted=True)
    
    def active(self):
        """Return only active (not deleted) records"""
        return self.get_queryset().filter(is_deleted=False)
