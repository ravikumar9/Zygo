"""
Signals for Booking app - auto-set timestamps for state transitions
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Booking


@receiver(pre_save, sender=Booking)
def set_reserved_at_timestamp(sender, instance, **kwargs):
    """
    Auto-set reserved_at timestamp when booking is created with RESERVED status.
    Also ensures confirmed_at is set when status transitions to CONFIRMED.
    """
    # Only set reserved_at if it's a new booking in RESERVED state
    if instance.pk is None and instance.status == 'reserved':
        instance.reserved_at = timezone.now()
    
    # Set confirmed_at when status transitions to CONFIRMED (if not already set)
    if instance.pk is not None:
        try:
            old_instance = Booking.objects.get(pk=instance.pk)
            # Status changed to CONFIRMED and confirmed_at not yet set
            if old_instance.status != 'confirmed' and instance.status == 'confirmed' and not instance.confirmed_at:
                instance.confirmed_at = timezone.now()
            
            # Set expires_at based on reserved_at (30 minutes from reservation)
            if instance.status == 'reserved' and instance.reserved_at and not instance.expires_at:
                from datetime import timedelta
                instance.expires_at = instance.reserved_at + timedelta(minutes=30)
        except Booking.DoesNotExist:
            pass


@receiver(post_save, sender=Booking)
def log_booking_state_transition(sender, instance, created, **kwargs):
    """
    Log booking state transitions for audit trail.
    (Optional - can be extended to create BookingHistory records)
    """
    if created:
        # New booking created
        from django.contrib.admin.models import LogEntry, ADDITION
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth.models import User
        
        # This is handled by Django's admin interface automatically
        pass
