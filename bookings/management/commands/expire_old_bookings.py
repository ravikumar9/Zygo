"""
Management command to expire old bookings and release inventory.

Usage:
    python manage.py expire_old_bookings

This command should be run via cron job every 5 minutes:
    */5 * * * * cd /path/to/project && python manage.py expire_old_bookings
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from bookings.models import Booking
from hotels.channel_manager_service import release_inventory_on_failure
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Expire old reserved bookings past their 10-minute deadline and release inventory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be expired without actually expiring',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        # Find all reserved/payment_pending bookings past their deadline
        expired_bookings = Booking.objects.filter(
            status__in=['reserved', 'payment_pending'],
            reserved_at__isnull=False
        ).select_related('hotel_details__room_type__hotel')
        
        expired_count = 0
        error_count = 0
        
        for booking in expired_bookings:
            deadline = booking.reservation_deadline
            if not deadline:
                continue
                
            if now >= deadline:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[DRY RUN] Would expire: {booking.booking_id} '
                            f'(created: {booking.reserved_at}, deadline: {deadline})'
                        )
                    )
                    expired_count += 1
                else:
                    try:
                        with transaction.atomic():
                            # Lock booking row
                            booking_locked = Booking.objects.select_for_update().get(pk=booking.pk)
                            
                            # Double-check status hasn't changed
                            if booking_locked.status not in ['reserved', 'payment_pending']:
                                continue
                            
                            # Update booking status
                            booking_locked.status = 'expired'
                            booking_locked.expires_at = deadline
                            booking_locked.save(update_fields=['status', 'expires_at', 'updated_at'])
                            
                            # Release inventory
                            release_inventory_on_failure(booking_locked)
                            
                            logger.info(
                                "[BOOKING_EXPIRED] booking=%s user=%s reserved_at=%s deadline=%s",
                                booking_locked.booking_id, 
                                booking_locked.user.email,
                                booking_locked.reserved_at,
                                deadline
                            )
                            
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Expired: {booking_locked.booking_id} (user: {booking_locked.user.email})'
                                )
                            )
                            expired_count += 1
                            
                    except Exception as e:
                        logger.error(
                            "[BOOKING_EXPIRE_ERROR] booking=%s error=%s",
                            booking.booking_id,
                            str(e)
                        )
                        self.stdout.write(
                            self.style.ERROR(
                                f'Error expiring {booking.booking_id}: {str(e)}'
                            )
                        )
                        error_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] Would expire {expired_count} bookings'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Expired {expired_count} bookings ({error_count} errors)'
                )
            )
