from django.urls import path
from . import views
from . import dashboard_api
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
    
    # API endpoints - PHASE 2.7.3.2 Dashboard (Revenue Risk Intelligence)
    path('api/admin/dashboard/summary/', dashboard_api.dashboard_executive_summary, name='dashboard-summary'),
    path('api/admin/dashboard/confidence/', dashboard_api.dashboard_confidence_score, name='dashboard-confidence'),
    path('api/admin/dashboard/heatmap/', dashboard_api.dashboard_risk_heatmap, name='dashboard-heatmap'),
    path('api/admin/dashboard/simulation/', dashboard_api.dashboard_enforcement_simulation, name='dashboard-simulation'),
    path('api/admin/dashboard/current-mode/', dashboard_api.dashboard_current_mode, name='dashboard-current-mode'),
    path('api/admin/dashboard/full-status/', dashboard_api.dashboard_full_status, name='dashboard-full-status'),
    path('api/admin/dashboard/switch-mode/', dashboard_api.dashboard_enforcement_switch, name='dashboard-switch-mode'),
    
    # API endpoints - PHASE 2.7.3.3 Revenue Intelligence (P0 SPRINT)
    path('api/admin/margin/suggestion/<int:room_type_id>/', dashboard_api.margin_suggestion, name='margin-suggestion'),
    path('api/admin/competitor/trust/<str:channel>/', dashboard_api.competitor_trust, name='competitor-trust'),
    path('api/admin/risk/alerts/', dashboard_api.risk_alerts, name='risk-alerts'),
    
    # API endpoints - PHASE 2.7.3.4 Owner Price Nudge (SMART DISCOUNT)
    path('api/owner/price-nudge/<int:room_type_id>/', dashboard_api.owner_price_nudge, name='owner-price-nudge'),
    path('api/owner/price-nudge/<int:room_type_id>/accept/', dashboard_api.owner_price_nudge_accept, name='owner-nudge-accept'),
    path('api/owner/price-nudge/<int:room_type_id>/reject/', dashboard_api.owner_price_nudge_reject, name='owner-nudge-reject'),

    # API endpoints - PHASE 2.7.3.5 Owner Negotiation (PREMIUM)
    path('api/owner/negotiation/opportunity/<int:hotel_id>/', dashboard_api.owner_negotiation_opportunity, name='owner-negotiation-opportunity'),
    path('api/owner/negotiation/propose/', dashboard_api.owner_negotiation_propose, name='owner-negotiation-propose'),
    path('api/owner/negotiation/respond/', dashboard_api.owner_negotiation_respond, name='owner-negotiation-respond'),
    path('api/admin/negotiation/active/', dashboard_api.admin_negotiation_active, name='admin-negotiation-active'),

    # API endpoints - PHASE 2.7.3.6 Owner Mobile Control Surface (READ-ONLY)
    path('api/owner/mobile/negotiation-opportunities/<int:hotel_id>/', dashboard_api.owner_mobile_negotiation_opportunities, name='owner-mobile-negotiation-opportunities'),
    path('api/owner/mobile/pending-nudges/<int:hotel_id>/', dashboard_api.owner_mobile_pending_nudges, name='owner-mobile-pending-nudges'),
    path('api/owner/mobile/history/<int:hotel_id>/', dashboard_api.owner_mobile_history, name='owner-mobile-history'),
    path('api/owner/mobile/incentives/<int:hotel_id>/', dashboard_api.owner_mobile_incentives, name='owner-mobile-incentives'),
]

