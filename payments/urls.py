from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('create-order/', views.CreatePaymentOrderView.as_view(), name='create-order'),
    path('verify/', views.VerifyPaymentView.as_view(), name='verify'),
    path('razorpay-webhook/', views.RazorpayWebhookView.as_view(), name='razorpay-webhook'),
    path('process-wallet/', views.process_wallet_payment, name='process-wallet'),
    path('wallet/', views.WalletView.as_view(), name='wallet'),
]
