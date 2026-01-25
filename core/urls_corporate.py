"""Corporate dashboard URLs"""
from django.urls import path
from . import views_corporate

app_name = 'corporate'

urlpatterns = [
    # Preferred routes
    path('register/', views_corporate.corporate_signup, name='register'),
    path('dashboard/', views_corporate.corporate_dashboard, name='dashboard'),
    path('dashboard/status/', views_corporate.corporate_status, name='status'),
    # Backwards-compatible alias
    path('signup/', views_corporate.corporate_signup, name='signup'),
]
