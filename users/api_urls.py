from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views
from .wallet_api import get_wallet_balance, check_wallet_payment

app_name = 'users_api'

urlpatterns = [
    path('register/', csrf_exempt(views.RegisterAPIView.as_view()), name='api-register'),
    path('login/', csrf_exempt(views.LoginAPIView.as_view()), name='api-login'),
    path('profile/', views.UserProfileView.as_view(), name='api-profile'),
    path('wallet/balance/', get_wallet_balance, name='wallet-balance'),
    path('wallet/check-payment/', check_wallet_payment, name='wallet-check-payment'),
]
