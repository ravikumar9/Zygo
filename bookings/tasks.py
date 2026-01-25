"""
Background tasks for GoExplorer using django-rq
"""
from django_rq import job
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string


@job
def auto_expire_reservations():
    """
    Auto-expire bookings that haven't been paid in 10 minutes.
    Releases inventory and marks booking as EXPIRED.
    
    This task should be run every 5 minutes via RQ scheduler.
    """
    from bookings.models import Booking
    from hotels.models import Hotel, RoomAvailability
    from buses.models import BusSchedule, BusBookingSeat
    
    now = timezone.now()
    ten_min_ago = now - timedelta(minutes=10)
    
    # Find expired reservations
    expired_bookings = Booking.objects.filter(
        status='reserved',
        reserved_at__lte=ten_min_ago,
        is_deleted=False
    )
    
    updated_count = 0
    
    for booking in expired_bookings:
        try:
            # Release inventory based on booking type
            if booking.booking_type == 'hotel':
                release_hotel_inventory(booking)
            elif booking.booking_type == 'bus':
                release_bus_inventory(booking)
            elif booking.booking_type == 'package':
                release_package_inventory(booking)
            
            # Mark as expired
            booking.status = 'expired'
            booking.cancelled_at = now
            booking.save(update_fields=['status', 'cancelled_at', 'updated_at'])
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info("[BOOKING_EXPIRED] booking=%s status=expired reserved_at=%s", booking.booking_id, booking.reserved_at)
                payload = {'booking_id': str(booking.booking_id), 'event': 'booking_expired'}
                logger.info("[NOTIFICATION_EMAIL] payload=%s", payload)
                logger.info("[NOTIFICATION_SMS] payload=%s", payload)
                logger.info("[NOTIFICATION_WHATSAPP] payload=%s", payload)
            except Exception:
                pass
            
            # Send email to user
            send_booking_expired_email(booking)
            
            updated_count += 1
        except Exception as e:
            print(f"Error expiring booking {booking.booking_id}: {str(e)}")
    
    return {
        'expired_count': updated_count,
        'timestamp': str(now),
        'status': 'completed'
    }


def release_hotel_inventory(booking):
    """Release hotel room back to availability"""
    from hotels.models import RoomAvailability
    
    hotel_booking = booking.hotel_details
    
    # Restore available rooms for each night
    for i in range(hotel_booking.total_nights):
        current_date = hotel_booking.check_in + timedelta(days=i)
        
        availability, created = RoomAvailability.objects.get_or_create(
            hotel=hotel_booking.room_type.hotel,
            date=current_date,
            defaults={'available_rooms': hotel_booking.number_of_rooms}
        )
        
        if not created:
            availability.available_rooms += hotel_booking.number_of_rooms
            availability.save(update_fields=['available_rooms', 'updated_at'])


def release_bus_inventory(booking):
    """Release bus seats back to availability"""
    from buses.models import BusBookingSeat
    
    bus_booking = booking.bus_details
    
    # Delete all seat bookings for this reservation
    BusBookingSeat.objects.filter(booking=bus_booking).delete()
    
    # Update schedule available seats
    schedule = bus_booking.bus_schedule
    booked_seats = BusBookingSeat.objects.filter(schedule=schedule).count()
    schedule.available_seats = schedule.route.bus.total_seats - booked_seats
    schedule.save(update_fields=['available_seats', 'updated_at'])


def release_package_inventory(booking):
    """Release package slot back to availability"""
    package_booking = booking.package_details
    
    departure = package_booking.package_departure
    if departure.available_slots < departure.total_slots:
        departure.available_slots += 1
        departure.save(update_fields=['available_slots', 'updated_at'])


def send_booking_expired_email(booking):
    """Send email notification that booking expired"""
    try:
        subject = f"Your GoExplorer booking {booking.booking_id} has expired"
        
        context = {
            'booking_id': booking.booking_id,
            'booking_type': booking.get_booking_type_display(),
            'created_at': booking.created_at,
        }
        
        html_message = render_to_string('emails/booking_expired.html', context)
        
        send_mail(
            subject,
            f"Your booking {booking.booking_id} expired due to non-payment.",
            'noreply@goexplorer.in',
            [booking.customer_email],
            html_message=html_message,
            fail_silently=True
        )
    except Exception as e:
        print(f"Error sending expiry email for {booking.booking_id}: {str(e)}")


@job
def cleanup_failed_bookings():
    """
    Optional: Completely delete failed bookings older than 24 hours
    Run daily via cron
    """
    from bookings.models import Booking
    
    now = timezone.now()
    day_ago = now - timedelta(hours=24)
    
    failed_bookings = Booking.objects.filter(
        status__in=['payment_failed', 'expired'],
        updated_at__lte=day_ago
    )
    
    count = failed_bookings.count()
    failed_bookings.delete()
    
    return {
        'deleted_count': count,
        'timestamp': str(now),
        'status': 'completed'
    }
