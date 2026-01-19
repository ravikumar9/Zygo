"""
Management command to ensure all buses have seat layouts
"""
from django.core.management.base import BaseCommand
from buses.models import Bus, SeatLayout


class Command(BaseCommand):
    help = 'Ensure all buses have seat layouts'

    def handle(self, *args, **options):
        buses = Bus.objects.filter(is_active=True)
        
        created_count = 0
        for bus in buses:
            # Check if bus already has seat layout
            if not bus.seat_layout.exists():
                # Create default 32-seater layout (4 rows x 8 seats)
                for row in range(1, 5):  # 4 rows
                    for col in range(1, 9):  # 8 seats per row
                        seat_num = f"{row}{chr(64+col)}"  # 1A, 1B, etc.
                        SeatLayout.objects.get_or_create(
                            bus=bus,
                            seat_number=seat_num,
                            defaults={
                                'seat_type': 'seater',
                                'row': row,
                                'column': col,
                                'deck': 1,
                                'reserved_for': 'general',
                            }
                        )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created seat layout for bus {bus.bus_number}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully ensured seats for {created_count} buses')
        )
