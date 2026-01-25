from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from decimal import Decimal

from bookings.models import Booking
from payments.models import Invoice
from hotels.models import Hotel
from property_owners.models import Property
from .models import OwnerPayout, PlatformLedger
from .serializers import (
    InvoiceSerializer,
    OwnerPayoutSerializer,
    PlatformLedgerSerializer,
    DashboardMetricsSerializer,
    BookingListSerializer,
)


def has_admin_role(user, *roles):
    """Check if user has any of the specified admin roles"""
    return user.groups.filter(name__in=roles).exists()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_metrics_api(request):
    """
    GET /api/admin/dashboard/metrics
    Required role: SUPER_ADMIN or FINANCE_ADMIN
    Returns: Dashboard summary metrics
    """
    # Permission check
    if not has_admin_role(request.user, 'SUPER_ADMIN', 'FINANCE_ADMIN'):
        return Response(
            {'error': 'Insufficient permissions. SUPER_ADMIN or FINANCE_ADMIN role required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    bookings = Booking.objects.all()
    
    if date_from:
        bookings = bookings.filter(created_at__date__gte=date_from)
    if date_to:
        bookings = bookings.filter(created_at__date__lte=date_to)
    
    # Calculate metrics
    total_bookings = bookings.count()
    
    total_revenue = bookings.filter(
        status='confirmed'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Service fee from price_snapshot
    total_service_fee = Decimal('0')
    for booking in bookings.filter(status='confirmed'):
        if hasattr(booking, 'hotel_details'):
            price_snapshot = getattr(booking.hotel_details, 'price_snapshot', {}) or {}
            total_service_fee += Decimal(str(price_snapshot.get('service_fee', 0)))
    
    # Wallet usage
    total_wallet_used = Decimal('0')
    for booking in bookings.filter(status='confirmed'):
        if booking.wallet_balance_before and booking.wallet_balance_after:
            total_wallet_used += (booking.wallet_balance_before - booking.wallet_balance_after)
    
    cancellations_count = bookings.filter(status='cancelled').count()
    active_properties = Property.objects.filter(status='APPROVED', is_active=True).count()
    pending_approvals = Property.objects.filter(status='PENDING', is_active=True).count()
    
    data = {
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'total_service_fee': total_service_fee,
        'total_wallet_used': total_wallet_used,
        'cancellations_count': cancellations_count,
        'active_properties': active_properties,
        'pending_approvals': pending_approvals,
    }
    
    serializer = DashboardMetricsSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoices_api(request):
    """
    GET /api/admin/invoices
    Required role: SUPER_ADMIN or FINANCE_ADMIN
    Returns: List of all invoices with filters
    """
    if not has_admin_role(request.user, 'SUPER_ADMIN', 'FINANCE_ADMIN'):
        return Response(
            {'error': 'Insufficient permissions. SUPER_ADMIN or FINANCE_ADMIN role required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    invoices = Invoice.objects.select_related('booking').all()
    
    # Filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)
    
    invoices = invoices.order_by('-created_at')
    
    serializer = InvoiceSerializer(invoices, many=True)
    return Response({
        'count': invoices.count(),
        'invoices': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bookings_api(request):
    """
    GET /api/admin/bookings
    Required role: Any admin role
    Returns: Filterable booking list
    """
    if not has_admin_role(request.user, 'SUPER_ADMIN', 'FINANCE_ADMIN', 'PROPERTY_ADMIN', 'SUPPORT_ADMIN'):
        return Response(
            {'error': 'Admin role required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    bookings = Booking.objects.select_related('user').all()
    
    # Filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status_filter = request.GET.get('status')
    property_id = request.GET.get('property_id')
    
    if date_from:
        bookings = bookings.filter(created_at__date__gte=date_from)
    if date_to:
        bookings = bookings.filter(created_at__date__lte=date_to)
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if property_id:
        bookings = bookings.filter(hotel_booking__room_type__hotel_id=property_id)
    
    bookings = bookings.order_by('-created_at')
    
    serializer = BookingListSerializer(bookings, many=True)
    return Response({
        'count': bookings.count(),
        'bookings': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def owner_earnings_api(request):
    """
    GET /api/owner/earnings
    Required role: Property owner (user owns at least one property)
    Returns: Earnings summary for property owner
    """
    # Check if user is a property owner
    from property_owners.models import PropertyOwner
    
    try:
        property_owner = PropertyOwner.objects.get(user=request.user)
        owned_properties = Property.objects.filter(owner=property_owner, status='APPROVED')
    except PropertyOwner.DoesNotExist:
        owned_properties = Property.objects.none()
    
    if not owned_properties.exists():
        return Response(
            {'error': 'You do not own any approved properties'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get hotels linked to owned properties
    owned_hotels = Hotel.objects.filter(owner_property__in=owned_properties)
    
    # Get bookings for owned hotels
    bookings = Booking.objects.filter(
        hotel_booking__room_type__hotel__in=owned_hotels,
        status='confirmed'
    ).select_related('hotel_booking__room_type__hotel')
    
    total_bookings = bookings.count()
    
    total_gross = bookings.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Get payout summary
    total_payouts = OwnerPayout.objects.filter(
        property__in=owned_hotels
    ).aggregate(total=Sum('net_payable_to_owner'))['total'] or Decimal('0')
    
    pending_payouts = OwnerPayout.objects.filter(
        property__in=owned_hotels,
        settlement_status='pending'
    ).aggregate(total=Sum('net_payable_to_owner'))['total'] or Decimal('0')
    
    settled_payouts = OwnerPayout.objects.filter(
        property__in=owned_hotels,
        settlement_status='settled'
    ).aggregate(total=Sum('net_payable_to_owner'))['total'] or Decimal('0')
    
    # Get recent payouts
    recent_payouts = OwnerPayout.objects.filter(
        property__in=owned_hotels
    ).select_related('property', 'booking').order_by('-created_at')[:20]
    
    payout_serializer = OwnerPayoutSerializer(recent_payouts, many=True)
    
    return Response({
        'total_bookings': total_bookings,
        'total_gross': total_gross,
        'total_payouts': total_payouts,
        'pending_payouts': pending_payouts,
        'settled_payouts': settled_payouts,
        'recent_payouts': payout_serializer.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_detail_api(request, invoice_id):
    """
    GET /api/invoices/<id>
    Required: User must own the booking or be admin
    Returns: Invoice details
    """
    try:
        invoice = Invoice.objects.select_related('booking').get(id=invoice_id)
    except Invoice.DoesNotExist:
        return Response(
            {'error': 'Invoice not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Permission check
    is_admin = has_admin_role(request.user, 'SUPER_ADMIN', 'FINANCE_ADMIN')
    is_owner = invoice.booking.user == request.user
    
    if not (is_admin or is_owner):
        return Response(
            {'error': 'Insufficient permissions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = InvoiceSerializer(invoice)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ledger_api(request):
    """
    GET /api/admin/ledger
    Required role: SUPER_ADMIN or FINANCE_ADMIN
    Returns: Platform ledger (daily aggregated data)
    """
    if not has_admin_role(request.user, 'SUPER_ADMIN', 'FINANCE_ADMIN'):
        return Response(
            {'error': 'Insufficient permissions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    ledger_entries = PlatformLedger.objects.all().order_by('-date')
    
    # Filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        ledger_entries = ledger_entries.filter(date__gte=date_from)
    if date_to:
        ledger_entries = ledger_entries.filter(date__lte=date_to)
    
    serializer = PlatformLedgerSerializer(ledger_entries, many=True)
    return Response({
        'count': ledger_entries.count(),
        'ledger': serializer.data
    })
