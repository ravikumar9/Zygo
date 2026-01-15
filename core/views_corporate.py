"""Corporate dashboard views"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from decimal import Decimal

from core.models import CorporateAccount
from bookings.models import Booking
from payments.models import Wallet


@login_required
def corporate_signup(request):
    """Corporate account signup/onboarding form"""
    # Check if user already has corporate account
    domain = request.user.email.split('@')[-1] if '@' in request.user.email else None
    existing = CorporateAccount.objects.filter(email_domain=domain).first() if domain else None
    
    if existing:
        messages.info(request, f'Your organization ({existing.company_name}) already has a corporate account.')
        return redirect('corporate:dashboard')
    
    if request.method == 'POST':
        company_name = request.POST.get('company_name', '').strip()
        email_domain = request.POST.get('email_domain', '').strip().lower()
        gst_number = request.POST.get('gst_number', '').strip()
        account_type = request.POST.get('account_type', 'business')
        contact_person_name = request.POST.get('contact_person_name', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        
        # Validate
        if not all([company_name, email_domain, contact_person_name, contact_email, contact_phone]):
            messages.error(request, 'All fields except GST are required.')
            return render(request, 'corporate/signup.html', {
                'form_data': request.POST
            })
        
        # Check if domain already exists
        if CorporateAccount.objects.filter(email_domain=email_domain).exists():
            messages.error(request, f'Corporate account for {email_domain} already exists.')
            return redirect('corporate:dashboard')
        
        # Create corporate account
        corporate_account = CorporateAccount.objects.create(
            company_name=company_name,
            email_domain=email_domain,
            gst_number=gst_number,
            account_type=account_type,
            contact_person_name=contact_person_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            admin_user=request.user,
            status='pending_verification',
        )
        
        messages.success(request, 
            f'Corporate account submitted successfully! '
            f'Your application is under review. You will be notified once approved.')
        return redirect('corporate:dashboard')
    
    # Pre-fill with user data
    context = {
        'user_email': request.user.email,
        'user_domain': request.user.email.split('@')[-1] if '@' in request.user.email else '',
        'user_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'corporate/signup.html', context)


@login_required
def corporate_dashboard(request):
    """Corporate user dashboard - wallet, bookings, discounts, coupon history"""
    # Get corporate account for user's email domain
    domain = request.user.email.split('@')[-1] if '@' in request.user.email else None
    corporate_account = CorporateAccount.objects.filter(email_domain=domain).first() if domain else None
    
    if not corporate_account:
        messages.warning(request, 'You are not part of any corporate account. Sign up to get corporate benefits!')
        return redirect('corporate:signup')
    
    # Get wallet
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    # Get bookings
    bookings = Booking.objects.filter(
        user=request.user,
        is_deleted=False
    ).order_by('-created_at')[:10]
    
    # Get corporate bookings (bookings with corporate discount applied)
    corporate_bookings = Booking.objects.filter(
        user=request.user,
        is_deleted=False,
        channel_reference__icontains='"type": "corp"'
    )
    
    # Stats
    total_bookings = Booking.objects.filter(user=request.user, is_deleted=False).count()
    corporate_bookings_count = corporate_bookings.count()
    total_spent = Booking.objects.filter(
        user=request.user, 
        is_deleted=False,
        status='confirmed'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    
    # Corporate discount stats (parsed from channel_reference JSON)
    import json
    corporate_savings = Decimal('0')
    for booking in corporate_bookings:
        if booking.channel_reference:
            try:
                meta = json.loads(booking.channel_reference)
                if meta.get('type') == 'corp':
                    corporate_savings += Decimal(str(meta.get('discount_amount', 0)))
            except:
                pass
    
    context = {
        'corporate_account': corporate_account,
        'wallet': wallet,
        'bookings': bookings,
        'total_bookings': total_bookings,
        'corporate_bookings_count': corporate_bookings_count,
        'total_spent': total_spent,
        'corporate_savings': corporate_savings,
        'corporate_coupon': corporate_account.corporate_coupon if corporate_account.status == 'approved' else None,
    }
    return render(request, 'corporate/dashboard.html', context)


@login_required
def corporate_status(request):
    """Simplified status check page for pending/rejected accounts"""
    domain = request.user.email.split('@')[-1] if '@' in request.user.email else None
    corporate_account = CorporateAccount.objects.filter(email_domain=domain).first() if domain else None
    
    if not corporate_account:
        return redirect('corporate:signup')
    
    return render(request, 'corporate/status.html', {
        'corporate_account': corporate_account
    })
