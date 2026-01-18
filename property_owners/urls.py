from django.urls import path
from . import views

app_name = 'property_owners'

urlpatterns = [
    path('register/', views.register_property_owner, name='register'),
    path('dashboard/', views.property_owner_dashboard, name='dashboard'),
    path('property/create/', views.create_property_draft, name='create_property'),
    path('property/<int:property_id>/detail/', views.property_detail, name='property_detail'),
    path('property/<int:property_id>/check-completion/', views.property_check_completion, name='check_completion'),
]
