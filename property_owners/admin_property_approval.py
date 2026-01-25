"""
Admin property approval workflow — Step 5 of property registration.
Allows admins to review and approve/reject pending properties.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from property_owners.models import Property, AdminApprovalLog


def is_admin(user):
    """Check if user is platform admin"""
    return hasattr(user, 'user_role') and user.user_role.role == 'admin'


@login_required
@user_passes_test(is_admin)
def admin_pending_properties_list(request):
    """Admin dashboard: list all pending properties awaiting approval"""
    pending = Property.objects.filter(status='PENDING').select_related(
        'owner__user', 'city', 'property_type'
    ).order_by('-submitted_at')
    
    rejected = Property.objects.filter(status='REJECTED').order_by('-created_at')
    approved = Property.objects.filter(status='APPROVED').order_by('-approved_at')
    
    stats = {
        'pending_count': pending.count(),
        'approved_count': approved.count(),
        'rejected_count': rejected.count(),
    }
    
    filter_status = request.GET.get('status', 'pending')
    if filter_status == 'approved':
        properties = approved[:50]
    elif filter_status == 'rejected':
        properties = rejected[:50]
    else:
        properties = pending
    
    return render(request, 'property_owners/admin_pending_properties.html', {
        'properties': properties,
        'stats': stats,
        'filter_status': filter_status,
    })


@login_required
@user_passes_test(is_admin)
def admin_property_review(request, property_id):
    """Admin property review page: view all details before approving/rejecting"""
    prop = get_object_or_404(Property, id=property_id)
    rooms = prop.room_types.all()
    
    # Compute completeness check
    checks, is_complete = prop.has_required_fields()
    
    context = {
        'property': prop,
        'rooms': rooms,
        'completion_checks': checks,
        'is_complete': is_complete,
        'can_approve': prop.status == 'PENDING' and is_complete,
        'can_reject': prop.status == 'PENDING',
    }
    return render(request, 'property_owners/admin_property_review.html', context)


@login_required
@user_passes_test(is_admin)
def admin_approve_property(request, property_id):
    """Admin approves a pending property → status = APPROVED (LIVE)"""
    prop = get_object_or_404(Property, id=property_id)
    
    if prop.status != 'PENDING':
        messages.warning(request, f'Property status is {prop.get_status_display()}, cannot approve')
        return redirect('property_owners:admin-pending-list')
    
    checks, is_complete = prop.has_required_fields()
    if not is_complete or prop.room_types.count() == 0:
        missing = [k for k, v in checks.items() if not v]
        messages.error(request, f'Cannot approve: Missing {", ".join(missing)}')
        return redirect('property_owners:admin-property-review', property_id=property_id)
    
    # Approve
    try:
        prop.approve(admin_user=request.user)
        
        # Log approval
        AdminApprovalLog.objects.create(
            admin=request.user,
            approval_type='property_owner',
            subject=f'Property Approved: {prop.name}',
            details={'property_id': prop.id, 'owner': prop.owner.business_name},
            decision='approved'
        )
        
        messages.success(request, f'✅ Property "{prop.name}" approved and is now LIVE!')
    except AssertionError as e:
        messages.error(request, f'Approval failed: {str(e)}')
    
    return redirect('property_owners:admin-pending-list')


@login_required
@user_passes_test(is_admin)
def admin_reject_property(request, property_id):
    """Admin rejects a pending property with mandatory reason"""
    prop = get_object_or_404(Property, id=property_id)
    
    if prop.status != 'PENDING':
        messages.warning(request, f'Property status is {prop.get_status_display()}, cannot reject')
        return redirect('property_owners:admin-pending-list')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Rejection reason is required')
            return render(request, 'property_owners/admin_reject_property.html', {'property': prop})
        
        try:
            prop.reject(reason=reason)
            
            # Log rejection
            AdminApprovalLog.objects.create(
                admin=request.user,
                approval_type='property_owner',
                subject=f'Property Rejected: {prop.name}',
                details={'property_id': prop.id, 'owner': prop.owner.business_name},
                decision='rejected',
                reason=reason
            )
            
            messages.success(request, f'✅ Property "{prop.name}" rejected. Owner can view reason and resubmit.')
        except AssertionError as e:
            messages.error(request, f'Rejection failed: {str(e)}')
        
        return redirect('property_owners:admin-pending-list')
    
    return render(request, 'property_owners/admin_reject_property.html', {'property': prop})
