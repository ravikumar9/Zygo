from django.urls import path
from . import views
# from .admin_api import admin_update_room_price

app_name = 'hotels'

urlpatterns = [
    # Web pages (for /hotels/ path)
    path('', views.hotel_list, name='hotel_list'),
    path('<int:pk>/', views.hotel_detail, name='hotel_detail'),
    # Alias route to satisfy E2E patterns expecting '/detail/' in URL
    path('detail/<int:pk>/', views.hotel_detail, name='hotel_detail_alias'),
    path('<int:pk>/book/', views.book_hotel, name='book_hotel'),
    
    # API endpoints - Listing & Search
    path('api/list/', views.HotelListView.as_view(), name='hotel-list-api'),
    path('api/search/', views.HotelSearchView.as_view(), name='hotel-search-api'),
    path('api/<int:pk>/', views.HotelDetailView.as_view(), name='hotel-detail-api'),
    
    # API endpoints - Pricing & Availability
    path('api/calculate-price/', views.calculate_price, name='calculate-price'),
    path('api/check-availability/', views.check_availability, name='check-availability'),
    path('api/<int:hotel_id>/occupancy/', views.get_hotel_occupancy, name='hotel-occupancy'),
    
    # API endpoints - Search Intelligence (FIX-2)
    path('api/suggestions/', views.search_suggestions, name='search-suggestions'),
    path('api/search-with-distance/', views.search_with_distance, name='search-with-distance'),
    path('api/universal-search/', views.universal_search, name='universal-search'),
    
    # API endpoints - Phase 1 Features
    path('api/wallet/status/', views.get_wallet_status, name='wallet-status'),
    path('api/room/<int:room_type_id>/availability-with-hold/', views.get_room_availability_with_hold_timer, name='room-availability-hold'),
    path('api/room/<int:room_type_id>/meal-plans/', views.get_meal_plans_for_room, name='room-meal-plans'),
    path('api/admin/price-update/', views.update_room_price_admin, name='admin-price-update'),
]

