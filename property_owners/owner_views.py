"""
Property owner dashboard views - production-ready role-based system
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.urls import reverse_lazy

from property_owners.models import (
    PropertyOwner, PropertyUpdateRequest, SeasonalPricing, UserRole
)
from hotels.models import Hotel, RoomType


class OwnerDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Property owner dashboard - view all their hotels and pending approvals"""
    template_name = 'property_owners/dashboard.html'
    context_object_name = 'hotels'
    paginate_by = 10
    
    def test_func(self):
        """Only property owners can access"""
        return hasattr(self.request.user, 'user_role') and self.request.user.user_role.role == 'property_owner'
    
    def get_queryset(self):
        """Get hotels owned by this property owner"""
        profile = get_object_or_404(PropertyOwner, user=self.request.user)
        return profile.properties.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(PropertyOwner, user=self.request.user)
        
        context['profile'] = profile
        context['pending_requests'] = PropertyUpdateRequest.objects.filter(
            owner=profile,
            status='pending'
        ).count()
        context['approved_requests'] = PropertyUpdateRequest.objects.filter(
            owner=profile,
            status='approved'
        ).count()
        
        return context


class PropertyDetailsView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View property details and manage room types"""
    model = Hotel
    template_name = 'property_owners/property_detail.html'
    context_object_name = 'hotel'
    
    def test_func(self):
        """Verify ownership"""
        hotel = get_object_or_404(Hotel, pk=self.kwargs['pk'])
        owner_profile = get_object_or_404(PropertyOwner, user=self.request.user)
        return hotel in owner_profile.properties.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hotel = self.get_object()
        
        context['room_types'] = hotel.room_types.all()
        context['pending_updates'] = PropertyUpdateRequest.objects.filter(
            owner__user=self.request.user,
            status='pending'
        )
        
        return context


@login_required
def submit_update_request(request, hotel_id):
    """Property owner submits an update request for admin approval"""
    from django.views.decorators.http import require_http_methods
    
    @require_http_methods(["POST"])
    def _submit_update(request):
        owner_profile = get_object_or_404(PropertyOwner, user=request.user)
        hotel = get_object_or_404(Hotel, pk=hotel_id)
        
        # Verify ownership
        if hotel not in owner_profile.properties.all():
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        change_type = request.POST.get('change_type')
        title = request.POST.get('title')
        description = request.POST.get('description')
        new_data = request.POST.get('new_data', '{}')
        
        import json
        try:
            new_data = json.loads(new_data)
        except:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        
        # Create update request
        update_req = PropertyUpdateRequest.objects.create(
            owner=owner_profile,
            change_type=change_type,
            title=title,
            description=description,
            new_data=new_data
        )
        
        messages.success(request, f'Update request submitted for review. ID: {update_req.id}')
        return redirect('property_owners:property-detail', pk=hotel_id)
    
    return _submit_update(request)


@login_required
def upload_room_images(request, room_type_id):
    """Property owner uploads images for a room type"""
    from hotels.models import RoomImage
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    room_type = get_object_or_404(RoomType, pk=room_type_id)
    hotel = room_type.hotel
    
    # Verify ownership
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    if hotel not in owner_profile.properties.all():
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    # Handle file upload
    if 'images' not in request.FILES:
        return JsonResponse({'error': 'No images provided'}, status=400)
    
    uploaded_count = 0
    for image_file in request.FILES.getlist('images'):
        try:
            # Create update request for image upload (for audit trail)
            update_req = PropertyUpdateRequest.objects.create(
                owner=owner_profile,
                change_type='images',
                title=f'Image upload for {room_type.name}',
                description=f'Uploaded {image_file.name}',
                new_data={'filename': image_file.name, 'size': image_file.size}
            )
            uploaded_count += 1
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    messages.success(request, f'{uploaded_count} images submitted for review')
    return JsonResponse({'success': True, 'uploaded': uploaded_count})


@login_required
def manage_seasonal_pricing(request, room_type_id):
    """Property owner manages seasonal pricing"""
    room_type = get_object_or_404(RoomType, pk=room_type_id)
    hotel = room_type.hotel
    
    # Verify ownership
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    if hotel not in owner_profile.properties.all():
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    if request.method == 'GET':
        pricing = SeasonalPricing.objects.filter(room_type=room_type).values()
        return JsonResponse({
            'pricing': list(pricing),
            'current_base_price': float(room_type.base_price)
        })
    
    elif request.method == 'POST':
        from datetime import datetime
        from decimal import Decimal
        
        start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
        base_price = Decimal(request.POST.get('base_price', room_type.base_price))
        discount_percentage = Decimal(request.POST.get('discount_percentage', 0))
        
        pricing = SeasonalPricing.objects.create(
            room_type=room_type,
            owner=owner_profile,
            start_date=start_date,
            end_date=end_date,
            base_price=base_price,
            discount_percentage=discount_percentage
        )
        
        messages.success(request, 'Seasonal pricing saved and pending admin approval')
        return JsonResponse({'success': True, 'pricing_id': pricing.id})


@login_required
def view_update_requests(request):
    """Property owner views their submitted update requests"""
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    requests = PropertyUpdateRequest.objects.filter(owner=owner_profile).order_by('-created_at')
    
    return render(request, 'property_owners/update_requests.html', {
        'requests': requests,
        'total': requests.count(),
        'pending': requests.filter(status='pending').count(),
        'approved': requests.filter(status='approved').count(),
        'rejected': requests.filter(status='rejected').count(),
    })
