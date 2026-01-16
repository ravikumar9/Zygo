"""
Management command to expire booking reservations after 10-minute hold time.
Run this every 1 minute via cron or Celery beat:
*/1 * * * * cd /path/to/project && python manage.py expire_bookings
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import Booking


class Command(BaseCommand):
    help = 'Expire booking reservations after 10-minute timeout and release inventory'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Find all payment_pending bookings that have exceeded their expiry time
        expired_bookings = Booking.objects.filter(
            status='payment_pending',
            expires_at__lte=now
        ).select_related('hotel_details', 'bus_details', 'package_details')

        count = 0
        for booking in expired_bookings:
            try:
                booking.status = 'expired'
                booking.save(update_fields=['status', 'updated_at'])
                booking.release_inventory_lock()
                count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'Expired booking {booking.booking_id} - inventory released'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'Failed to expire booking {booking.booking_id}: {str(e)}'
                ))

        if count > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Successfully expired {count} booking(s)'
            ))
        else:
            self.stdout.write(self.style.WARNING('No bookings to expire'))
