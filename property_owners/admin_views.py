"""
Admin approval views - manage property owner requests and approvals
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone

from property_owners.models import (
    PropertyUpdateRequest, AdminApprovalLog, UserRole, SeasonalPricing
)


def is_admin(user):
    """Check if user is platform admin"""
    return hasattr(user, 'user_role') and user.user_role.role == 'admin'


class AdminUpdateRequestsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin dashboard for approving/rejecting update requests"""
    template_name = 'property_owners/admin_update_requests.html'
    context_object_name = 'requests'
    paginate_by = 20
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get_queryset(self):
        status = self.request.GET.get('status', 'pending')
        qs = PropertyUpdateRequest.objects.all()
        if status in ['pending', 'approved', 'rejected']:
            qs = qs.filter(status=status)
        return qs.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_count'] = PropertyUpdateRequest.objects.filter(status='pending').count()
        context['approved_count'] = PropertyUpdateRequest.objects.filter(status='approved').count()
        context['rejected_count'] = PropertyUpdateRequest.objects.filter(status='rejected').count()
        return context


@login_required
@user_passes_test(is_admin)
def approve_update_request(request, request_id):
    """Admin approves an update request"""
    update_req = get_object_or_404(PropertyUpdateRequest, pk=request_id)
    
    if request.method == 'POST':
        update_req.approve(request.user)
        
        # Log approval
        AdminApprovalLog.objects.create(
            admin=request.user,
            approval_type='update_request',
            subject=f'{update_req.owner.business_name} - {update_req.get_change_type_display()}',
            details={'request_id': update_req.id, 'type': update_req.change_type},
            decision='approved'
        )
        
        messages.success(request, 'Update request approved successfully')
        return redirect('property_owners:admin-update-requests')
    
    return render(request, 'property_owners/admin_approve.html', {'request': update_req})


@login_required
@user_passes_test(is_admin)
def reject_update_request(request, request_id):
    """Admin rejects an update request"""
    update_req = get_object_or_404(PropertyUpdateRequest, pk=request_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        update_req.reject(request.user, reason)
        
        # Log rejection
        AdminApprovalLog.objects.create(
            admin=request.user,
            approval_type='update_request',
            subject=f'{update_req.owner.business_name} - {update_req.get_change_type_display()}',
            details={'request_id': update_req.id, 'type': update_req.change_type},
            decision='rejected',
            reason=reason
        )
        
        messages.info(request, 'Update request rejected')
        return redirect('property_owners:admin-update-requests')
    
    return render(request, 'property_owners/admin_reject.html', {'request': update_req})


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard with statistics"""
    from property_owners.models import UserRole
    from bookings.models import Booking
    from decimal import Decimal
    
    context = {
        'total_property_owners': UserRole.objects.filter(role='property_owner', is_active=True).count(),
        'pending_requests': PropertyUpdateRequest.objects.filter(status='pending').count(),
        'approved_today': PropertyUpdateRequest.objects.filter(
            status='approved',
            reviewed_at__date=timezone.now().date()
        ).count(),
        'total_approvals': AdminApprovalLog.objects.filter(decision='approved').count(),
        'recent_logs': AdminApprovalLog.objects.order_by('-created_at')[:10],
    }
    
    return render(request, 'property_owners/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def view_approval_history(request):
    """View admin approval history for audit trail"""
    logs = AdminApprovalLog.objects.order_by('-created_at')
    
    # Filter by admin
    admin_id = request.GET.get('admin')
    if admin_id:
        logs = logs.filter(admin_id=admin_id)
    
    # Filter by type
    approval_type = request.GET.get('type')
    if approval_type:
        logs = logs.filter(approval_type=approval_type)
    
    return render(request, 'property_owners/approval_history.html', {
        'logs': logs[:100],
        'total': logs.count(),
    })
