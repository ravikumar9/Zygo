from django.urls import path
from . import views
from . import operator_views

app_name = 'buses'

urlpatterns = [
    # Web routes
    path('', views.bus_list, name='bus_list'),
    path('<int:bus_id>/', views.bus_detail, name='bus_detail'),
    path('<int:bus_id>/book/', views.book_bus, name='book_bus'),
    
    # Session 3: Operator registration & approval workflow
    path('operator/register/', operator_views.operator_create_draft, name='operator_register'),
    path('operator/<int:pk>/', operator_views.operator_detail, name='operator_detail'),
    path('operator/<int:pk>/submit/', operator_views.operator_submit, name='operator_submit'),
    path('operator/<int:pk>/completion/', operator_views.operator_completion_json, name='operator_completion'),
    path('operator/dashboard/', operator_views.operator_dashboard, name='operator_dashboard'),
    
    # Sprint-1: Bulk CSV Schedule Import
    path('operator/schedule/upload/', operator_views.upload_schedule_csv, name='upload_schedule_csv'),
    path('operator/schedule/import/<int:import_id>/preview/', operator_views.preview_schedule_import, name='preview_schedule_import'),
    path('operator/schedule/import/<int:import_id>/confirm/', operator_views.confirm_schedule_import, name='confirm_schedule_import'),
    
    # API routes
    path('search/', views.BusSearchView.as_view(), name='bus-search'),
    path('routes/', views.BusRouteListView.as_view(), name='route-list'),
    path('routes/<int:pk>/', views.BusRouteDetailView.as_view(), name='route-detail'),
]
