"""Status synchronization utilities for bookings."""
from django.http import JsonResponse
from .models import Booking


def get_booking_status(request, booking_id):
    """API endpoint to fetch current booking status."""
    try:
        booking = Booking.objects.get(booking_id=booking_id, user=request.user)
        
        return JsonResponse({
            'booking_id': str(booking.booking_id),
            'status': booking.status,
            'total_amount': str(booking.total_amount),
            'amount_paid': str(booking.amount_paid),
            'refund_amount': str(booking.refund_amount) if booking.refund_amount else '0.00',
            'expires_at': booking.expires_at.isoformat() if booking.expires_at else None,
            'updated_at': booking.updated_at.isoformat()
        })
    
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
