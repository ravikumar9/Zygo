from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from bookings.models import Booking
from payments.models import Invoice, Payment
from hotels.models import Hotel
from property_owners.models import Property
from users.models import User
from .models import OwnerPayout, PlatformLedger


def is_admin_user(user):
    """Check if user has admin role"""
    return user.groups.filter(name__in=['SUPER_ADMIN', 'FINANCE_ADMIN', 'PROPERTY_ADMIN', 'SUPPORT_ADMIN']).exists()


def is_super_or_finance_admin(user):
    """Check if user is SUPER_ADMIN or FINANCE_ADMIN"""
    return user.groups.filter(name__in=['SUPER_ADMIN', 'FINANCE_ADMIN']).exists()


@login_required
@user_passes_test(is_super_or_finance_admin)
def admin_dashboard(request):
    """Super admin dashboard with summary metrics and booking table"""
    
    # Date filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    property_id = request.GET.get('property')
    status = request.GET.get('status')
    payment_mode = request.GET.get('payment_mode')
    wallet_filter = request.GET.get('wallet_used')  # 'yes' or 'no'
    
    # Base queryset
    bookings = Booking.objects.select_related('user').all()
    
    # Apply filters
    if date_from:
        bookings = bookings.filter(created_at__date__gte=date_from)
    if date_to:
        bookings = bookings.filter(created_at__date__lte=date_to)
    if status:
        bookings = bookings.filter(status=status)
    
    # Calculate summary metrics
    total_bookings = bookings.count()
    
    total_revenue = bookings.filter(
        status='confirmed'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Calculate service fee from hotel_details.price_snapshot
    total_service_fee = Decimal('0')
    for booking in bookings.filter(status='confirmed'):
        try:
            if hasattr(booking, 'hotel_details') and booking.hotel_details:
                price_snapshot = booking.hotel_details.price_snapshot or {}
                service_fee = price_snapshot.get('service_fee', 0)
                if isinstance(service_fee, (int, float)):
                    total_service_fee += Decimal(str(service_fee))
        except:
            pass
    
    total_wallet_used = Decimal('0')
    for booking in bookings.filter(status='confirmed'):
        if booking.wallet_balance_before and booking.wallet_balance_after:
            total_wallet_used += (booking.wallet_balance_before - booking.wallet_balance_after)
    
    cancellations_count = bookings.filter(status='cancelled').count()
    
    active_properties = Property.objects.filter(status='APPROVED', is_active=True).count()
    pending_approvals = Property.objects.filter(status='PENDING', is_active=True).count()
    
    # Booking table data
    booking_list = bookings.order_by('-created_at')[:100]  # Latest 100
    
    # Get all properties for filter dropdown
    properties = Hotel.objects.filter(is_active=True).values('id', 'name')
    
    context = {
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'total_service_fee': total_service_fee,
        'total_wallet_used': total_wallet_used,
        'cancellations_count': cancellations_count,
        'active_properties': active_properties,
        'pending_approvals': pending_approvals,
        'booking_list': booking_list,
        'properties': properties,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'property': property_id,
            'status': status,
            'payment_mode': payment_mode,
            'wallet_used': wallet_filter,
        }
    }
    
    return render(request, 'finance/admin_dashboard.html', context)


@login_required
@user_passes_test(is_super_or_finance_admin)
def property_metrics(request):
    """Property-level dashboard showing per-property metrics"""
    
    # Get all approved properties
    properties = Property.objects.filter(status='APPROVED', is_active=True).select_related('owner')
    
    property_data = []
    for property_obj in properties:
        # Get linked hotel if exists
        try:
            hotel = Hotel.objects.get(owner_property=property_obj)
        except Hotel.DoesNotExist:
            continue
        
        # Get revenue for this property
        hotel_bookings = Booking.objects.filter(
            hotel_booking__room_type__hotel=hotel,
            status='confirmed'
        )
        
        revenue = hotel_bookings.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        # Calculate service fee from price_snapshot
        service_fee = Decimal('0')
        for booking in hotel_bookings:
            if hasattr(booking, 'hotel_details'):
                price_snapshot = getattr(booking.hotel_details, 'price_snapshot', {}) or {}
                service_fee += Decimal(str(price_snapshot.get('service_fee', 0)))
        
        # Get payout info
        total_payout = OwnerPayout.objects.filter(
            property=hotel
        ).aggregate(total=Sum('net_payable_to_owner'))['total'] or Decimal('0')
        
        pending_payout = OwnerPayout.objects.filter(
            property=hotel,
            settlement_status='pending'
        ).aggregate(total=Sum('net_payable_to_owner'))['total'] or Decimal('0')
        
        property_data.append({
            'property': property_obj,
            'hotel': hotel,
            'revenue': revenue,
            'service_fee': service_fee,
            'total_payout': total_payout,
            'pending_payout': pending_payout,
        })
    
    context = {
        'property_data': property_data,
    }
    
    return render(request, 'finance/property_metrics.html', context)


@login_required
@user_passes_test(is_admin_user)
def booking_table(request):
    """Filterable booking table for all admin roles"""
    
    # Filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    property_id = request.GET.get('property')
    status = request.GET.get('status')
    payment_mode = request.GET.get('payment_mode')
    wallet_filter = request.GET.get('wallet_used')
    
    bookings = Booking.objects.select_related('user').all()
    
    if date_from:
        bookings = bookings.filter(created_at__date__gte=date_from)
    if date_to:
        bookings = bookings.filter(created_at__date__lte=date_to)
    if status:
        bookings = bookings.filter(status=status)
    if property_id:
        bookings = bookings.filter(hotel_booking__room_type__hotel_id=property_id)
    
    bookings = bookings.order_by('-created_at')
    
    properties = Hotel.objects.filter(is_active=True).values('id', 'name')
    
    context = {
        'bookings': bookings,
        'properties': properties,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'property': property_id,
            'status': status,
            'payment_mode': payment_mode,
            'wallet_used': wallet_filter,
        }
    }
    
    return render(request, 'finance/booking_table.html', context)


@login_required
def owner_earnings(request):
    """Owner dashboard showing bookings and earnings"""
    
    # Check if user owns any properties via PropertyOwner
    from property_owners.models import PropertyOwner
    
    try:
        property_owner = PropertyOwner.objects.get(user=request.user)
        owned_properties = Property.objects.filter(owner=property_owner, status='APPROVED')
    except PropertyOwner.DoesNotExist:
        owned_properties = Property.objects.none()
    
    if not owned_properties.exists():
        return render(request, 'finance/owner_earnings.html', {
            'error': 'You do not own any approved properties.'
        })
    
    # Get hotels linked to owned properties
    owned_hotels = Hotel.objects.filter(owner_property__in=owned_properties)
    
    # Get all bookings for owned hotels
    bookings = Booking.objects.filter(
        hotel_booking__room_type__hotel__in=owned_hotels,
        status='confirmed'
    ).select_related('user', 'hotel_booking__room_type__hotel').order_by('-created_at')
    
    # Get payout summary
    total_gross = bookings.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
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
    
    context = {
        'owned_properties': owned_properties,
        'bookings': bookings[:50],  # Latest 50
        'total_bookings': bookings.count(),
        'total_gross': total_gross,
        'total_payouts': total_payouts,
        'pending_payouts': pending_payouts,
        'settled_payouts': settled_payouts,
        'recent_payouts': recent_payouts,
    }
    
    return render(request, 'finance/owner_earnings.html', context)


@login_required
def download_invoice(request, invoice_id):
    """Download user invoice PDF"""
    from django.http import HttpResponse, Http404
    
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        
        # Check permission: owner of booking or admin
        if invoice.booking.user != request.user and not is_admin_user(request.user):
            raise Http404("Invoice not found")
        
        # For now, return invoice data as text
        # In production, generate PDF using reportlab or weasyprint
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.txt"'
        
        content = f"""
INVOICE: {invoice.invoice_number}
Date: {invoice.invoice_date}

BILLING TO:
{invoice.billing_name}
{invoice.billing_email}
{invoice.billing_phone}

BOOKING DETAILS:
Property: {invoice.property_name}
Check-in: {invoice.check_in}
Check-out: {invoice.check_out}
Rooms: {invoice.num_rooms}
Meal Plan: {invoice.meal_plan}

AMOUNT BREAKDOWN:
Subtotal: ₹{invoice.subtotal}
Service Fee: ₹{invoice.service_fee}
Tax: ₹{invoice.tax_amount}
Discount: ₹{invoice.discount_amount}
Wallet Used: ₹{invoice.wallet_used}
---
Total: ₹{invoice.total_amount}
Paid: ₹{invoice.paid_amount}

Payment Mode: {invoice.payment_mode}
Payment Time: {invoice.payment_timestamp}

Thank you for your booking!
"""
        
        response.write(content)
        return response
        
    except Invoice.DoesNotExist:
        raise Http404("Invoice not found")
