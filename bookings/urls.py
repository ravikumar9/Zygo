from django.urls import path
from .views import BookingListView, BookingDetailView, my_bookings  # Import classes explicitly
from . import views  # Still import views for other view functions
from .status_sync import get_booking_status
from .cancellation_views import refund_preview_api, cancel_booking_with_refund
from .promo_api import validate_promo_code

app_name = 'bookings'

urlpatterns = [
    path('my-bookings/', my_bookings, name='my_bookings'),
    path('', BookingListView.as_view(), name='booking-list'),
    path('<uuid:booking_id>/', BookingDetailView.as_view(), name='booking-detail'),
    path('<uuid:booking_id>/confirm/', views.booking_confirmation, name='booking-confirm'),
    path('<uuid:booking_id>/payment/', views.payment_page, name='booking-payment'),
    path('<uuid:booking_id>/cancel/', views.cancel_booking, name='cancel-booking'),
    path('<uuid:booking_id>/confirm-wallet-only/', views.confirm_wallet_only_booking, name='confirm-wallet-only'),
    path('api/timer/<uuid:booking_id>/', views.get_booking_timer, name='booking-timer'),
    path('api/status/<uuid:booking_id>/', get_booking_status, name='booking-status'),
    path('api/create-order/', views.create_razorpay_order, name='create-order'),
    path('api/verify-payment/', views.verify_payment, name='verify-payment'),
    path('api/validate-promo/', validate_promo_code, name='validate-promo'),
    # FIX-4 STEP-4: Cancellation endpoints
    path('api/refund-preview/<uuid:booking_id>/', refund_preview_api, name='refund-preview-api'),
    path('api/cancel/<uuid:booking_id>/', cancel_booking_with_refund, name='cancel-refund-api'),
]

