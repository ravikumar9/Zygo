from django.shortcuts import render
from django.views.generic import TemplateView
from hotels.models import Hotel
from buses.models import Bus
from packages.models import Package
from core.models import City
from core.utils import get_recent_searches
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import time


class HomeView(TemplateView):
    """Home page view"""
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Show full city list in the search dropdown so users can find any destination
        context['popular_cities'] = City.objects.all().order_by('name')
        context['featured_hotels'] = Hotel.objects.filter(is_featured=True)[:6]
        context['featured_packages'] = Package.objects.filter(is_active=True)[:4]
        context['recent_searches'] = get_recent_searches(self.request.session)
        context['show_location_prompt'] = not self.request.session.get('location_prompt_shown', False)
        if context['show_location_prompt']:
            self.request.session['location_prompt_shown'] = True
            self.request.session.modified = True
        return context


class AboutView(TemplateView):
    """About page view"""
    template_name = 'about.html'


class ContactView(TemplateView):
    """Contact page view"""
    template_name = 'contact.html'


def healthz(request):
    """Lightweight health endpoint.

    Returns 200 only when:
    - DB responds to a simple SELECT
    - Cache set/get succeeds (if configured)
    """
    status = {
        'status': 'ok',
        'db': 'ok',
        'cache': 'ok',
        'timestamp': int(time.time()),
        'version': 'v1'
    }
    # DB ping
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception as e:
        status['db'] = f'fail: {type(e).__name__}'
        status['status'] = 'fail'

    # Cache check (best-effort)
    try:
        cache.set('healthz_key', 'ok', 5)
        if cache.get('healthz_key') != 'ok':
            status['cache'] = 'fail: read_mismatch'
            status['status'] = 'fail'
    except Exception as e:
        status['cache'] = f'fail: {type(e).__name__}'
        status['status'] = 'fail'

    http_status = 200 if status['status'] == 'ok' else 503
    return JsonResponse(status, status=http_status)
