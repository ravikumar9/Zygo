"""
Management command to backfill expires_at for existing bookings
This is a ONE-TIME migration to sync old bookings with the new 10-minute expiry rule
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from bookings.models import Booking


class Command(BaseCommand):
    help = 'Backfill expires_at for existing reserved/payment_pending bookings (10-minute rule)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Target: reserved or payment_pending bookings WITHOUT proper expires_at
        # OR with old 30-minute expiry that needs correction
        target_bookings = Booking.objects.filter(
            status__in=['reserved', 'payment_pending'],
            reserved_at__isnull=False
        )
        
        count_updated = 0
        count_expired = 0
        count_skipped = 0
        
        now = timezone.now()
        
        self.stdout.write(self.style.WARNING(
            f'\n{"="*60}\n'
            f'  BACKFILL expires_at FOR EXISTING BOOKINGS\n'
            f'{"="*60}\n'
        ))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('[DRY RUN MODE - No changes will be made]\n'))
        
        for booking in target_bookings:
            # Calculate what expires_at SHOULD be (reserved_at + 10 minutes)
            correct_expires_at = booking.reserved_at + timedelta(minutes=10)
            
            # Check if already expired based on correct 10-min deadline
            if now >= correct_expires_at:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ⏰ EXPIRED: Booking {booking.booking_id} '
                        f'(reserved {booking.reserved_at} → deadline {correct_expires_at}) - '
                        f'Will be marked as expired'
                    )
                )
                
                if not dry_run:
                    booking.status = 'expired'
                    booking.expires_at = correct_expires_at
                    booking.save(update_fields=['status', 'expires_at', 'updated_at'])
                    
                    # Release inventory
                    from hotels.channel_manager_service import release_inventory_on_failure
                    release_inventory_on_failure(booking)
                    
                    self.stdout.write(self.style.SUCCESS(f'    ✅ Marked as expired and inventory released'))
                
                count_expired += 1
                
            else:
                # Still valid - update expires_at to correct value
                old_expires = booking.expires_at
                
                # Only update if different (avoid unnecessary writes)
                if old_expires != correct_expires_at:
                    remaining_seconds = int((correct_expires_at - now).total_seconds())
                    
                    self.stdout.write(
                        f'  🔄 UPDATE: Booking {booking.booking_id} '
                        f'(old: {old_expires} → new: {correct_expires_at}) - '
                        f'{remaining_seconds}s remaining'
                    )
                    
                    if not dry_run:
                        booking.expires_at = correct_expires_at
                        booking.save(update_fields=['expires_at', 'updated_at'])
                        self.stdout.write(self.style.SUCCESS(f'    ✅ Updated'))
                    
                    count_updated += 1
                else:
                    count_skipped += 1
        
        # Summary
        self.stdout.write(
            self.style.WARNING(
                f'\n{"="*60}\n'
                f'  SUMMARY\n'
                f'{"="*60}\n'
            )
        )
        
        total = count_updated + count_expired + count_skipped
        
        self.stdout.write(f'  Total Scanned: {total}')
        self.stdout.write(self.style.SUCCESS(f'  ✅ Updated (valid): {count_updated}'))
        self.stdout.write(self.style.ERROR(f'  ⏰ Expired (auto-marked): {count_expired}'))
        self.stdout.write(f'  ⏭️  Skipped (already correct): {count_skipped}')
        
        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f'\n[DRY RUN] No changes made. Run without --dry-run to apply.\n'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Backfill complete! All active bookings now use 10-minute expiry.\n'
                )
            )
