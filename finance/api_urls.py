from django.urls import path
from . import api_views

app_name = 'finance_api'

urlpatterns = [
    # Admin APIs (SUPER_ADMIN, FINANCE_ADMIN)
    path('dashboard/metrics/', api_views.dashboard_metrics_api, name='dashboard_metrics'),
    path('invoices/', api_views.invoices_api, name='invoices'),
    path('invoices/<int:invoice_id>/', api_views.invoice_detail_api, name='invoice_detail'),
    path('ledger/', api_views.ledger_api, name='ledger'),
    
    # Admin booking list (all admin roles)
    path('bookings/', api_views.bookings_api, name='bookings'),
    
    # Owner APIs (property owners)
    path('owner/earnings/', api_views.owner_earnings_api, name='owner_earnings'),
]
