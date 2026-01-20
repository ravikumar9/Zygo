from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from django.db import transaction
from .models import PropertyOwner, Property
from .forms import PropertyOwnerRegistrationForm, PropertyRegistrationForm, RoomTypeInlineFormSet
from hotels.models import RoomType


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
    approved = properties.filter(approval_status='approved')
    pending = properties.filter(approval_status='pending_verification')
    rejected = properties.filter(approval_status='rejected')
    draft = properties.filter(approval_status='draft')
    
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
    Create/edit property as DRAFT with inline room type collection.
    - Allows incomplete data for save-as-you-go experience
    - MANDATORY: At least 1 room type required before approval
    - Does NOT submit for approval without complete room data
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
        property_obj = get_object_or_404(Property, id=property_id, owner=owner, approval_status='draft')
    
    if request.method == 'POST':
        form = PropertyRegistrationForm(request.POST, instance=property_obj)
        formset = RoomTypeInlineFormSet(request.POST, request.FILES, instance=property_obj or Property())
        
        if form.is_valid() and formset.is_valid():
            # SUBMISSION VALIDATION - Check if user clicked "Submit for Approval"
            if 'submit_for_approval' in request.POST:
                checks, is_complete = form.instance.has_required_fields()
                
                # Count valid rooms in formset
                valid_rooms = sum(1 for form in formset.forms if form.cleaned_data and not form.cleaned_data.get('DELETE', False))
                
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
                    property_obj.approval_status = 'pending_verification'
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
                    property_obj.approval_status = 'draft'
                    property_obj.save()
                    
                    # Save room types
                    formset.instance = property_obj
                    formset.save()
                
                valid_rooms = sum(1 for form in formset.forms if form.cleaned_data and not form.cleaned_data.get('DELETE', False))
                completion = property_obj.completion_percentage
                messages.success(request, f"✅ Draft saved ({completion}% complete, {valid_rooms} room(s)). Add rooms & click 'Submit for Approval'.")
                return redirect('property_owners:property_detail', property_id=property_obj.id)
        
        else:
            # Form validation failed
            messages.error(request, "Please fix the errors below before continuing.")
    
    else:
        # GET request - display form
        if property_obj:
            form = PropertyRegistrationForm(instance=property_obj)
            formset = RoomTypeInlineFormSet(instance=property_obj)
        else:
            # Create empty property for formset binding
            form = PropertyRegistrationForm()
            formset = RoomTypeInlineFormSet(instance=Property())
    
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
    can_edit = property_obj.approval_status == 'draft'
    can_resubmit = property_obj.approval_status == 'rejected'
    
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
        'status': property_obj.approval_status,
    })
