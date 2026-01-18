"""
Bus Operator Registration Views - Session 3
Registration workflow: DRAFT -> PENDING_VERIFICATION -> APPROVED/REJECTED
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db import transaction
from .models import BusOperator
from .operator_forms import OperatorRegistrationForm


@login_required
def operator_create_draft(request):
    """Create or update operator registration draft"""
    # Get or create operator
    operator, created = BusOperator.objects.get_or_create(
        user=request.user,
        defaults={'approval_status': 'draft'}
    )
    
    # Only draft operators can edit
    if operator.approval_status != 'draft':
        messages.warning(request, "Only draft registrations can be edited. Contact admin if you need to change submitted data.")
        return redirect('buses:operator_detail', pk=operator.pk)
    
    if request.method == 'POST':
        form = OperatorRegistrationForm(request.POST, instance=operator)
        if form.is_valid():
            # Save to database
            with transaction.atomic():
                operator = form.save(commit=False)
                # Don't auto-submit - leave as DRAFT
                operator.save()
            
            messages.success(request, "Registration saved as draft. Complete all sections to submit for approval.")
            return redirect('buses:operator_detail', pk=operator.pk)
    else:
        form = OperatorRegistrationForm(instance=operator)
    
    # Calculate completion
    _, all_required = operator.has_required_fields()
    completion = operator.completion_percentage
    
    context = {
        'form': form,
        'operator': operator,
        'completion': completion,
        'page_title': 'Register as Bus Operator',
        'is_draft': True,
    }
    return render(request, 'buses/operator_form.html', context)


@login_required
def operator_submit(request, pk):
    """Submit draft registration for approval"""
    operator = get_object_or_404(BusOperator, pk=pk, user=request.user)
    
    # Only draft operators can submit
    if operator.approval_status != 'draft':
        messages.warning(request, "This registration has already been submitted.")
        return redirect('buses:operator_detail', pk=operator.pk)
    
    if request.method == 'POST':
        # Validate all required fields
        checks, has_all = operator.has_required_fields()
        if not has_all:
            missing = [k.replace('_', ' ').title() for k, v in checks.items() if not v]
            messages.error(request, f"Cannot submit. Incomplete sections: {', '.join(missing)}")
            return redirect('buses:operator_detail', pk=operator.pk)
        
        # Change status to PENDING_VERIFICATION
        with transaction.atomic():
            operator.approval_status = 'pending_verification'
            operator.submitted_at = timezone.now()
            operator.save()
        
        messages.success(request, "Registration submitted for admin approval. You'll receive an email when reviewed.")
        return redirect('buses:operator_detail', pk=operator.pk)
    
    # GET: Show confirmation page
    checks, has_all = operator.has_required_fields()
    context = {
        'operator': operator,
        'checks': checks,
        'completion': operator.completion_percentage,
        'can_submit': has_all,
    }
    return render(request, 'buses/operator_submit.html', context)


@login_required
def operator_detail(request, pk):
    """View operator registration status and details"""
    operator = get_object_or_404(BusOperator, pk=pk, user=request.user)
    
    checks, has_all = operator.has_required_fields()
    
    context = {
        'operator': operator,
        'completion': operator.completion_percentage,
        'checks': checks,
        'all_complete': has_all,
        'is_draft': operator.approval_status == 'draft',
        'is_pending': operator.approval_status == 'pending_verification',
        'is_approved': operator.approval_status == 'approved',
        'is_rejected': operator.approval_status == 'rejected',
    }
    return render(request, 'buses/operator_detail.html', context)


@login_required
def operator_dashboard(request):
    """Operator dashboard - show all registrations grouped by status"""
    try:
        operators = BusOperator.objects.filter(user=request.user)
    except BusOperator.DoesNotExist:
        operators = []
    
    # Group by status
    draft = operators.filter(approval_status='draft')
    pending = operators.filter(approval_status='pending_verification')
    approved = operators.filter(approval_status='approved')
    rejected = operators.filter(approval_status='rejected')
    
    context = {
        'draft_count': draft.count(),
        'pending_count': pending.count(),
        'approved_count': approved.count(),
        'rejected_count': rejected.count(),
        'operators': {
            'draft': draft,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
        }
    }
    return render(request, 'buses/operator_dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def operator_completion_json(request, pk):
    """JSON endpoint for completion percentage (AJAX)"""
    operator = get_object_or_404(BusOperator, pk=pk, user=request.user)
    checks, has_all = operator.has_required_fields()
    
    return JsonResponse({
        'completion': operator.completion_percentage,
        'checks': checks,
        'all_complete': has_all,
        'status': operator.get_approval_status_display(),
    })


from django.utils import timezone
