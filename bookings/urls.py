from django.urls import path
from .views import BookingListView, BookingDetailView, my_bookings  # Import classes explicitly
from . import views  # Still import views for other view functions
from .status_sync import get_booking_status

app_name = 'bookings'

urlpatterns = [
    path('my-bookings/', my_bookings, name='my_bookings'),
    path('', BookingListView.as_view(), name='booking-list'),
    path('<uuid:booking_id>/', BookingDetailView.as_view(), name='booking-detail'),
    path('<uuid:booking_id>/confirm/', views.booking_confirmation, name='booking-confirm'),
    path('<uuid:booking_id>/payment/', views.payment_page, name='booking-payment'),
    path('<uuid:booking_id>/cancel/', views.cancel_booking, name='cancel-booking'),
    path('api/timer/<uuid:booking_id>/', views.get_booking_timer, name='booking-timer'),
    path('api/status/<uuid:booking_id>/', get_booking_status, name='booking-status'),
    path('api/create-order/', views.create_razorpay_order, name='create-order'),
    path('api/verify-payment/', views.verify_payment, name='verify-payment'),
]

