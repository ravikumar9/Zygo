"""Corporate dashboard URLs"""
from django.urls import path
from . import views_corporate

app_name = 'corporate'

urlpatterns = [
    path('signup/', views_corporate.corporate_signup, name='signup'),
    path('dashboard/', views_corporate.corporate_dashboard, name='dashboard'),
    path('dashboard/status/', views_corporate.corporate_status, name='status'),
]
