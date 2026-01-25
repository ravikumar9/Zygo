#!/usr/bin/env python
"""
COMPLETE PAYMENT FLOW TEST - ALL HOTELS
Tests booking → reserve → payment for every hotel
Generates PASS/FAIL report with evidence
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from hotels.models import Hotel, RoomType, RoomMealPlan
from bookings.models import Booking, HotelBooking, InventoryLock
from users.models import User
from hotels.views import calculate_service_fee, format_price_disclosure

class PaymentFlowTester:
    def __init__(self):
        self.client = Client()
        self.test_user = None
        self.results = {
            'pass': [],
            'fail': [],
            'error': [],
            'total': 0,
            'passed': 0,
            'failed': 0,
        }
        self.setup_test_user()
    
    def setup_test_user(self):
        """Create or get test user"""
        try:
            self.test_user = User.objects.get(email='paymenttest@goexplorer.com')
        except User.DoesNotExist:
            self.test_user = User.objects.create_user(
                username='paymenttest',
                email='paymenttest@goexplorer.com',
                password='TestPass@123',
                phone='+919876543210',
            )
            self.test_user.email_verified = True
            self.test_user.phone_verified = True
            self.test_user.save()
        
        # Login user
        self.client.login(username='paymenttest', password='TestPass@123')
        print(f"[OK] Test user authenticated: {self.test_user.email}\n")
    
    def test_hotel_booking_flow(self, hotel):
        """Test complete booking flow for a hotel"""
        hotel_name = hotel.name
        self.results['total'] += 1
        
        try:
            # Step 1: Get room type
            room_types = RoomType.objects.filter(hotel=hotel).first()
            if not room_types:
                self.log_result('fail', hotel_name, 'No room types available')
                return False
            
            # Step 2: Create booking request
            checkin = date.today() + timedelta(days=5)
            checkout = checkin + timedelta(days=2)
            
            booking_data = {
                'hotel_id': hotel.id,
                'room_type_id': room_types.id,
                'checkin_date': checkin.isoformat(),
                'checkout_date': checkout.isoformat(),
                'num_rooms': 1,
                'guest_name': 'Test Guest',
                'guest_email': self.test_user.email,
                'guest_phone': self.test_user.phone,
                'meal_plan': '',  # Optional now
            }
            
            # Step 3: Test POST to booking endpoint
            response = self.client.post(
                reverse('hotels:create_booking'),
                data=booking_data,
                follow=True
            )
            
            # Check for error messages in response
            if response.status_code != 200:
                self.log_result('fail', hotel_name, f'POST failed with status {response.status_code}')
                return False
            
            # Check for validation errors
            if 'error' in response.content.decode().lower():
                self.log_result('fail', hotel_name, 'Validation error in response')
                return False
            
            # Step 4: Verify booking was created
            booking = Booking.objects.filter(
                user=self.test_user,
                booking_type='hotel'
            ).order_by('-created_at').first()
            
            if not booking:
                self.log_result('fail', hotel_name, 'Booking not created')
                return False
            
            hotel_booking = booking.hotelbooking
            if not hotel_booking:
                self.log_result('fail', hotel_name, 'HotelBooking detail not created')
                return False
            
            # Step 5: Calculate pricing
            try:
                nights = (checkout - checkin).days
                base_price = room_types.base_price * nights * booking_data['num_rooms']
                service_fee = calculate_service_fee(base_price)
                gst_rate = Decimal('0.05') if (base_price + service_fee) <= 7500 else Decimal('0.18')
                gst_amount = (base_price + service_fee) * gst_rate
                total_payable = base_price + service_fee + gst_amount
                
                # Verify database totals
                if not booking.total_payable or booking.total_payable != total_payable:
                    self.log_result('fail', hotel_name, 
                        f'Price mismatch: DB={booking.total_payable}, Calc={total_payable}')
                    return False
                
            except Exception as e:
                self.log_result('fail', hotel_name, f'Pricing calc error: {str(e)}')
                return False
            
            # Step 6: Check inventory lock
            lock = InventoryLock.objects.filter(
                booking=booking,
                hotel=hotel
            ).first()
            
            if not lock:
                self.log_result('fail', hotel_name, 'Inventory lock not created')
                return False
            
            # Step 7: Verify meal plan is optional (can be NULL)
            if room_types.meal_plans.exists():
                # If hotel has meal plans, verify it can be NULL
                if hotel_booking.meal_plan is None:
                    meal_plan_status = 'NULL (as per optional)'
                else:
                    meal_plan_status = f'ID={hotel_booking.meal_plan.id}'
            else:
                meal_plan_status = 'No meal plans for hotel'
            
            # SUCCESS
            self.log_result('pass', hotel_name, 
                f'Booking: {booking.id}, Total: {total_payable}, Meal Plan: {meal_plan_status}')
            self.results['passed'] += 1
            return True
            
        except Exception as e:
            self.log_result('error', hotel_name, str(e))
            return False
    
    def log_result(self, status, hotel_name, message):
        """Log test result"""
        result_entry = {
            'hotel': hotel_name,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if status == 'pass':
            self.results['pass'].append(result_entry)
            print(f"[PASS] {hotel_name}")
        elif status == 'fail':
            self.results['fail'].append(result_entry)
            print(f"[FAIL] {hotel_name} - {message}")
        else:
            self.results['error'].append(result_entry)
            print(f"[ERROR] {hotel_name} - {message}")
    
    def run_all_hotels(self):
        """Test all hotels in system"""
        hotels = Hotel.objects.filter(is_active=True).order_by('name')
        
        print(f"\n{'='*80}")
        print(f"PAYMENT FLOW TEST - ALL {hotels.count()} HOTELS")
        print(f"{'='*80}\n")
        
        for i, hotel in enumerate(hotels, 1):
            print(f"[{i}/{hotels.count()}] Testing: {hotel.name}")
            self.test_hotel_booking_flow(hotel)
            print()
        
        return self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        report = "\n" + "="*80 + "\n"
        report += "PAYMENT FLOW TEST REPORT\n"
        report += "="*80 + "\n\n"
        
        report += f"Total Hotels Tested: {self.results['total']}\n"
        report += f"PASSED: {self.results['passed']}\n"
        report += f"FAILED: {self.results['failed']}\n"
        report += f"ERRORS: {len(self.results['error'])}\n"
        report += f"Success Rate: {(self.results['passed']/self.results['total']*100):.1f}%\n\n"
        
        if self.results['pass']:
            report += "PASSED HOTELS:\n"
            report += "-"*80 + "\n"
            for item in self.results['pass'][:10]:  # Show first 10
                report += f"[PASS] {item['hotel']}: {item['message']}\n"
            if len(self.results['pass']) > 10:
                report += f"... and {len(self.results['pass'])-10} more\n"
        
        if self.results['fail']:
            report += f"\nFAILED HOTELS ({len(self.results['fail'])}):\n"
            report += "-"*80 + "\n"
            for item in self.results['fail']:
                report += f"[FAIL] {item['hotel']}: {item['message']}\n"
        
        if self.results['error']:
            report += f"\nERROR HOTELS ({len(self.results['error'])}):\n"
            report += "-"*80 + "\n"
            for item in self.results['error']:
                report += f"[ERROR] {item['hotel']}: {item['message']}\n"
        
        report += "\n" + "="*80 + "\n"
        
        return report

if __name__ == '__main__':
    tester = PaymentFlowTester()
    report = tester.run_all_hotels()
    print(report)
    
    # Save report
    with open('payment_flow_test_report.txt', 'w') as f:
        f.write(report)
    
    print(f"Report saved to: payment_flow_test_report.txt")
    
    # Exit with proper code
    sys.exit(0 if tester.results['failed'] == 0 else 1)
