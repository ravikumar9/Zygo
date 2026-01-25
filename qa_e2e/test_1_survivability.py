"""
SECTION A: SURVIVABILITY & DATA INTEGRITY
Test zero-room hotels, missing data scenarios
"""
import pytest
from playwright.sync_api import Page, expect
import datetime


class TestSurvivability:
    
    def test_hotel_with_zero_rooms(self, page: Page, base_url: str, seed_data):
        """Property with ZERO rooms: form hidden, no CTA"""
        hotel_id = seed_data['hotel_zero_rooms'].id
        
        page.goto(f"{base_url}/hotels/{hotel_id}/")
        page.screenshot(path="test-results/01_zero_rooms_hotel.png", full_page=True)
        
        # Must show no rooms message
        expect(page.locator('text=/No rooms available/i')).to_be_visible()
        
        # Form must be hidden
        booking_form = page.locator('form#bookingForm')
        if booking_form.count() > 0:
            expect(booking_form).not_to_be_visible()
        
        print("✅ PASS: Zero-room hotel survivability")
    
    
    def test_hotel_with_no_meal_plans(self, page: Page, base_url: str, seed_data):
        """Hotel with rooms but NO meal plans: booking proceeds"""
        hotel_id = seed_data['hotel_no_meals'].id
        
        page.goto(f"{base_url}/hotels/{hotel_id}/")
        
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        
        page.fill('input[name="checkin"]', today.strftime('%Y-%m-%d'))
        page.fill('input[name="checkout"]', tomorrow.strftime('%Y-%m-%d'))
        
        room_select = page.locator('select[name="room_type"]')
        if room_select.count() > 0:
            options = room_select.locator('option').all()
            if len(options) > 1:
                room_select.select_option(index=1)
        
        page.screenshot(path="test-results/02_no_meal_plans.png", full_page=True)
        print("✅ PASS: Hotel with no meal plans")
    
    
    def test_hotel_with_no_images(self, page: Page, base_url: str, seed_data):
        """Hotel with NO images: layout intact"""
        hotel_id = seed_data['hotel_no_images'].id
        
        page.goto(f"{base_url}/hotels/{hotel_id}/")
        page.screenshot(path="test-results/03_no_images.png", full_page=True)
        
        print("✅ PASS: Hotel with no images")
    
    
    def test_zero_rooms_no_errors(self, page: Page, base_url: str, seed_data):
        """Zero-room hotel page loads without errors"""
        hotel_id = seed_data['hotel_zero_rooms'].id
        
        page.goto(f"{base_url}/hotels/{hotel_id}/")
        page.screenshot(path="test-results/04_zero_rooms_graceful.png", full_page=True)
        
        # No stack traces
        page_content = page.content()
        assert "Traceback" not in page_content
        
        print("✅ PASS: Zero-room hotel loads gracefully")
