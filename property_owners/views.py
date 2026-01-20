from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from django.db import transaction
from .models import PropertyOwner, Property, PropertyRoomType
from .forms import PropertyOwnerRegistrationForm, PropertyRegistrationForm, PropertyRoomTypeInlineFormSet


def register_property_owner(request):
    """Register as a property owner"""
    # Check if user already has a property owner profile
    if hasattr(request.user, 'property_owner_profile'):
        messages.info(request, "You already have a property owner account.")
        return redirect('property_owners:dashboard')
    
    if request.method == 'POST':
        form = PropertyOwnerRegistrationForm(request.POST)
        if form.is_valid():
            owner = form.save(commit=False)
            owner.user = request.user
            owner.save()
            messages.success(request, "Registration successful! Your account is pending verification.")
            return redirect('property_owners:dashboard')
    else:
        form = PropertyOwnerRegistrationForm()
    
    context = {
        'form': form,
        'page_title': 'Register as Property Owner',
    }
    return render(request, 'property_owners/register.html', context)


@login_required
def property_owner_dashboard(request):
    """Dashboard for property owners - shows approval status"""
    try:
        owner = request.user.property_owner_profile
    except PropertyOwner.DoesNotExist:
        messages.warning(request, "Please register as a property owner first.")
        return redirect('property_owners:register')
    
    properties = owner.properties.all()
    
    # Categorize properties by status
    approved = properties.filter(status='APPROVED')
    pending = properties.filter(status='PENDING')
    rejected = properties.filter(status='REJECTED')
    draft = properties.filter(status='DRAFT')
    
    stats = {
        'total_properties': properties.count(),
        'approved_count': approved.count(),
        'pending_count': pending.count(),
        'rejected_count': rejected.count(),
        'draft_count': draft.count(),
        'total_bookings': sum(p.bookings.count() for p in approved),
        'verification_status': owner.get_verification_status_display(),
    }
    
    context = {
        'owner': owner,
        'approved_properties': approved,
        'pending_properties': pending,
        'rejected_properties': rejected,
        'draft_properties': draft,
        'all_properties': properties,
        'stats': stats,
    }
    return render(request, 'property_owners/dashboard.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def create_property_draft(request):
    """
    Create/edit property with PropertyRoomType inline formset (Phase-2).
    - Minimum 1 room type required before submission
    - Atomic transaction for property + rooms
    """
    try:
        owner = request.user.property_owner_profile
    except PropertyOwner.DoesNotExist:
        messages.error(request, "Please register as a property owner first.")
        return redirect('property_owners:register')
    
    # Check if editing existing draft
    property_id = request.GET.get('edit')
    property_obj = None
    
    if property_id:
        property_obj = get_object_or_404(Property, id=property_id, owner=owner, status='DRAFT')
    
    if request.method == 'POST':
        form = PropertyRegistrationForm(request.POST, instance=property_obj)
        formset = PropertyRoomTypeInlineFormSet(request.POST, request.FILES, instance=property_obj or Property())
        
        if form.is_valid() and formset.is_valid():
            # Count valid rooms in formset
            valid_rooms = sum(1 for f in formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE', False))
            
            # SUBMISSION VALIDATION - Check if user clicked "Submit for Approval"
            if 'submit_for_approval' in request.POST:
                checks, is_complete = form.instance.has_required_fields()
                
                if not is_complete or valid_rooms == 0:
                    # Incomplete - reject submission
                    missing = [k for k, v in checks.items() if not v]
                    if valid_rooms == 0:
                        missing.append('At least 1 room type required')
                    messages.error(request, f"Cannot submit. Missing: {', '.join(missing)}")
                    
                    context = {
                        'form': form,
                        'formset': formset,
                        'property': form.instance,
                        'page_title': 'Create Property',
                        'mode': 'draft',
                        'completion_percentage': form.instance.completion_percentage if property_obj else 0,
                        'required_checks': checks,
                        'valid_rooms': valid_rooms,
                    }
                    return render(request, 'property_owners/property_form.html', context)
                
                # Complete - submit for approval
                with transaction.atomic():
                    property_obj = form.save(commit=False)
                    property_obj.owner = owner
                    property_obj.status = 'PENDING'
                    property_obj.submitted_at = timezone.now()
                    property_obj.save()
                    
                    # Save room types
                    formset.instance = property_obj
                    formset.save()
                
                messages.success(request, f"✅ Property submitted with {valid_rooms} room type(s)! Admin will review soon.")
                return redirect('property_owners:property_detail', property_id=property_obj.id)
            
            else:
                # Just saving draft (no submission)
                with transaction.atomic():
                    property_obj = form.save(commit=False)
                    property_obj.owner = owner
                    property_obj.status = 'DRAFT'
                    property_obj.save()
                    
                    # Save room types
                    formset.instance = property_obj
                    formset.save()
                
                completion = property_obj.completion_percentage
                messages.success(request, f"✅ Draft saved ({completion}% complete, {valid_rooms} room(s)).")
                return redirect('property_owners:property_detail', property_id=property_obj.id)
        
        else:
            # Form validation failed
            messages.error(request, "Please fix the errors below before continuing.")
    
    else:
        # GET request - display form
        if property_obj:
            form = PropertyRegistrationForm(instance=property_obj)
            formset = PropertyRoomTypeInlineFormSet(instance=property_obj)
        else:
            form = PropertyRegistrationForm()
            formset = PropertyRoomTypeInlineFormSet(instance=Property())
    
    # Calculate completion if editing
    completion_percentage = 0
    required_checks = {}
    valid_rooms = 0
    
    if property_obj:
        completion_percentage = property_obj.completion_percentage
        required_checks, _ = property_obj.has_required_fields()
        valid_rooms = property_obj.room_types.count()
    
    context = {
        'form': form,
        'formset': formset,
        'property': property_obj,
        'page_title': 'Create/Edit Property',
        'mode': 'draft',
        'completion_percentage': completion_percentage,
        'required_checks': required_checks,
        'valid_rooms': valid_rooms,
    }
    return render(request, 'property_owners/property_form.html', context)


@login_required
def property_detail(request, property_id):
    """View property details with approval status and actions"""
    try:
        owner = request.user.property_owner_profile
    except PropertyOwner.DoesNotExist:
        messages.error(request, "Please register as a property owner first.")
        return redirect('property_owners:register')
    
    property_obj = get_object_or_404(Property, id=property_id, owner=owner)
    
    # Check if can edit (only DRAFT properties)
    can_edit = property_obj.status == 'DRAFT'
    can_resubmit = property_obj.status == 'REJECTED'
    
    # Get required fields status
    checks, is_complete = property_obj.has_required_fields()
    
    context = {
        'property': property_obj,
        'can_edit': can_edit,
        'can_resubmit': can_resubmit,
        'is_complete': is_complete,
        'required_checks': checks,
        'completion_percentage': property_obj.completion_percentage,
    }
    
    return render(request, 'property_owners/property_detail.html', context)


@login_required
def property_check_completion(request, property_id):
    """AJAX endpoint to check property completion status"""
    try:
        owner = request.user.property_owner_profile
    except PropertyOwner.DoesNotExist:
        return JsonResponse({'error': 'Not a property owner'}, status=403)
    
    property_obj = get_object_or_404(Property, id=property_id, owner=owner)
    checks, is_complete = property_obj.has_required_fields()
    
    return JsonResponse({
        'completion_percentage': property_obj.completion_percentage,
        'is_complete': is_complete,
        'checks': checks,
        'status': property_obj.status,
    })


@login_required
def admin_pending_properties(request):
    """List all pending properties for admin review"""
    if not request.user.is_staff:
        messages.error(request, "Unauthorized: Admins only")
        return redirect('users:profile')
    pending = Property.objects.filter(status='PENDING').order_by('-submitted_at')
    return render(request, 'property_owners/admin_pending.html', {'properties': pending})


@login_required
def admin_approve_property(request, property_id):
    """Approve a pending property (1-click)"""
    if not request.user.is_staff:
        messages.error(request, "Unauthorized: Admins only")
        return redirect('users:profile')
    prop = get_object_or_404(Property, id=property_id)
    try:
        prop.approve(admin_user=request.user)
        messages.success(request, f"Property #{prop.id} approved")
    except AssertionError as e:
        messages.error(request, str(e))
    return redirect('property_owners:admin-pending')


@login_required
def admin_reject_property(request, property_id):
    """Reject a pending property with mandatory reason"""
    if not request.user.is_staff:
        messages.error(request, "Unauthorized: Admins only")
        return redirect('users:profile')
    prop = get_object_or_404(Property, id=property_id)
    reason = request.POST.get('reason') or request.GET.get('reason')
    try:
        prop.reject(reason=reason or '')
        messages.success(request, f"Property #{prop.id} rejected")
    except AssertionError as e:
        messages.error(request, str(e))
    return redirect('property_owners:admin-pending')
