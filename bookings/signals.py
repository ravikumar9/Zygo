"""
Signals for Booking app - auto-set timestamps for state transitions
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Booking
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Booking)
def set_reserved_at_timestamp(sender, instance, **kwargs):
    """
    Auto-set reserved_at timestamp when booking is created with RESERVED status.
    Also ensures confirmed_at is set when status transitions to CONFIRMED.
    CRITICAL: expires_at is set to 10 minutes (inventory lock duration).
    """
    # Only set reserved_at if it's a new booking in RESERVED state
    if instance.pk is None and instance.status == 'reserved':
        instance.reserved_at = timezone.now()
        user_email = instance.user.email if instance.user else instance.customer_email
        logger.info("[BOOKING_RESERVED] booking=%s user=%s reserved_at=%s", 
                   instance.booking_id, user_email, instance.reserved_at)
    
    # Set confirmed_at when status transitions to CONFIRMED (if not already set)
    if instance.pk is not None:
        try:
            old_instance = Booking.objects.get(pk=instance.pk)
            
            # Status changed to CONFIRMED and confirmed_at not yet set
            if old_instance.status != 'confirmed' and instance.status == 'confirmed' and not instance.confirmed_at:
                instance.confirmed_at = timezone.now()
                user_email = instance.user.email if instance.user else instance.customer_email
                logger.info("[BOOKING_CONFIRMED] booking=%s user=%s confirmed_at=%s", 
                           instance.booking_id, user_email, instance.confirmed_at)
            
            # Set expires_at based on reserved_at (10 MINUTES from reservation - CRITICAL for inventory locking)
            if instance.status == 'reserved' and instance.reserved_at and not instance.expires_at:
                from datetime import timedelta
                instance.expires_at = instance.reserved_at + timedelta(minutes=10)
                logger.info("[BOOKING_EXPIRY_SET] booking=%s deadline=%s remaining_minutes=10", 
                           instance.booking_id, instance.expires_at)
                           
        except Booking.DoesNotExist:
            pass


@receiver(post_save, sender=Booking)
def log_booking_state_transition(sender, instance, created, **kwargs):
    """
    Log booking state transitions for audit trail.
    """
    if created:
        # Log new booking with inventory lock info
        user_email = instance.user.email if instance.user else instance.customer_email
        logger.info("[BOOKING_CREATED] booking=%s user=%s type=%s status=%s expires_at=%s", 
                   instance.booking_id, user_email, instance.booking_type, instance.status, instance.expires_at)
