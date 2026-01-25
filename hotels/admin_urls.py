"""Admin API URL routing"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .admin_api import AdminRoomTypeViewSet

router = DefaultRouter()
router.register(r'rooms', AdminRoomTypeViewSet, basename='admin-room')

urlpatterns = [
    path('', include(router.urls)),
]
