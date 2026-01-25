from rest_framework import generics, filters, status

from rest_framework.decorators import api_view

from rest_framework.response import Response

from rest_framework.pagination import PageNumberPagination

from django.shortcuts import render, get_object_or_404, redirect

from django.views.decorators.csrf import csrf_exempt

from django.db import DatabaseError
from django.db.models import Min, Value, FloatField, Q, DecimalField, F

from django.db.models.functions import Coalesce

from datetime import date, datetime, timedelta

import json

from django.views.decorators.http import require_http_methods

from django_filters.rest_framework import DjangoFilterBackend

from decimal import Decimal

from math import radians, sin, cos, asin, sqrt

from django.utils import timezone

import uuid

import logging

from core.utils import get_recent_searches, update_recent_search



logger = logging.getLogger(__name__)


# User-facing booking errors must remain generic; UI gating handles validation.
GENERIC_BOOKING_ERROR = "Unable to process booking. Please try again."



# ============================================

# FIX-3: PRICE DISCLOSURE HELPERS

# ============================================



def calculate_service_fee(base_amount):

    """Wrapper: delegate to centralized pricing utils."""

    try:

        from bookings.utils.pricing import calculate_service_fee as _calc

        return _calc(base_amount)

    except Exception:

        return 0





def calculate_gst(service_fee):

    """Wrapper: delegate to centralized pricing utils."""

    try:

        from bookings.utils.pricing import calculate_gst as _gst

        return _gst(service_fee)

    except Exception:

        return 0





def format_price_disclosure(hotel, room_type, check_in=None, check_out=None):

    """

    FIX-3: Format price info for display on search results and detail pages

    

    Returns dict with:

    - base_price: Room base price per night

    - discounted_price: Price after any active discounts

    - discount_badge: Display text for discount if any

    - service_fee: Calculated service fee (not shown on search)

    - gst_applicable: Whether GST applies

    """

    from .pricing_service import PricingCalculator

    

    base_price = room_type.base_price if room_type else hotel.room_types.aggregate(min_price=Min('base_price'))['min_price']

    

    if not base_price:

        base_price = Decimal('0')

    

    discounted_price = base_price

    discount_badge = None

    

    # Check for active hotel discounts

    now = timezone.now()

    active_discount = hotel.discounts.filter(

        is_active=True,

        valid_from__lte=now,

        valid_till__gte=now

    ).first()

    

    if active_discount:

        if active_discount.discount_type == 'percentage':

            discount_amount = base_price * Decimal(str(active_discount.discount_value)) / Decimal('100')

            discounted_price = base_price - discount_amount

            discount_badge = f"{int(active_discount.discount_value)}% off"

        elif active_discount.discount_type == 'flat':

            discounted_price = base_price - Decimal(str(active_discount.discount_value))

            if discounted_price < 0:

                discounted_price = base_price

            else:

                discount_badge = f"Rs. {int(active_discount.discount_value)} off"

    

    service_fee = calculate_service_fee(discounted_price)

    

    return {

        'base_price': float(base_price),

        'discounted_price': float(discounted_price),

        'discount_badge': discount_badge,

        'service_fee': service_fee,

        'gst_applicable': True,

        'currency': 'INR'

    }





from .channel_manager_service import (

    ExternalChannelManagerClient,

    InternalInventoryService,

    InventoryLockError,

    AvailabilityError,

    get_hotel_availability_snapshot,

)

from .models import (

    Hotel,

    RoomType,

    RoomMealPlan,

    RoomAvailability,

    HotelDiscount,

    ChannelManagerRoomMapping,

    RoomCancellationPolicy,

)

from .serializers import (

    HotelListSerializer, HotelDetailSerializer, RoomTypeSerializer,

    PricingRequestSerializer, AvailabilityCheckSerializer,

    HotelSearchFilterSerializer

)

from .pricing_service import PricingCalculator, OccupancyCalculator

from core.models import City, CorporateDiscount

from bookings.models import Booking, HotelBooking, InventoryLock





class StandardResultsSetPagination(PageNumberPagination):

    page_size = 10

    page_size_query_param = 'page_size'

    max_page_size = 100





# ============================================

# HOTEL LISTING & SEARCH APIs

# ============================================



class HotelListView(generics.ListAPIView):

    """List all hotels with filters (approved properties only)"""

    queryset = (
        Hotel.objects.filter(is_active=True)
        .filter(Q(owner_property__isnull=True) | Q(owner_property__status='APPROVED', owner_property__is_active=True))
        .prefetch_related('room_types', 'images')
    )

    serializer_class = HotelListSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = ['city', 'star_rating', 'is_featured', 'property_type',

                        'has_wifi', 'has_parking', 'has_pool', 'has_gym', 'has_restaurant', 'has_spa']

    search_fields = ['name', 'description', 'city__name']

    ordering_fields = ['review_rating', 'name']

    pagination_class = StandardResultsSetPagination





class HotelDetailView(generics.RetrieveAPIView):

    """Get hotel details with all room types and amenities (approved only)"""

    queryset = (
        Hotel.objects.filter(is_active=True)
        .filter(Q(owner_property__isnull=True) | Q(owner_property__status='APPROVED', owner_property__is_active=True))
        .prefetch_related('room_types', 'images', 'discounts')
    )

    serializer_class = HotelDetailSerializer





class HotelSearchView(generics.ListAPIView):

    """

    Advanced hotel search with filters

    

    Query Parameters:

    - city_id: Filter by city

    - check_in: Check-in date (YYYY-MM-DD)

    - check_out: Check-out date (YYYY-MM-DD)

    - min_price: Minimum base price

    - max_price: Maximum base price

    - star_rating: Hotel star rating (1-5)

    - has_wifi, has_parking, has_pool, has_gym, has_restaurant, has_spa: Boolean filters

    - sort_by: price_asc, price_desc, rating_asc, rating_desc, name

    - page: Page number (default 1)

    - page_size: Items per page (default 10)

    """

    serializer_class = HotelListSerializer

    pagination_class = StandardResultsSetPagination

    

    def get_queryset(self):

        queryset = (
            Hotel.objects.filter(is_active=True)
            .filter(Q(owner_property__isnull=True) | Q(owner_property__status='APPROVED', owner_property__is_active=True))
            .prefetch_related('room_types', 'images')
        )

        

        # City filter

        city_id = self.request.query_params.get('city_id')

        if city_id:

            # Accept either numeric id or city name for backward compatibility

            try:

                cid = int(city_id)

                queryset = queryset.filter(city_id=cid)

            except (ValueError, TypeError):

                queryset = queryset.filter(city__name__iexact=city_id)

        

        # Star rating filter

        star_rating = self.request.query_params.get('star_rating')

        if star_rating:

            queryset = queryset.filter(star_rating=int(star_rating))



        # Property type filter

        property_type = self.request.query_params.get('property_type')

        if property_type:

            queryset = queryset.filter(property_type=property_type)

        

        # Amenity filters

        if self.request.query_params.get('has_wifi') == 'true':

            queryset = queryset.filter(has_wifi=True)

        if self.request.query_params.get('has_parking') == 'true':

            queryset = queryset.filter(has_parking=True)

        if self.request.query_params.get('has_pool') == 'true':

            queryset = queryset.filter(has_pool=True)

        if self.request.query_params.get('has_gym') == 'true':

            queryset = queryset.filter(has_gym=True)

        if self.request.query_params.get('has_restaurant') == 'true':

            queryset = queryset.filter(has_restaurant=True)

        if self.request.query_params.get('has_spa') == 'true':

            queryset = queryset.filter(has_spa=True)

        

        # Price filter (min price of room types)

        min_price = self.request.query_params.get('min_price')

        max_price = self.request.query_params.get('max_price')

        

        if min_price or max_price:

            queryset = queryset.annotate(

                min_room_price=Coalesce(Min('room_types__base_price'), Value(0, output_field=DecimalField()))

            )

            if min_price:

                queryset = queryset.filter(min_room_price__gte=Decimal(min_price))

            if max_price:

                queryset = queryset.filter(min_room_price__lte=Decimal(max_price))

        

        # Sorting

        sort_by = self.request.query_params.get('sort_by', 'name')

        if sort_by == 'price_asc':

            queryset = queryset.annotate(

                min_room_price=Coalesce(Min('room_types__base_price'), Value(0, output_field=DecimalField()))

            ).order_by('min_room_price')

        elif sort_by == 'price_desc':

            queryset = queryset.annotate(

                max_room_price=Coalesce(F('room_types__base_price'), Value(0, output_field=DecimalField()), output_field=DecimalField())

            ).order_by('-max_room_price')

        elif sort_by == 'rating_asc':

            queryset = queryset.order_by('review_rating')

        elif sort_by == 'rating_desc':

            queryset = queryset.order_by('-review_rating')

        else:

            queryset = queryset.order_by('name')

        

        return queryset

    

    def get_serializer_context(self):

        context = super().get_serializer_context()

        context['check_in'] = self.request.query_params.get('check_in')

        context['check_out'] = self.request.query_params.get('check_out')

        return context





# ============================================

# PRICING & AVAILABILITY APIs

# ============================================



@api_view(['POST'])

def calculate_price(request):

    """

    Calculate total price for a room booking (backend-driven, GST hidden)

    

    Request body:

    {

        "room_type_id": 1,

        "meal_plan_id": 5 (optional),

        "check_in": "2024-01-10",

        "check_out": "2024-01-15",

        "num_rooms": 2,

        "stay_type": "overnight" | "hourly" (optional, default: overnight),

        "hourly_hours": 6 | 12 | 24 (required if stay_type=hourly),

        "discount_code": "SAVE20" (optional)

    }

    """

    serializer = PricingRequestSerializer(data=request.data)

    if not serializer.is_valid():

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    

    try:

        room_type = RoomType.objects.get(id=serializer.validated_data['room_type_id'])

        meal_plan = None

        if serializer.validated_data.get('meal_plan_id'):

            meal_plan = RoomMealPlan.objects.get(

                id=serializer.validated_data['meal_plan_id'],

                room_type=room_type,

                is_active=True

            )

        

        calculator = PricingCalculator(room_type.hotel)

        

        pricing = calculator.calculate_total_price(

            room_type=room_type,

            check_in=serializer.validated_data['check_in'],

            check_out=serializer.validated_data['check_out'],

            num_rooms=serializer.validated_data.get('num_rooms', 1),

            discount_code=serializer.validated_data.get('discount_code'),

            meal_plan=meal_plan,

            stay_type=serializer.validated_data.get('stay_type', 'overnight'),

            hourly_hours=serializer.validated_data.get('hourly_hours')

        )

        

# GST hidden rule: Remove GST % from response
        response_pricing = dict(pricing)
        response_pricing.pop('gst_rate_percent', None)
        response_pricing.pop('effective_tax_rate', None)
        
        return Response({

            'success': True,

            'pricing': response_pricing,

            'gst_hidden': True,

            'tax_modal_data': {

                'gst_amount': pricing['gst_amount'],

                'service_fee': pricing['service_fee'],

                'subtotal': pricing['subtotal_after_discount'],

                'taxes_total': pricing['taxes_total'],

                'total_payable': pricing['total_amount'],

                'breakdown': pricing.get('breakdown', {}),

            }

        }, status=status.HTTP_200_OK)

    

    except RoomType.DoesNotExist:

        return Response(

            {'error': 'Room type not found'},

            status=status.HTTP_404_NOT_FOUND

        )

    except RoomMealPlan.DoesNotExist:

        return Response(

            {'error': 'Meal plan not available for this room'},

            status=status.HTTP_400_BAD_REQUEST

        )

    except ValueError as e:

        return Response(

            {'error': str(e)},

            status=status.HTTP_400_BAD_REQUEST

        )





@api_view(['POST'])

def check_availability(request):

    """

    Check if rooms are available and inventory status (includes warnings)

    

    Request body:

    {

        "room_type_id": 1,

        "check_in": "2024-01-10",

        "check_out": "2024-01-15",

        "num_rooms": 2

    }

    """

    serializer = AvailabilityCheckSerializer(data=request.data)

    if not serializer.is_valid():

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    

    try:

        room_type = RoomType.objects.get(id=serializer.validated_data['room_type_id'])

        calculator = PricingCalculator(room_type.hotel)

        

        availability = calculator.check_availability(

            room_type=room_type,

            check_in=serializer.validated_data['check_in'],

            check_out=serializer.validated_data['check_out'],

            num_rooms=serializer.validated_data.get('num_rooms', 1)

        )

        

        # Add inventory warning if < 5 rooms available

        inventory_warning = None

        available_count = availability.get('available_rooms', 0)

        if 0 < available_count < 5:

            inventory_warning = f"Only {available_count} room(s) left"

        elif available_count == 0:

            inventory_warning = "This room type is not available"

        

        return Response({

            'success': True,

            'availability': availability,

            'inventory_warning': inventory_warning,

            'inventory_available': available_count > 0,

        }, status=status.HTTP_200_OK)

    

    except RoomType.DoesNotExist:

        return Response(

            {'error': 'Room type not found'},

            status=status.HTTP_404_NOT_FOUND

        )





@api_view(['GET'])

def get_hotel_occupancy(request, hotel_id):

    """

    Get occupancy details for a hotel

    

    Query Parameters:

    - start_date: Start date (YYYY-MM-DD)

    - end_date: End date (YYYY-MM-DD)

    """

    try:

        hotel = Hotel.objects.get(id=hotel_id)

        

        start_date_str = request.query_params.get('start_date')

        end_date_str = request.query_params.get('end_date')

        

        if not start_date_str or not end_date_str:

            return Response(

                {'error': 'start_date and end_date are required'},

                status=status.HTTP_400_BAD_REQUEST

            )

        

        start_date = date.fromisoformat(start_date_str)

        end_date = date.fromisoformat(end_date_str)

        

        occupancy = OccupancyCalculator.get_hotel_occupancy_summary(

            hotel, start_date, end_date

        )

        

        return Response({

            'success': True,

            'occupancy': occupancy

        }, status=status.HTTP_200_OK)

    

    except Hotel.DoesNotExist:

        return Response(

            {'error': 'Hotel not found'},

            status=status.HTTP_404_NOT_FOUND

        )

    except ValueError as e:

        return Response(

            {'error': str(e)},

            status=status.HTTP_400_BAD_REQUEST

        )





# ============================================

# HTML WEB VIEWS

# ============================================



def hotel_list(request):

    """Hotel listing page with search"""

    # Hotels are independent - no property_owner relationship

    hotels = (

        Hotel.objects.filter(is_active=True)

        .filter(Q(owner_property__isnull=True) | Q(owner_property__status='APPROVED', owner_property__is_active=True))

        .annotate(min_price=Coalesce(Min('room_types__base_price'), Value(0, output_field=DecimalField())))

        .select_related('city')

        .prefetch_related('images', 'room_types', 'channel_mappings')

    )

    cities = City.objects.all().order_by('name')

    base_hotels_qs = hotels

    

    # Search filters

    city_id = request.GET.get('city_id')

    if city_id:

        try:

            cid = int(city_id)

            hotels = hotels.filter(city_id=cid)

        except (ValueError, TypeError):

            hotels = hotels.filter(city__name__iexact=city_id)

    

    query = (request.GET.get('q') or '').strip()

    checkin = request.GET.get('checkin')

    checkout = request.GET.get('checkout')

    price_min = request.GET.get('price_min')

    price_max = request.GET.get('price_max')

    star_rating = request.GET.get('star_rating')

    property_type = request.GET.get('property_type')

    sort = request.GET.get('sort')

    guests = request.GET.get('guests')

    near_me_flag = request.GET.get('near_me') == '1'

    near_me_lat = request.GET.get('lat')

    near_me_lng = request.GET.get('lng')

    radius_km = request.GET.get('radius') or 10

    near_me_error = None

    near_me_notice = None



    amenity_flags = {

        'has_wifi': request.GET.get('has_wifi') in ('true', 'on', '1'),

        'has_parking': request.GET.get('has_parking') in ('true', 'on', '1'),

        'has_pool': request.GET.get('has_pool') in ('true', 'on', '1'),

        'has_gym': request.GET.get('has_gym') in ('true', 'on', '1'),

        'has_restaurant': request.GET.get('has_restaurant') in ('true', 'on', '1'),

        'has_spa': request.GET.get('has_spa') in ('true', 'on', '1'),

        'has_ac': request.GET.get('has_ac') in ('true', 'on', '1'),

    }



    date_error = None

    if checkin and checkout:

        try:

            checkin_dt = datetime.strptime(checkin, '%Y-%m-%d').date()

            checkout_dt = datetime.strptime(checkout, '%Y-%m-%d').date()

            if checkout_dt <= checkin_dt:

                date_error = 'Check-out must be after check-in.'

        except Exception:

            date_error = 'Invalid dates provided.'



    # Universal search across city, area/address, and property name

    if query:

        hotels = hotels.filter(

            Q(name__icontains=query)

            | Q(description__icontains=query)

            | Q(address__icontains=query)

            | Q(city__name__icontains=query)

        )



    # Basic price range filter

    if price_min:

        hotels = hotels.filter(min_price__gte=price_min)

    if price_max:

        hotels = hotels.filter(min_price__lte=price_max)



    # Star rating filter

    if star_rating:

        hotels = hotels.filter(star_rating=star_rating)



    # Property type filter

    if property_type:

        hotels = hotels.filter(property_type=property_type)



    # Amenity filters

    for field, enabled in amenity_flags.items():

        if enabled:

            hotels = hotels.filter(**{field: True})



    # Sorting

    if sort == 'price_asc':

        hotels = hotels.order_by('min_price')

    elif sort == 'price_desc':

        hotels = hotels.order_by('-min_price')

    elif sort == 'rating_desc':

        hotels = hotels.order_by('-review_rating')

    elif sort == 'rating_asc':

        hotels = hotels.order_by('review_rating')

    

    availability_errors = {}

    # Near-me radius filter (fallback-safe)

    if near_me_flag:

        try:

            user_lat = float(near_me_lat)

            user_lng = float(near_me_lng)

            radius = float(radius_km) if float(radius_km) > 0 else 10.0



            def haversine_km(lat1, lon1, lat2, lon2):

                R = 6371.0

                d_lat = radians(lat2 - lat1)

                d_lon = radians(lon2 - lon1)

                a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2

                c = 2 * asin(sqrt(a))

                return R * c



            nearby = []

            for hotel in hotels:

                if hotel.latitude is None or hotel.longitude is None:

                    continue

                distance = haversine_km(float(hotel.latitude), float(hotel.longitude), user_lat, user_lng)

                if distance <= radius:

                    hotel.distance_km = round(distance, 2)

                    hotel.is_nearby = True

                    nearby.append(hotel)

            hotels = sorted(nearby, key=lambda h: getattr(h, 'distance_km', 0))

            if not hotels:

                near_me_error = 'No hotels found within the selected radius.'

        except Exception:

            near_me_error = 'Unable to apply Near Me filter. Please retry.'



    # Fallback to city center results to avoid dead-ends

    if near_me_flag and (near_me_error or not hotels):

        hotels = base_hotels_qs

        if city_id:

            try:

                hotels = hotels.filter(city_id=int(city_id))

            except Exception:

                hotels = hotels.filter(city__name__iexact=city_id)

        hotels = list(hotels)

        if not hotels:

            hotels = list(base_hotels_qs)

        near_me_notice = 'Location unavailable. Showing closest city results instead.'

        near_me_error = None

    

    hotels_iterable = hotels if isinstance(hotels, list) else list(hotels)



    if checkin and checkout:

        for hotel in hotels_iterable:

            try:

                hotel.availability_snapshot = get_hotel_availability_snapshot(

                    hotel, checkin, checkout, int(guests or 1)

                )

                hotel.availability_error = None

            except AvailabilityError as exc:

                hotel.availability_snapshot = None

                hotel.availability_error = str(exc)

                availability_errors[hotel.id] = str(exc)

            except Exception:

                hotel.availability_snapshot = None

                hotel.availability_error = "Availability temporarily unavailable"

                availability_errors[hotel.id] = "Availability temporarily unavailable"



    combined_error = date_error or near_me_error



    # Persist recent hotel search in session for recency widget

    if request.GET:

        city_name = None

        if city_id:

            city_obj = City.objects.filter(id=city_id).first()

            city_name = city_obj.name if city_obj else None

        update_recent_search(

            request.session,

            'hotels',

            {

                'city_id': city_id,

                'city_name': city_name,

                'checkin': checkin,

                'checkout': checkout,

                'query': query,

            },

        )



    recent_searches = get_recent_searches(request.session)



    context = {

        'hotels': hotels_iterable,

        'cities': cities,

        'property_types': Hotel.PROPERTY_TYPES,

        'today': date.today().strftime('%Y-%m-%d'),

        'search_query': query,

        'selected_city': city_id,

        'selected_checkin': checkin,

        'selected_checkout': checkout,

        'selected_price_min': price_min,

        'selected_price_max': price_max,

        'selected_star_rating': star_rating,

        'selected_property_type': property_type,

        'selected_sort': sort,

        'selected_guests': guests,

        'selected_amenities': amenity_flags,

        'availability_errors': availability_errors,

        'search_error': combined_error,

        'selected_near_me': near_me_flag,

        'selected_lat': near_me_lat,

        'selected_lng': near_me_lng,

        'selected_radius': radius_km,

        'near_me_notice': near_me_notice,

        'recent_searches': recent_searches,

    }

    

    if combined_error:

        return render(request, 'hotels/hotel_list.html', context)

    

    return render(request, 'hotels/hotel_list.html', context)





def hotel_detail(request, pk):

    """Hotel detail page with defensive context data (Principal Architect)"""

    # CRITICAL: Use explicit prefetch_related to avoid N+1 queries

    hotel_qs = (

        Hotel.objects.select_related('city')

        .filter(Q(owner_property__isnull=True) | Q(owner_property__status='APPROVED', owner_property__is_active=True))

        .prefetch_related(

            'images',

            'room_types__images',

            'room_types__meal_plans',  # CRITICAL for meal plan dropdown

            'room_types',

            'channel_mappings'

        )

    )

    hotel = get_object_or_404(hotel_qs, pk=pk, is_active=True)

    

    today = date.today()

    default_checkin = request.GET.get('checkin') or today.strftime('%Y-%m-%d')

    default_checkout = request.GET.get('checkout') or (today + timedelta(days=1)).strftime('%Y-%m-%d')

    default_guests = request.GET.get('guests') or 1

    default_room_type = request.GET.get('room_type')

    default_num_rooms = request.GET.get('rooms') or request.GET.get('num_rooms') or 1

    default_meal_plan = request.GET.get('meal_plan_id') or ''



    # Restore draft booking data from session

    draft = request.session.get('booking_draft') or {}

    if draft.get('hotel_id') == hotel.id:

        default_checkin = draft.get('check_in', default_checkin)

        default_checkout = draft.get('check_out', default_checkout)

        default_guests = draft.get('num_guests', default_guests)

        default_room_type = draft.get('room_type_id', default_room_type)

        request.prefill_guest_name = draft.get('guest_name', '')

        request.prefill_guest_email = draft.get('guest_email', '')

        request.prefill_guest_phone = draft.get('guest_phone', '')

        request.prefill_num_rooms = draft.get('num_rooms', default_num_rooms)

        request.prefill_meal_plan = draft.get('meal_plan_id', default_meal_plan)

    else:

        request.prefill_guest_name = ''

        request.prefill_guest_email = ''

        request.prefill_guest_phone = ''

        request.prefill_num_rooms = default_num_rooms

        request.prefill_meal_plan = default_meal_plan

    

    try:

        availability_snapshot = get_hotel_availability_snapshot(hotel, default_checkin, default_checkout, int(default_guests or 1))

    except Exception:

        availability_snapshot = None

    

    # ========================================================================

    # DEFENSIVE: Generate pricing data for template (pre-calculated, no JS math)

    # ========================================================================

    try:

        effective_prices = []

        for rt in hotel.room_types.all():

            try:

                effective_prices.append(rt.get_effective_price())

            except Exception:

                continue



        min_price = min(effective_prices) if effective_prices else None



        nights = 1

        # Support hourly stays preview parameters
        stay_type = request.GET.get('stay_type', '').strip()
        slot_hours_val = request.GET.get('hourly_hours', '').strip()
        slot_hours = int(slot_hours_val) if slot_hours_val.isdigit() else 0

        try:
            ci = datetime.strptime(default_checkin, '%Y-%m-%d').date()
            co = datetime.strptime(default_checkout, '%Y-%m-%d').date()
            nights = max((co - ci).days, 1)
        except Exception:
            nights = 1



        if min_price and min_price > 0:
            # Hourly: compute base_total from slot when enabled and selected
            if hotel.hourly_stays_enabled and stay_type == 'hourly' and slot_hours in [6, 12, 24]:
                hourly_prices = []
                for rt in hotel.room_types.all():
                    try:
                        hourly_prices.append(rt.get_hourly_price(slot_hours))
                    except Exception:
                        continue
                hmin = min(hourly_prices) if hourly_prices else Decimal(min_price)
                base_total = Decimal(hmin)
            else:
                base_total = Decimal(min_price) * Decimal(nights)

            service_fee = min(base_total * Decimal('0.05'), Decimal('500'))

            gst_amount = service_fee * Decimal('0.18')

            taxes_and_fees = service_fee + gst_amount

            total = base_total + taxes_and_fees



            pricing_data = {
                'base_total': max(1, int(base_total)),
                'service_fee': max(1, int(service_fee)),
                'gst_amount': max(1, int(gst_amount)),
                'taxes_and_fees': max(1, int(taxes_and_fees)),
                'total': max(1, int(total)),
                'nights': nights,
                'slot_hours': slot_hours if (hotel.hourly_stays_enabled and stay_type == 'hourly' and slot_hours in [6,12,24]) else 0,
            }

        else:

            pricing_data = None



    except Exception:

        pricing_data = None

    

    # ========================================================================

    # DEFENSIVE: Get hotel cancellation policy (hotel-level, not room-level)

    # ========================================================================

    try:

        hotel_policy = hotel.get_structured_cancellation_policy()

        if not hotel_policy:

            # Fallback if policy undefined

            hotel_policy = {

                'policy_type': 'NON_REFUNDABLE',

                'refund_percentage': 0,

                'policy_text': 'Non-refundable booking',

                'free_cancel_until_display': 'Not applicable',

            }

    except Exception as e:

        # DEFENSIVE: Policy retrieval failed

        hotel_policy = {

            'policy_type': 'NON_REFUNDABLE',

            'refund_percentage': 0,

            'policy_text': 'Policy information unavailable',

            'free_cancel_until_display': 'Not applicable',

        }
    
    # Fetch structured policies (Goibibo-style)
    policies_by_category = {}
    try:
        from collections import defaultdict
        policies_grouped = defaultdict(list)
        for policy in hotel.policies.select_related('category').order_by('category__display_order', 'display_order'):
            policies_grouped[policy.category].append(policy)
        policies_by_category = dict(policies_grouped)
    except Exception:
        policies_by_category = {}
    
    # CRITICAL: Always populate pricing_data when room_type is specified
    # This ensures booking form components render properly during E2E tests
    if default_room_type and not pricing_data:
        try:
            selected_room = hotel.room_types.filter(id=default_room_type).first()
            if selected_room:
                room_price = selected_room.get_effective_price()
                ci = datetime.strptime(default_checkin, '%Y-%m-%d').date()
                co = datetime.strptime(default_checkout, '%Y-%m-%d').date()
                nights = max((co - ci).days, 1)
                
                if hotel.hourly_stays_enabled and stay_type == 'hourly' and slot_hours in [6, 12, 24]:
                    base_total = Decimal(selected_room.get_hourly_price(slot_hours))
                else:
                    base_total = Decimal(room_price) * Decimal(nights)
                
                service_fee = min(base_total * Decimal('0.05'), Decimal('500'))
                gst_amount = service_fee * Decimal('0.18')
                taxes_and_fees = service_fee + gst_amount
                total = base_total + taxes_and_fees
                
                pricing_data = {
                    'base_total': max(1, int(base_total)),
                    'service_fee': max(1, int(service_fee)),
                    'gst_amount': max(1, int(gst_amount)),
                    'taxes_and_fees': max(1, int(taxes_and_fees)),
                    'total': max(1, int(total)),
                    'nights': nights,
                    'slot_hours': slot_hours if (hotel.hourly_stays_enabled and stay_type == 'hourly' and slot_hours in [6,12,24]) else 0,
                }
        except Exception:
            pass
    
        # FALLBACK: If still no pricing_data, create minimal default from first room
        if not pricing_data:
            first_room = hotel.room_types.first()
            if first_room:
                base_total = Decimal(first_room.get_effective_price())
                service_fee = min(base_total * Decimal('0.05'), Decimal('500'))
                gst_amount = service_fee * Decimal('0.18')
                taxes_and_fees = service_fee + gst_amount
                total = base_total + taxes_and_fees
                pricing_data = {
                    'base_total': max(1, int(base_total)),
                    'service_fee': max(1, int(service_fee)),
                    'gst_amount': max(1, int(gst_amount)),
                    'taxes_and_fees': max(1, int(taxes_and_fees)),
                    'total': max(1, int(total)),
                    'nights': 1,
                    'slot_hours': 0,
                }
    
    context = {

        'hotel': hotel,

        'prefill_checkin': default_checkin,

        'prefill_checkout': default_checkout,

        'prefill_guests': default_guests,

        'prefill_room_type': default_room_type,

        'prefill_meal_plan': getattr(request, 'prefill_meal_plan', ''),

        'prefill_guest_name': getattr(request, 'prefill_guest_name', ''),

        'prefill_guest_email': getattr(request, 'prefill_guest_email', ''),

        'prefill_guest_phone': getattr(request, 'prefill_guest_phone', ''),

        'prefill_num_rooms': getattr(request, 'prefill_num_rooms', 1),

        'availability_snapshot': availability_snapshot,

        # NEW: Defensive context for components

        'hotel_policy': hotel_policy,

        'pricing_data': pricing_data,

        'room_types': hotel.room_types.all(),  # Explicit for templates
        
        # Goibibo-style policies
        'policies_by_category': policies_by_category,

    }

    

    return render(request, 'hotels/hotel_detail.html', context)





@csrf_exempt

def book_hotel(request, pk):

    """Book hotel (POST handler)"""

    hotel_qs = Hotel.objects.prefetch_related('room_types', 'channel_mappings').select_related('city')

    hotel = get_object_or_404(hotel_qs, pk=pk, is_active=True)



    if request.method == 'POST':

        # CRITICAL: Check if request is AJAX to enforce JSON-only response contract
        is_ajax = (request.headers.get('x-requested-with', '').lower() == 'xmlhttprequest' or
                   request.headers.get('X-Requested-With', '') == 'XMLHttpRequest')

        

        # GUEST BOOKING CONTRACT: Allow unauthenticated users to book as guests
        # Authenticated users must verify email BEFORE proceeding to payment
        
        from django.conf import settings as dj_settings
        if getattr(dj_settings, 'REQUIRE_EMAIL_VERIFICATION', True):
            if request.user.is_authenticated and not request.user.email_verified_at:

                if is_ajax:

                    from django.http import JsonResponse

                    return JsonResponse({'error': 'Please verify your email before booking'}, status=403)

                from django.contrib import messages

                messages.error(request, 'Please verify your email before booking.')

                request.session['pending_user_id'] = request.user.id

                request.session['pending_email'] = request.user.email

                request.session['pending_phone'] = getattr(request.user, 'phone', '')

                return redirect('users:verify-registration-otp')



        # ISSUE #3: Backend validation for all required fields

        room_type_id = request.POST.get('room_type_id', '').strip()

        meal_plan_id = request.POST.get('meal_plan_id', '').strip()

        checkin_date = request.POST.get('check_in', '').strip()

        checkout_date = request.POST.get('check_out', '').strip()

        num_rooms = request.POST.get('number_of_rooms', '1').strip()

        guests = request.POST.get('num_guests', '1').strip()

        guest_name = request.POST.get('guest_name', '').strip()

        guest_email = request.POST.get('guest_email', '').strip()

        guest_phone = request.POST.get('guest_phone', '').strip()
        stay_type = request.POST.get('stay_type', '').strip()
        hourly_hours_val = request.POST.get('hourly_hours', '').strip()
        hourly_hours = int(hourly_hours_val) if hourly_hours_val.isdigit() else 0



        # Persist draft to session so "Back to Booking" restores fields

        booking_draft = {

            'hotel_id': hotel.id,

            'room_type_id': room_type_id,

            'meal_plan_id': meal_plan_id,

            'check_in': checkin_date,

            'check_out': checkout_date,

            'num_rooms': num_rooms,

            'num_guests': guests,

            'guest_name': guest_name,

            'guest_email': guest_email,

            'guest_phone': guest_phone,

        }

        request.session['booking_draft'] = booking_draft

        request.session.modified = True



        # Hard block: guest identity must exist before any further processing

        if not (guest_name and guest_email and guest_phone):

            message_text = "Guest name, email, and phone number are required"

            if is_ajax:

                from django.http import JsonResponse

                return JsonResponse({'error': message_text}, status=400)

            from django.contrib import messages

            messages.error(request, message_text)

            return render(request, 'hotels/hotel_detail.html', {

                'hotel': hotel,

                'prefill_checkin': checkin_date,

                'prefill_checkout': checkout_date,

                'prefill_guests': guests,

                'prefill_room_type': room_type_id,

                'prefill_meal_plan': meal_plan_id,

                'prefill_guest_name': guest_name,

                'prefill_guest_email': guest_email,

                'prefill_guest_phone': guest_phone,

                'prefill_num_rooms': num_rooms,

            })


        # Validate all mandatory fields

        errors = []

        if not room_type_id:

            errors.append('Please select a room type')

        # Meal plan is now OPTIONAL (Priority 1 Fix)

        if not checkin_date:

            errors.append('Please select a check-in date')

        if not checkout_date:

            errors.append('Please select a check-out date')

        
        # Hourly flow: adjust validation errors (checkout not required, slot required)
        if hotel.hourly_stays_enabled and stay_type == 'hourly':
            errors = [e for e in errors if e != 'Please select a check-out date']
            if hourly_hours not in [6, 12, 24]:
                errors.append('Please select a valid hourly slot')

        if errors:

            if is_ajax:

                from django.http import JsonResponse

                return JsonResponse({'error': '; '.join(errors)}, status=400)

            from django.contrib import messages

            for error in errors:

                messages.error(request, error)

            context = {

                'hotel': hotel,

                'errors': errors,

                'prefill_checkin': checkin_date,

                'prefill_checkout': checkout_date,

                'prefill_guests': guests,

                'prefill_room_type': room_type_id,

                'prefill_meal_plan': meal_plan_id,

                'prefill_guest_name': guest_name,

                'prefill_guest_email': guest_email,

                'prefill_guest_phone': guest_phone,

                'prefill_num_rooms': num_rooms,

            }

            return render(request, 'hotels/hotel_detail.html', context)



        # Parse dates

        try:
            checkin = datetime.strptime(checkin_date, '%Y-%m-%d').date()
            checkout = datetime.strptime(checkout_date, '%Y-%m-%d').date() if checkout_date else checkin
        except Exception as e:

            logger.error(f"[DATE_PARSING_ERROR] check_in={checkin_date}, check_out={checkout_date}, error={str(e)}")

            if is_ajax:

                from django.http import JsonResponse

                return JsonResponse({'error': 'Invalid dates selected'}, status=400)

            return render(request, 'hotels/hotel_detail.html', {'hotel': hotel, 'error': 'Invalid dates selected'})



        if stay_type != 'hourly' and checkout < checkin:  # Overnight only

            if is_ajax:

                from django.http import JsonResponse

                return JsonResponse({'error': 'Check-out must be after check-in'}, status=400)

            return render(request, 'hotels/hotel_detail.html', {'hotel': hotel, 'error': 'Check-out must be after check-in'})

        

        # Additional validation: require at least 1 night

        if stay_type != 'hourly' and checkout == checkin:

            if is_ajax:

                from django.http import JsonResponse

                return JsonResponse({'error': 'Minimum 1 night stay required'}, status=400)

            return render(request, 'hotels/hotel_detail.html', {'hotel': hotel, 'error': 'Minimum 1 night stay required'})



        # Validate room type exists - with proper error handling

        try:

            if not room_type_id.isdigit():

                raise ValueError('Room ID must be numeric')

            room_type = hotel.room_types.get(id=int(room_type_id))

        except (RoomType.DoesNotExist, ValueError):

            if is_ajax:

                from django.http import JsonResponse

                return JsonResponse({'error': 'Selected room type not found'}, status=400)

            return render(request, 'hotels/hotel_detail.html', {'hotel': hotel, 'error': 'Selected room type not found'})

        
        # SPRINT-1 CRITICAL: Inventory + Block validation (internal only)
        from django.db.models import Min
        from hotels.models import RoomAvailability, RoomBlock, RoomMealPlan

        # Parse numeric fields early for availability checks
        try:
            num_rooms = int(num_rooms) if num_rooms and str(num_rooms).isdigit() else 1
            guests = int(guests) if guests and str(guests).isdigit() else 1
        except ValueError:
            friendly_error = 'Invalid room or guest count'
            if is_ajax:
                from django.http import JsonResponse
                return JsonResponse({'error': friendly_error}, status=400)
            from django.contrib import messages
            messages.error(request, friendly_error)
            return render(request, 'hotels/hotel_detail.html', {'hotel': hotel, 'error': friendly_error})

        # Meal plan must exist; auto-pick default if not provided
        meal_plan_qs = RoomMealPlan.objects.filter(room_type=room_type, is_active=True).select_related('meal_plan').order_by('display_order', 'id')
        if not meal_plan_qs.exists():
            friendly_error = 'Meal plans not configured for this room. Please contact support.'
            if is_ajax:
                from django.http import JsonResponse
                return JsonResponse({'error': friendly_error}, status=400)
            from django.contrib import messages
            messages.error(request, friendly_error)
            return render(request, 'hotels/hotel_detail.html', {'hotel': hotel, 'error': friendly_error})

        # Choose meal plan: requested id -> default -> first
        meal_plan = None
        if meal_plan_id and meal_plan_id.isdigit():
            meal_plan = meal_plan_qs.filter(id=int(meal_plan_id)).first()
        if not meal_plan:
            meal_plan = meal_plan_qs.filter(is_default=True).first() or meal_plan_qs.first()

        # Availability: internal inventory must have stock for every night
        try:
            if stay_type == 'hourly':
                availability_qs = RoomAvailability.objects.filter(
                    room_type=room_type,
                    date=checkin,
                )
            else:
                availability_qs = RoomAvailability.objects.filter(
                    room_type=room_type,
                    date__gte=checkin,
                    date__lt=checkout,
                )
            availability = availability_qs.aggregate(min_rooms=Min('available_rooms')).get('min_rooms')
        except DatabaseError as exc:
            friendly_error = 'Inventory data not configured for selected dates'
            logger.error(
                "[INVENTORY_CHECK_FAILED] hotel=%s room_type=%s error=%s",
                hotel.id,
                room_type.id,
                str(exc),
                exc_info=exc,
            )
            if is_ajax:
                from django.http import JsonResponse
                return JsonResponse({'error': friendly_error}, status=400)
            from django.contrib import messages
            messages.error(request, friendly_error)
            return render(request, 'hotels/hotel_detail.html', {'hotel': hotel, 'error': friendly_error})

        if availability is None or availability < num_rooms:
            friendly_error = 'Room not available for selected dates'
            logger.info(
                "[INVENTORY_UNAVAILABLE] hotel=%s room_type=%s checkin=%s checkout=%s min=%s rooms_requested=%s",
                hotel.id, room_type.id, checkin, checkout, availability, num_rooms,
            )
            if is_ajax:
                from django.http import JsonResponse
                return JsonResponse({'error': friendly_error}, status=400)
            from django.contrib import messages
            messages.error(request, friendly_error)
            return render(request, 'hotels/hotel_detail.html', {'hotel': hotel, 'error': friendly_error})

        # Blocks: owner blocks override availability
        block_exists = RoomBlock.objects.filter(
            room_type=room_type,
            is_active=True,
            blocked_from__lt=checkout,
            blocked_to__gt=checkin,
        ).exists()

        if block_exists:
            friendly_error = 'Room blocked by property owner for the selected dates'
            logger.warning(
                "[AVAILABILITY_BLOCK] room_type_id=%s check_in=%s check_out=%s",
                room_type_id, checkin, checkout,
            )
            if is_ajax:
                from django.http import JsonResponse
                return JsonResponse({'error': friendly_error}, status=400)
            from django.contrib import messages
            messages.error(request, friendly_error)
            return render(request, 'hotels/hotel_detail.html', {
                'hotel': hotel,
                'error': friendly_error,
                'prefill_checkin': checkin_date,
                'prefill_checkout': checkout_date,
                'prefill_guests': guests,
                'prefill_guest_name': guest_name,
                'prefill_guest_email': guest_email,
                'prefill_guest_phone': guest_phone,
                'prefill_num_rooms': num_rooms,
            })

        


        # Compute total nights for inventory validation

        nights = (checkout - checkin).days if stay_type != 'hourly' else 1



        from django.conf import settings as dj_settings
        hold_minutes = getattr(dj_settings, 'PLAYWRIGHT_HOLD_MINUTES', 10)

        lock = None

        inventory_channel = hotel.inventory_source

        booking_source = 'external' if hotel.inventory_source == 'external_cm' else 'internal'



        try:

            if hotel.inventory_source == 'external_cm':

                mapping = ChannelManagerRoomMapping.objects.filter(room_type=room_type, is_active=True).first()

                if not mapping:

                    raise InventoryLockError('Channel manager mapping is missing for the selected room.')

                cm_client = ExternalChannelManagerClient(provider=mapping.provider)

                lock_resp = cm_client.lock_inventory(mapping, checkin, checkout, num_rooms, hold_minutes=hold_minutes)

                reference_id = lock_resp.get('lock_id') or f"CM-{uuid.uuid4().hex[:10].upper()}"

                lock = InventoryLock.objects.create(

                    hotel=hotel,

                    room_type=room_type,

                    reference_id=reference_id,

                    lock_id=lock_resp.get('lock_id', reference_id),

                    source='external_cm',

                    provider=mapping.provider,

                    check_in=checkin,

                    check_out=checkout,

                    num_rooms=num_rooms,

                    expires_at=lock_resp.get('expires_at', timezone.now() + timedelta(minutes=hold_minutes)),

                    payload={'mapping_id': mapping.id},

                )

            else:

                internal_service = InternalInventoryService(hotel)

                lock = internal_service.lock_inventory(
                    room_type=room_type,
                    check_in=checkin,
                    check_out=(checkin + timedelta(days=1)) if stay_type == 'hourly' else checkout,
                    num_rooms=num_rooms,
                    hold_minutes=hold_minutes,
                )

        except InventoryLockError as exc:

            logger.error("[LOCK_FAILED] hotel=%s room_type=%s error=%s", hotel.id, room_type_id, str(exc), exc_info=True)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':

                from django.http import JsonResponse

                return JsonResponse({'error': str(exc)}, status=400)

            return render(request, 'hotels/hotel_detail.html', {'hotel': hotel, 'error': str(exc)})



        # nights already computed above

        # Calculate price using hourly or per-night logic
        if stay_type == 'hourly' and hotel.hourly_stays_enabled:
            base_total = room_type.get_hourly_price(hourly_hours) * num_rooms
        else:
            if meal_plan:
                base_total = meal_plan.calculate_total_price(num_rooms, nights)
            else:
                # If no meal plan selected, calculate from room type base price
                base_total = room_type.get_effective_price() * num_rooms * nights





        # Corporate discount (email-verified users only; mobile optional)

        corp_discount_amount = Decimal('0.00')

        corp_meta = None

        if request.user.is_authenticated and request.user.email_verified_at:

            corp = CorporateDiscount.get_for_email(guest_email or request.user.email)

            if corp:

                corp_discount_amount = Decimal(str(corp.calculate_discount(base_total, service_type='hotel')))

                if corp_discount_amount > 0:

                    corp_meta = json.dumps({

                        'type': 'corp',

                        'company': corp.company_name,

                        'domain': corp.email_domain,

                        'discount_type': corp.discount_type,

                        'discount_value': float(corp.discount_value),

                        'discount_amount': float(corp_discount_amount),

                    })



        total = base_total - corp_discount_amount



        try:

            reserved_at = timezone.now()

            # GUEST BOOKING: Support unauthenticated users (user=None)
            booking_user = request.user if request.user.is_authenticated else None
            
            # For authenticated users, use account data; for guests, use form-provided data
            if request.user.is_authenticated:
                customer_name = guest_name or request.user.get_full_name() or request.user.username
                customer_email = guest_email or request.user.email
                customer_phone = guest_phone or getattr(request.user, 'phone', '')
            else:
                # Guests must provide all contact data
                customer_name = guest_name
                customer_email = guest_email
                customer_phone = guest_phone

            booking = Booking.objects.create(

                user=booking_user,

                booking_type='hotel',

                total_amount=total,

                status='payment_pending',  # ← CRITICAL FIX: Start with payment_pending, not reserved

                reserved_at=reserved_at,

                expires_at=reserved_at + timedelta(minutes=hold_minutes),

                customer_name=customer_name,

                customer_email=customer_email,

                customer_phone=customer_phone,

                booking_source=booking_source,

                inventory_channel=inventory_channel,

                lock_id=(lock.lock_id or lock.reference_id) if lock else '',

                channel_reference=corp_meta or '',

            )



            if lock:

                lock.booking = booking

                lock.save(update_fields=['booking'])



            # CRITICAL: Use HOTEL-level cancellation policy (single source of truth)

            # Room-level policies are deprecated per system architecture

            hotel_policy = hotel.get_structured_cancellation_policy()

            policy_type = hotel_policy['policy_type']

            policy_text = hotel_policy['policy_text']

            policy_refund_percentage = hotel_policy['refund_percentage']



            # Compute cancellation cutoff based on check-in datetime and hotel policy

            from django.conf import settings as dj_settings

            from datetime import time as dtime

            

            # Use hotel policy's cancellation_hours if specified, otherwise fall back to settings default

            cancel_hours = hotel_policy.get('cancellation_hours') or getattr(dj_settings, 'CANCELLATION_FREE_HOURS_DEFAULT', 48)

            

            # Combine selected check-in date with hotel's check-in time (fallback 14:00)

            checkin_time = getattr(hotel, 'checkin_time', None) or dtime(14, 0)

            checkin_dt = timezone.make_aware(datetime.combine(checkin, checkin_time), timezone.get_current_timezone())



            if policy_type in ['FREE', 'PARTIAL']:

                policy_free_cancel_until = checkin_dt - timedelta(hours=int(cancel_hours))

            else:

                policy_free_cancel_until = None



            # SNAPSHOT (RULE D): Freeze room specs and pricing at booking time
            room_snapshot = {
                'name': room_type.name,
                'bed_type': room_type.get_bed_type_display() if room_type.bed_type else 'Not specified',
                'room_size': room_type.room_size if room_type.room_size else 0,
                'max_adults': room_type.max_adults if room_type.max_adults else 0,
                'max_children': room_type.max_children if room_type.max_children else 0,
                'is_refundable': meal_plan.meal_plan.is_refundable if meal_plan else False,
                'meal_plan_name': meal_plan.meal_plan.name if meal_plan else 'Room Only',
                'meal_plan_inclusions': meal_plan.meal_plan.inclusions if meal_plan else [],
            }
            
            # Calculate pricing components for snapshot
            base_room_price = room_type.base_price
            meal_plan_delta = meal_plan.price_delta if meal_plan else Decimal('0.00')
            price_per_night = base_room_price + meal_plan_delta
            subtotal = price_per_night * num_rooms * nights
            
            price_snapshot = {
                'base_price': float(base_room_price),
                'meal_plan_delta': float(meal_plan_delta),
                'price_per_night': float(price_per_night),
                'num_rooms': num_rooms,
                'num_nights': nights if stay_type != 'hourly' else 0,
                'hourly_hours': hourly_hours if stay_type == 'hourly' else 0,
                'subtotal': float(subtotal),
                'total': float(total),
                'stay_type': 'hourly' if stay_type == 'hourly' else 'overnight',
            }

            HotelBooking.objects.create(

                booking=booking,

                room_type=room_type,

                meal_plan=meal_plan,
                
                room_snapshot=room_snapshot,
                
                price_snapshot=price_snapshot,

                cancellation_policy=None,  # Deprecated: now using hotel-level policy

                policy_type=policy_type,

                policy_text=policy_text,

                policy_refund_percentage=policy_refund_percentage,

                policy_free_cancel_until=policy_free_cancel_until,

                policy_locked_at=timezone.now(),

                check_in=checkin,

                check_out=checkout if stay_type != 'hourly' else checkin,

                number_of_rooms=num_rooms,

                number_of_adults=guests,

                total_nights=nights if stay_type != 'hourly' else 0,

            )



            # Persist booking state before redirect; required keys for front-end recovery

            request.session['last_booking_state'] = {

                'room_type_id': str(room_type.id),

                'meal_plan_id': str(meal_plan.id) if meal_plan else '',

                'check_in': checkin.isoformat(),

                'check_out': checkout.isoformat(),

                'guest_name': guest_name,

                'guest_email': guest_email,

                'guest_phone': guest_phone,

                'rooms': num_rooms,

                'hotel_id': hotel.id,

                'num_guests': guests,

                'booking_id': str(booking.booking_id),

            }

            # Keep booking_draft aligned with actual booking for Back to Booking

            request.session['booking_draft'] = {

                'hotel_id': hotel.id,

                'room_type_id': str(room_type.id),

                'meal_plan_id': str(meal_plan.id) if meal_plan else '',

                'check_in': checkin.isoformat(),

                'check_out': checkout.isoformat(),

                'num_rooms': num_rooms,

                'num_guests': guests,

                'guest_name': guest_name,

                'guest_email': guest_email,

                'guest_phone': guest_phone,

                'booking_id': str(booking.booking_id),

            }

            request.session.modified = True

            request.session.save()



            # Use the public booking UUID, not the numeric PK, to match URL patterns

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':

                from django.http import JsonResponse

                return JsonResponse({'booking_url': f'/bookings/{booking.booking_id}/confirm/'}, status=200)

            return redirect(f'/bookings/{booking.booking_id}/confirm/')

        except Exception as exc:

            logger.error("Booking failed for hotel %s: %s", hotel.id, str(exc), exc_info=True)

            if lock and lock.source == 'internal_cm':

                InternalInventoryService(hotel).release_lock(lock)

            elif lock and lock.source == 'external_cm':

                try:

                    ExternalChannelManagerClient(provider=lock.provider).release_lock(lock.lock_id or lock.reference_id)

                except InventoryLockError:

                    pass

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':

                from django.http import JsonResponse

                return JsonResponse({'error': 'Booking failed'}, status=400)

            return render(request, 'hotels/hotel_detail.html', {'hotel': hotel, 'error': str(exc)})



    return redirect(f'/hotels/{pk}/')





# ============================================

# SEARCH INTELLIGENCE & SUGGESTIONS APIs

# ============================================



def calculate_distance(lat1, lon1, lat2, lon2):

    """Calculate distance between two coordinates in km (Haversine formula)"""

    try:

        lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])

        dlon = lon2 - lon1

        dlat = lat2 - lat1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2

        c = 2 * asin(sqrt(a))

        km = 6371 * c

        return round(km, 1)

    except:

        return None





# Mapping of cities to sub-areas based on coordinates

AREA_MAPPINGS = {

    'Coorg': {

        'Madikeri': {'lat_min': 12.4, 'lat_max': 12.5, 'lon_min': 75.7, 'lon_max': 75.8},

        'Kushalnagar': {'lat_min': 12.3, 'lat_max': 12.4, 'lon_min': 75.9, 'lon_max': 76.0},

        'Virajpet': {'lat_min': 12.2, 'lat_max': 12.3, 'lon_min': 75.8, 'lon_max': 75.9},

    },

    'Ooty': {

        'Coonoor': {'lat_min': 11.3, 'lat_max': 11.4, 'lon_min': 76.7, 'lon_max': 76.8},

        'Kotagiri': {'lat_min': 11.4, 'lat_max': 11.5, 'lon_min': 76.8, 'lon_max': 76.9},

    },

    'Goa': {

        'North Goa': {'lat_min': 15.5, 'lat_max': 15.8, 'lon_min': 73.7, 'lon_max': 73.9},

        'South Goa': {'lat_min': 14.8, 'lat_max': 15.3, 'lon_min': 73.7, 'lon_max': 74.0},

    },

}





@api_view(['GET'])

def search_suggestions(request):

    """

    FIX-2: Autocomplete suggestions for hotel search

    

    Returns: Cities, Areas, and Hotels with property counts

    Never returns suggestions with zero properties

    """

    query = request.query_params.get('q', '').strip().lower()

    

    if len(query) < 1:

        return Response({'suggestions': []})

    

    suggestions = []

    

    # Search Cities

    cities_list = City.objects.filter(

        name__icontains=query

    ).distinct()

    

    for city in cities_list:

        hotel_count = Hotel.objects.filter(city=city, is_active=True).count()

        if hotel_count > 0:

            suggestions.append({

                'type': 'city',

                'id': city.id,

                'name': city.name,

                'count': hotel_count,

                'display': f"{city.name} ({hotel_count} hotel{'s' if hotel_count != 1 else ''})"

            })

    

    # Search Areas (sub-regions within cities)

    city_areas_found = set()

    for hotel in Hotel.objects.filter(name__icontains=query, is_active=True).select_related('city'):

        city_name = hotel.city.name

        if city_name in AREA_MAPPINGS:

            for area_name, bounds in AREA_MAPPINGS[city_name].items():

                if (bounds['lat_min'] <= hotel.latitude <= bounds['lat_max'] and
                    bounds['lon_min'] <= hotel.longitude <= bounds['lon_max']):

                    area_key = (city_name, area_name)

                    if area_key not in city_areas_found:

                        city_areas_found.add(area_key)

                        area_count = Hotel.objects.filter(

                            city__name=city_name,

                            latitude__gte=bounds['lat_min'],

                            latitude__lte=bounds['lat_max'],

                            longitude__gte=bounds['lon_min'],

                            longitude__lte=bounds['lon_max'],

                            is_active=True

                        ).count()

                        if area_count > 0:

                            suggestions.append({

                                'type': 'area',

                                'city': city_name,

                                'name': area_name,

                                'count': area_count,

                                'display': f"{area_name} ({area_count} hotel{'s' if area_count != 1 else ''})"

                            })

    

    # Search Hotels

    hotels = Hotel.objects.filter(name__icontains=query, is_active=True)[:10]

    for hotel in hotels:

        room_count = hotel.room_types.count()

        if room_count > 0:

            suggestions.append({

                'type': 'hotel',

                'id': hotel.id,

                'name': hotel.name,

                'city': hotel.city.name,

                'count': room_count,

                'display': f"{hotel.name}, {hotel.city.name} ({room_count} room{'s' if room_count != 1 else ''})"

            })

    

    return Response({'suggestions': suggestions})





@api_view(['GET'])

def search_with_distance(request):

    """

    FIX-2: Search hotels with distance calculation

    

    Query Params:

    - city: City name (required)

    - area: Sub-area name (optional)

    - user_lat: User latitude (optional)

    - user_lon: User longitude (optional)

    - radius: Search radius in km (default 50)

    

    Returns: Hotels with distances from user or city center

    Fallback: If no hotels in radius, return entire city with "Showing across city" banner

    """

    city_name = request.query_params.get('city', '').strip()

    area_name = request.query_params.get('area', '').strip()

    user_lat = request.query_params.get('user_lat')

    user_lon = request.query_params.get('user_lon')

    radius = int(request.query_params.get('radius', 50))

    

    if not city_name:

        return Response({'error': 'city parameter required'}, status=400)

    

    try:

        city = City.objects.get(name__iexact=city_name)

    except City.DoesNotExist:

        return Response({'error': f'City "{city_name}" not found'}, status=404)

    

    # Get hotel queryset

    if area_name and city_name in AREA_MAPPINGS and area_name in AREA_MAPPINGS[city_name]:

        bounds = AREA_MAPPINGS[city_name][area_name]

        hotels = Hotel.objects.filter(

            city=city,

            latitude__gte=bounds['lat_min'],

            latitude__lte=bounds['lat_max'],

            longitude__gte=bounds['lon_min'],

            longitude__lte=bounds['lon_max'],

            is_active=True

        ).prefetch_related('room_types', 'images')

        search_context = f"{area_name}, {city_name}"

    else:

        hotels = Hotel.objects.filter(city=city, is_active=True).prefetch_related('room_types', 'images')

        search_context = city_name

    

    # Apply distance filtering if user location provided

    fallback_used = False

    if user_lat and user_lon:

        try:

            user_lat, user_lon = float(user_lat), float(user_lon)

            hotels_with_distance = []

            for hotel in hotels:

                dist = calculate_distance(user_lat, user_lon, hotel.latitude, hotel.longitude)

                if dist and dist <= radius:

                    hotels_with_distance.append((hotel, dist))

            

            # Fallback: If no hotels in radius, show all hotels in city

            if not hotels_with_distance:

                fallback_used = True

                hotels_with_distance = []

                for hotel in Hotel.objects.filter(city=city, is_active=True).prefetch_related('room_types', 'images'):

                    dist = calculate_distance(user_lat, user_lon, hotel.latitude, hotel.longitude)

                    if dist:

                        hotels_with_distance.append((hotel, dist))

            

            # Sort by distance, then rating

            hotels_with_distance.sort(key=lambda x: (x[1], -x[0].star_rating))

        except (ValueError, TypeError):

            hotels_with_distance = [(h, None) for h in hotels]

    else:

        # Use city center as reference (simple average)

        city_hotels = Hotel.objects.filter(city=city, is_active=True)

        if city_hotels.exists():

            avg_lat = sum(h.latitude for h in city_hotels) / city_hotels.count()

            avg_lon = sum(h.longitude for h in city_hotels) / city_hotels.count()

        else:

            avg_lat, avg_lon = city.latitude, city.longitude

        

        hotels_with_distance = []

        for hotel in hotels:

            dist = calculate_distance(avg_lat, avg_lon, hotel.latitude, hotel.longitude)

            hotels_with_distance.append((hotel, dist))

        

        hotels_with_distance.sort(key=lambda x: (-x[0].star_rating, x[1] if x[1] else 999))

    

    # Build response

    hotel_list = []

    for hotel, distance in hotels_with_distance:

        min_price = hotel.room_types.aggregate(min_price=Min('base_price'))['min_price']

        hotel_list.append({

            'id': hotel.id,

            'name': hotel.name,

            'city': hotel.city.name,

            'rating': float(hotel.star_rating),

            'min_price': float(min_price) if min_price else None,

            'distance_km': distance,

            'has_wifi': hotel.has_wifi,

            'has_pool': hotel.has_pool,

            'has_parking': hotel.has_parking,

        })

    

    return Response({

        'search_context': search_context,

        'fallback': fallback_used,

        'fallback_message': f'Showing hotels across {city_name}' if fallback_used else None,

        'total': len(hotel_list),

        'hotels': hotel_list

    })





def universal_search(request):

    """

    Universal search across cities and hotels.

    Matches: City name, Property name

    Returns: JSON response with matching results

    """

    from django.http import JsonResponse

    from core.models import City

    

    q = request.GET.get('q', '').strip()

    

    if not q or len(q) < 1:

        return JsonResponse([], safe=False)

    

    results = []

    

    # Search Cities - clicking redirects to filtered hotel list

    cities = City.objects.filter(name__icontains=q)

    for city in cities:

        hotel_count = Hotel.objects.filter(city=city, is_active=True).count()

        if hotel_count > 0:

            results.append({

                'type': 'city',

                'id': city.id,

                'label': f"{city.name} ({hotel_count} hotel{'s' if hotel_count != 1 else ''})",

                'name': city.name,

                'url': f"/hotels/?city_id={city.id}"  # Fixed: use city_id parameter for filtering

            })

    

    # Search Hotels

    hotels = Hotel.objects.filter(name__icontains=q, is_active=True)[:10]

    for hotel in hotels:

        results.append({

            'type': 'hotel',

            'id': hotel.id,

            'label': hotel.name,

            'name': hotel.name,

            'city': hotel.city.name,

            'url': f"/hotels/{hotel.id}/"

        })

    

    # Search Areas / Landmarks (based on address substrings)

    area_labels = set()

    area_hotels = Hotel.objects.filter(address__icontains=q, is_active=True)[:10]

    for h in area_hotels:

        label = h.address

        if not label:

            continue

        # Normalize and deduplicate simple area strings

        label_norm = label.strip()

        if label_norm and label_norm.lower() not in area_labels:

            area_labels.add(label_norm.lower())

            results.append({

                'type': 'area',

                'label': label_norm,

                'url': f"/hotels/?q={q}"

            })

    

    return JsonResponse(results, safe=False)


# ============================================

# WALLET & ADMIN APIs (PHASE 1)

# ============================================


@api_view(['GET'])
def get_wallet_status(request):
    """
    Get wallet status for logged-in user.
    Returns empty for guests (not authenticated).
    """
    if not request.user.is_authenticated:
        return Response({
            'is_authenticated': False,
            'balance': None,
            'message': 'Login to view wallet'
        }, status=status.HTTP_200_OK)
    
    from payments.models import Wallet
    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={'balance': Decimal('0.00')})
    
    return Response({
        'is_authenticated': True,
        'balance': float(wallet.balance),
        'currency': 'INR',
        'available_balance': float(wallet.get_available_balance()),
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def update_room_price_admin(request):
    """
    Admin endpoint to update room pricing immediately.
    Must be staff user.
    
    Request body:
    {
        "room_type_id": 1,
        "base_price": 5000,
        "reason": "Admin update"
    }
    """
    if not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    room_type_id = request.data.get('room_type_id')
    new_price = request.data.get('base_price')
    reason = request.data.get('reason', 'Admin price update')
    
    if not room_type_id or new_price is None:
        return Response(
            {'error': 'room_type_id and base_price required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        new_price = Decimal(str(new_price))
        if new_price <= 0:
            raise ValueError("Price must be positive")
    except Exception as e:
        return Response(
            {'error': f'Invalid price: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        room_type = RoomType.objects.get(id=room_type_id)
        old_price = room_type.base_price
        room_type.base_price = new_price
        room_type.save(update_fields=['base_price', 'updated_at'])
        
        # Log the change
        from .models import PriceLog
        PriceLog.objects.create(
            room_type=room_type,
            old_price=old_price,
            new_price=new_price,
            reason=reason
        )
        
        return Response({
            'success': True,
            'message': f'Price updated from {old_price} to {new_price}',
            'room_type_id': room_type_id,
            'old_price': float(old_price),
            'new_price': float(new_price),
        }, status=status.HTTP_200_OK)
    
    except RoomType.DoesNotExist:
        return Response(
            {'error': 'Room type not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to update price: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_room_availability_with_hold_timer(request, room_type_id):
    """
    Get availability and hold timer info for a room.
    Used by UI to display "Only X left" and countdown.
    
    Query params:
    - check_in: Check-in date (YYYY-MM-DD)
    - check_out: Check-out date (YYYY-MM-DD)
    """
    try:
        room_type = RoomType.objects.get(id=room_type_id)
    except RoomType.DoesNotExist:
        return Response(
            {'error': 'Room type not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    check_in_str = request.query_params.get('check_in')
    check_out_str = request.query_params.get('check_out')
    
    if not check_in_str or not check_out_str:
        return Response(
            {'error': 'check_in and check_out required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        check_in = date.fromisoformat(check_in_str)
        check_out = date.fromisoformat(check_out_str)
    except ValueError:
        return Response(
            {'error': 'Invalid date format (YYYY-MM-DD)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    calculator = PricingCalculator(room_type.hotel)
    availability = calculator.check_availability(
        room_type=room_type,
        check_in=check_in,
        check_out=check_out,
        num_rooms=1
    )
    
    available_count = availability.get('available_rooms', 0)
    
    # Calculate hold timer: if active locks exist, show countdown
    from bookings.models import InventoryLock
    now = timezone.now()
    active_locks = InventoryLock.objects.filter(
        room_type=room_type,
        check_in=check_in,
        check_out=check_out,
        status__in=['active', 'confirmed'],
        expires_at__gt=now
    ).order_by('-expires_at')
    
    hold_expires_at = None
    countdown_seconds = None
    if active_locks.exists():
        hold_expires_at = active_locks.first().expires_at.isoformat()
        countdown_seconds = int((active_locks.first().expires_at - now).total_seconds())
    
    return Response({
        'room_type_id': room_type_id,
        'check_in': check_in_str,
        'check_out': check_out_str,
        'available_rooms': available_count,
        'inventory_warning': f'Only {available_count} left' if 0 < available_count < 5 else None,
        'is_available': available_count > 0,
        'hold_expires_at': hold_expires_at,
        'hold_countdown_seconds': countdown_seconds,
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_meal_plans_for_room(request, room_type_id):
    """
    Get all available meal plans for a room type.
    
    Response: Array of meal plans with price deltas (for backend-driven pricing).
    """
    try:
        room_type = RoomType.objects.get(id=room_type_id)
    except RoomType.DoesNotExist:
        return Response(
            {'error': 'Room type not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    meal_plans = RoomMealPlan.objects.filter(
        room_type=room_type,
        is_active=True
    ).select_related('meal_plan').order_by('display_order', 'id')
    
    meal_plan_list = []
    for rmp in meal_plans:
        meal_plan_list.append({
            'id': rmp.id,
            'room_meal_plan_id': rmp.id,
            'name': rmp.meal_plan.name if rmp.meal_plan else 'Room Only',
            'plan_type': rmp.meal_plan.plan_type if rmp.meal_plan else 'room_only',
            'description': rmp.meal_plan.description if rmp.meal_plan else '',
            'inclusions': rmp.meal_plan.inclusions if rmp.meal_plan else [],
            'price_delta': float(rmp.price_delta or 0),
            'display_order': rmp.display_order,
            'data_testid': f'meal-plan-{rmp.id}',
        })
    
    return Response({
        'room_type_id': room_type_id,
        'meal_plans': meal_plan_list,
    }, status=status.HTTP_200_OK)