from django.urls import path
from . import views
from . import views_corporate

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('healthz', views.healthz, name='healthz'),
    # Corporate registration flow
    path('corporate/register/', views_corporate.corporate_signup, name='corporate-register'),
    path('corporate/dashboard/', views_corporate.corporate_dashboard, name='corporate-dashboard'),
]
