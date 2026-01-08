from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from .models import Booking  # Ensure model import

@login_required
class BookingListView(ListView):
    model = Booking
    template_name = 'bookings/booking_list.html'  # Specify your template path if needed

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by('-created_at')

@login_required
class BookingDetailView(DetailView):
    model = Booking
    template_name = 'bookings/booking_detail.html'  # Specify your template path if needed

    def get_object(self, queryset=None):
        booking_id = self.kwargs.get('booking_id')
        return get_object_or_404(Booking, booking_id=booking_id, user=self.request.user)

