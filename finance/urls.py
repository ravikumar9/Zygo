from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/properties/', views.property_metrics, name='property_metrics'),
    path('admin/bookings/', views.booking_table, name='booking_table'),
    path('owner/earnings/', views.owner_earnings, name='owner_earnings'),
    path('invoice/<int:invoice_id>/download/', views.download_invoice, name='download_invoice'),
]
