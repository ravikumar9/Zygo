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
        
        # Sprint-1: Dashboard Metrics (30-day)
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Sum, Count, Q
        from bookings.models import HotelBooking
        from decimal import Decimal
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Get all rooms for this owner's hotels
        owner_hotels = profile.properties.all()
        from hotels.models import RoomType
        owner_rooms = RoomType.objects.filter(hotel__in=[h.id for h in owner_hotels]) if owner_hotels.exists() else RoomType.objects.none()
        
        # Bookings in last 30 days
        recent_bookings = HotelBooking.objects.filter(
            room_type__in=owner_rooms,
            booking__created_at__gte=thirty_days_ago
        )
        
        # Total bookings count
        bookings_30d = recent_bookings.count()
        
        # Revenue (30d) - sum of booking totals
        revenue_30d = recent_bookings.aggregate(
            total=Sum('booking__total_amount')
        )['total'] or Decimal('0')
        
        # Occupancy % - Calculate as: booked nights / total available nights
        total_rooms = owner_rooms.count()
        if total_rooms > 0:
            # Total available room-nights in 30 days
            total_capacity = total_rooms * 30
            
            # Total booked nights
            booked_nights = recent_bookings.aggregate(
                total=Sum('total_nights')
            )['total'] or 0
            
            occupancy_pct = round((booked_nights / total_capacity) * 100, 1) if total_capacity > 0 else 0
        else:
            occupancy_pct = 0
        
        context['metrics'] = {
            'bookings_30d': bookings_30d,
            'revenue_30d': revenue_30d,
            'occupancy_pct': occupancy_pct,
        }
        
        return context

@login_required
def owner_onboarding(request):
    """Owner onboarding wizard: checklist and quick links to complete setup"""
    # Basic guard: require property_owner role
    if not (hasattr(request.user, 'user_role') and request.user.user_role.role == 'property_owner'):
        return redirect('property_owners:owner-dashboard')

    # Gather simple progress signals if available
    from property_owners.models import PropertyOwner
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    hotels = owner_profile.properties.all()
    first_hotel = hotels.first()
    rooms_count = 0
    images_ok = False
    if first_hotel:
        rooms = first_hotel.room_types.all()
        rooms_count = rooms.count()
        images_ok = any(r.images.count() >= 1 for r in rooms)

    context = {
        'owner': owner_profile,
        'first_hotel': first_hotel,
        'has_property': first_hotel is not None,
        'rooms_count': rooms_count,
        'has_any_images': images_ok,
    }
    return render(request, 'property_owners/onboarding.html', context)


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


# ===== PROPERTY REGISTRATION STEP 2: ROOM TYPES COLLECTION =====

@login_required
def hotel_room_list(request, hotel_id):
    """Property owner views all room types for a hotel"""
    from property_owners.models import PropertyOwner
    
    hotel = get_object_or_404(Hotel, pk=hotel_id)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    
    # Verify ownership via Hotel → Property relationship
    # (Hotel is linked to Property which is linked to PropertyOwner)
    if not hasattr(hotel, 'property') or hotel.property.owner != owner_profile:
        return redirect('property_owners:owner-dashboard')
    
    rooms = hotel.room_types.all().order_by('name')
    draft_count = rooms.filter(status='DRAFT').count()
    ready_count = rooms.filter(status='READY').count()
    
    return render(request, 'property_owners/hotel_rooms_list.html', {
        'hotel': hotel,
        'rooms': rooms,
        'draft_count': draft_count,
        'ready_count': ready_count,
        'can_add_room': True,  # Always allow adding rooms during registration
    })


@login_required
def room_type_create(request, hotel_id):
    """Property owner creates a new room type"""
    from property_owners.models import PropertyOwner
    from property_owners.forms import RoomTypeForm
    
    hotel = get_object_or_404(Hotel, pk=hotel_id)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    
    # Verify ownership
    if not hasattr(hotel, 'property') or hotel.property.owner != owner_profile:
        return redirect('property_owners:owner-dashboard')
    
    if request.method == 'POST':
        form = RoomTypeForm(request.POST, hotel=hotel)
        if form.is_valid():
            room = form.save()
            messages.success(request, f'Room type "{room.name}" created. Add images to complete.')
            return redirect('property_owners:room-edit', hotel_id=hotel_id, room_id=room.id)
    else:
        form = RoomTypeForm(hotel=hotel)
    
    return render(request, 'property_owners/room_type_form.html', {
        'form': form,
        'hotel': hotel,
        'title': 'Add Room Type',
        'action': 'create',
    })


@login_required
def room_type_edit(request, hotel_id, room_id):
    """Property owner edits a room type (only if DRAFT status)"""
    from property_owners.models import PropertyOwner
    from property_owners.forms import RoomTypeForm
    
    hotel = get_object_or_404(Hotel, pk=hotel_id)
    room = get_object_or_404(RoomType, pk=room_id, hotel=hotel)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    
    # Verify ownership
    if not hasattr(hotel, 'property') or hotel.property.owner != owner_profile:
        return redirect('property_owners:owner-dashboard')
    
    # Can only edit DRAFT rooms
    if room.status != 'DRAFT':
        messages.warning(request, 'Only DRAFT room types can be edited')
        return redirect('property_owners:room-list', hotel_id=hotel_id)
    
    if request.method == 'POST':
        form = RoomTypeForm(request.POST, instance=room, hotel=hotel)
        if form.is_valid():
            room = form.save()
            messages.success(request, f'Room type "{room.name}" updated')
            return redirect('property_owners:room-images', hotel_id=hotel_id, room_id=room.id)
    else:
        form = RoomTypeForm(instance=room, hotel=hotel)
    
    images = room.images.all()
    meals = room.meal_plans.filter(is_active=True)
    
    return render(request, 'property_owners/room_type_form.html', {
        'form': form,
        'hotel': hotel,
        'room': room,
        'images': images,
        'meals': meals,
        'title': 'Edit Room Type',
        'action': 'edit',
    })


@login_required
def room_images_manage(request, hotel_id, room_id):
    """Property owner uploads/manages images for a room type"""
    from property_owners.models import PropertyOwner
    from hotels.models import RoomImage
    
    hotel = get_object_or_404(Hotel, pk=hotel_id)
    room = get_object_or_404(RoomType, pk=room_id, hotel=hotel)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    
    # Verify ownership
    if not hasattr(hotel, 'property') or hotel.property.owner != owner_profile:
        return redirect('property_owners:owner-dashboard')
    
    # Can only edit DRAFT rooms
    if room.status != 'DRAFT':
        messages.warning(request, 'Only DRAFT room types can have images modified')
        return redirect('property_owners:room-list', hotel_id=hotel_id)
    
    if request.method == 'POST':
        # Handle image upload
        if 'images' in request.FILES:
            uploaded = 0
            for img_file in request.FILES.getlist('images'):
                RoomImage.objects.create(
                    room_type=room,
                    image=img_file,
                    display_order=room.images.count() + uploaded
                )
                uploaded += 1
            messages.success(request, f'{uploaded} image(s) uploaded')
        
        # Mark room as READY if all fields complete
        if room.set_ready():
            messages.success(request, 'Room marked as READY for approval')
            return redirect('property_owners:room-list', hotel_id=hotel_id)
        else:
            messages.warning(request, 'Room incomplete - must have images, price>0, capacity>0')
    
    images = room.images.all()
    
    return render(request, 'property_owners/room_images_manage.html', {
        'hotel': hotel,
        'room': room,
        'images': images,
        'can_upload': room.status == 'DRAFT',
    })


@login_required
def room_image_delete(request, hotel_id, room_id, image_id):
    """Property owner deletes a room image"""
    from property_owners.models import PropertyOwner
    from hotels.models import RoomImage
    
    hotel = get_object_or_404(Hotel, pk=hotel_id)
    room = get_object_or_404(RoomType, pk=room_id, hotel=hotel)
    image = get_object_or_404(RoomImage, pk=image_id, room_type=room)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    
    # Verify ownership
    if not hasattr(hotel, 'property') or hotel.property.owner != owner_profile:
        return redirect('property_owners:owner-dashboard')
    
    if image.delete():
        messages.success(request, 'Image deleted')
    
    return redirect('property_owners:room-images', hotel_id=hotel_id, room_id=room_id)


@login_required
def room_type_delete(request, hotel_id, room_id):
    """Property owner deletes a room type (only if DRAFT)"""
    from property_owners.models import PropertyOwner
    
    hotel = get_object_or_404(Hotel, pk=hotel_id)
    room = get_object_or_404(RoomType, pk=room_id, hotel=hotel)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    
    # Verify ownership
    if not hasattr(hotel, 'property') or hotel.property.owner != owner_profile:
        return redirect('property_owners:owner-dashboard')
    
    # Can only delete DRAFT rooms
    if room.status != 'DRAFT':
        messages.warning(request, 'Only DRAFT room types can be deleted')
        return redirect('property_owners:room-list', hotel_id=hotel_id)
    
    if request.method == 'POST':
        room_name = room.name
        room.delete()
        messages.success(request, f'Room type "{room_name}" deleted')
    
    return redirect('property_owners:room-list', hotel_id=hotel_id)


# Sprint-1: Room Availability Calendar Views
@login_required
def room_calendar(request, room_id):
    """View room availability calendar with blocks"""
    from hotels.models import RoomBlock
    from property_owners.models import PropertyOwner
    from datetime import date, timedelta
    import calendar
    
    room = get_object_or_404(RoomType, pk=room_id)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    
    # Verify ownership through property
    if not hasattr(room.hotel, 'property') or room.hotel.property.owner != owner_profile:
        messages.error(request, 'Not authorized')
        return redirect('property_owners:owner-dashboard')
    
    # Get current month or requested month
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))
    
    # Get blocks for this room in the current month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    
    blocks = RoomBlock.objects.filter(
        room_type=room,
        is_active=True,
        blocked_from__lte=last_day,
        blocked_to__gte=first_day
    ).order_by('blocked_from')
    
    # Generate calendar data
    cal = calendar.Calendar(firstweekday=6)  # Start with Sunday
    month_days = cal.monthdatescalendar(year, month)
    
    # Mark blocked dates
    blocked_dates = set()
    for block in blocks:
        current = max(block.blocked_from, first_day)
        end = min(block.blocked_to, last_day)
        while current <= end:
            blocked_dates.add(current)
            current += timedelta(days=1)
    
    # Get bookings for this room to prevent blocking
    from bookings.models import HotelBooking
    upcoming_bookings = HotelBooking.objects.filter(
        room_type=room,
        check_in_date__lte=last_day,
        check_out_date__gte=first_day,
        status__in=['RESERVED', 'CONFIRMED', 'CHECKED_IN']
    ).values_list('check_in_date', 'check_out_date')
    
    booked_dates = set()
    for check_in, check_out in upcoming_bookings:
        current = max(check_in, first_day)
        end = min(check_out, last_day)
        while current < end:  # Check-out day is not included
            booked_dates.add(current)
            current += timedelta(days=1)
    
    return render(request, 'property_owners/room_calendar.html', {
        'room': room,
        'hotel': room.hotel,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'month_days': month_days,
        'blocked_dates': blocked_dates,
        'booked_dates': booked_dates,
        'blocks': blocks,
        'prev_month': (date(year, month, 1) - timedelta(days=1)),
        'next_month': (last_day + timedelta(days=1)),
    })


@login_required
def block_dates(request, room_id):
    """Block single date or range"""
    from hotels.models import RoomBlock
    from property_owners.models import PropertyOwner
    from datetime import datetime
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    room = get_object_or_404(RoomType, pk=room_id)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    
    # Verify ownership
    if not hasattr(room.hotel, 'property') or room.hotel.property.owner != owner_profile:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        blocked_from = datetime.strptime(request.POST.get('blocked_from'), '%Y-%m-%d').date()
        blocked_to = datetime.strptime(request.POST.get('blocked_to'), '%Y-%m-%d').date()
        reason = request.POST.get('reason', '').strip()
        
        # Create block with validation
        block = RoomBlock(
            room_type=room,
            blocked_from=blocked_from,
            blocked_to=blocked_to,
            reason=reason,
            created_by=request.user
        )
        block.full_clean()  # Runs validation
        block.save()
        
        messages.success(request, f'Blocked {blocked_from} to {blocked_to}')
        return JsonResponse({'success': True, 'message': 'Dates blocked successfully'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def unblock_dates(request, block_id):
    """Remove a date block"""
    from hotels.models import RoomBlock
    from property_owners.models import PropertyOwner
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    block = get_object_or_404(RoomBlock, pk=block_id)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    
    # Verify ownership
    if not hasattr(block.room_type.hotel, 'property') or block.room_type.hotel.property.owner != owner_profile:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        block.delete()
        messages.success(request, 'Block removed')
        return JsonResponse({'success': True, 'message': 'Block removed successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def bulk_block_dates(request, room_id):
    """Bulk block multiple date ranges"""
    from hotels.models import RoomBlock
    from property_owners.models import PropertyOwner
    from datetime import datetime
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    room = get_object_or_404(RoomType, pk=room_id)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    
    # Verify ownership
    if not hasattr(room.hotel, 'property') or room.hotel.property.owner != owner_profile:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        ranges = json.loads(request.POST.get('ranges', '[]'))
        reason = request.POST.get('reason', '').strip()
        
        created_count = 0
        errors = []
        
        for range_data in ranges:
            try:
                blocked_from = datetime.strptime(range_data['from'], '%Y-%m-%d').date()
                blocked_to = datetime.strptime(range_data['to'], '%Y-%m-%d').date()
                
                block = RoomBlock(
                    room_type=room,
                    blocked_from=blocked_from,
                    blocked_to=blocked_to,
                    reason=reason,
                    created_by=request.user
                )
                block.full_clean()
                block.save()
                created_count += 1
            except Exception as e:
                errors.append(f"{range_data.get('from')} to {range_data.get('to')}: {str(e)}")
        
        if errors:
            return JsonResponse({
                'success': False,
                'created': created_count,
                'errors': errors
            }, status=400)
        
        messages.success(request, f'Blocked {created_count} date ranges')
        return JsonResponse({
            'success': True,
            'created': created_count,
            'message': f'{created_count} ranges blocked successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# Sprint-1: Payout Request Views
@login_required
def request_payout(request):
    """Owner requests payout from wallet"""
    from property_owners.models import PropertyOwner
    from payments.models import Wallet, PayoutRequest
    from django.core.exceptions import ValidationError
    from decimal import Decimal
    
    try:
        owner_profile = PropertyOwner.objects.get(user=request.user)
    except PropertyOwner.DoesNotExist:
        messages.error(request, "Property owner profile not found")
        return redirect('property_owners:owner-dashboard')
    
    # Get or create wallet
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            
            # Create payout request with bank details from owner profile
            payout = PayoutRequest(
                owner=owner_profile,
                wallet=wallet,
                amount=amount,
                bank_account_name=owner_profile.bank_account_name or "",
                bank_account_number=owner_profile.bank_account_number or "",
                bank_ifsc=owner_profile.bank_ifsc or ""
            )
            
            # Request payout (validates and deducts from wallet)
            payout.request_payout()
            
            messages.success(request, f"Payout request for ₹{amount} submitted successfully")
            return redirect('property_owners:payout-history')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Failed to create payout request: {str(e)}")
    
    # Show payout request form
    pending_requests = PayoutRequest.objects.filter(
        owner=owner_profile,
        status='requested'
    )
    
    return render(request, 'property_owners/payout_request.html', {
        'owner': owner_profile,
        'wallet': wallet,
        'pending_requests': pending_requests,
        'min_payout': Decimal('100'),
    })


@login_required
def payout_history(request):
    """View payout history"""
    from property_owners.models import PropertyOwner
    from payments.models import PayoutRequest
    
    try:
        owner_profile = PropertyOwner.objects.get(user=request.user)
    except PropertyOwner.DoesNotExist:
        messages.error(request, "Property owner profile not found")
        return redirect('property_owners:owner-dashboard')
    
    payouts = PayoutRequest.objects.filter(owner=owner_profile).order_by('-created_at')
    
    return render(request, 'property_owners/payout_history.html', {
        'owner': owner_profile,
        'payouts': payouts,
    })
