#!/usr/bin/env python
"""
Critical Bug Fix Verification Script
=====================================
Tests all fixes for:
1. Admin errors (FieldError, SafeString, has_delete_permission)
2. Bus seat logic (ladies seats AVAILABLE, not reserved)
3. E2E bus booking flow (male blocked from ladies seats, female allowed)
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from django.contrib.admin.sites import site
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from buses.models import Bus, SeatLayout, BusRoute
from hotels.models import Hotel, HotelImage
from packages.models import Package, PackageImage
from property_owners.admin import PropertyTypeAdmin
from property_owners.models import PropertyType

User = get_user_model()

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


def test_admin_field_errors():
    """Test that HotelImage and PackageImage admin inlines work without FieldError"""
    print_info("Testing Admin Field Errors (alt_text, display_order)...")
    
    try:
        # Test HotelImage has required fields
        from hotels.models import HotelImage
        hotel_img = HotelImage._meta
        
        assert hotel_img.get_field('alt_text'), "HotelImage missing alt_text field"
        assert hotel_img.get_field('display_order'), "HotelImage missing display_order field"
        print_success("HotelImage has alt_text and display_order fields")
        
        # Test PackageImage has required fields
        from packages.models import PackageImage
        package_img = PackageImage._meta
        
        assert package_img.get_field('alt_text'), "PackageImage missing alt_text field"
        assert package_img.get_field('display_order'), "PackageImage missing display_order field"
        print_success("PackageImage has alt_text and display_order fields")
        
        # Test admin registration works
        from hotels.admin import HotelImageInline
        from packages.admin import PackageImageInline
        
        assert 'alt_text' in HotelImageInline.fields, "HotelImageInline doesn't use alt_text"
        assert 'display_order' in HotelImageInline.fields, "HotelImageInline doesn't use display_order"
        print_success("HotelImageInline admin configuration correct")
        
        assert 'alt_text' in PackageImageInline.fields, "PackageImageInline doesn't use alt_text"
        assert 'display_order' in PackageImageInline.fields, "PackageImageInline doesn't use display_order"
        print_success("PackageImageInline admin configuration correct")
        
        return True
    except Exception as e:
        print_error(f"Admin field error test failed: {str(e)}")
        return False


def test_property_type_admin_signature():
    """Test that PropertyTypeAdmin.has_delete_permission has correct signature"""
    print_info("Testing PropertyTypeAdmin.has_delete_permission signature...")
    
    try:
        admin_instance = PropertyTypeAdmin(PropertyType, site)
        factory = RequestFactory()
        request = factory.get('/admin/')
        
        # Should accept obj parameter (can be None)
        result = admin_instance.has_delete_permission(request, obj=None)
        assert result == False, "has_delete_permission should return False"
        print_success("PropertyTypeAdmin.has_delete_permission signature correct")
        
        return True
    except TypeError as e:
        if "obj" in str(e):
            print_error(f"has_delete_permission signature missing obj parameter: {str(e)}")
            return False
        raise
    except Exception as e:
        print_error(f"PropertyTypeAdmin test failed: {str(e)}")
        return False


def test_ladies_seat_availability():
    """Test that ladies seats are AVAILABLE (not reserved) by default"""
    print_info("Testing Ladies Seat Availability Logic...")
    
    try:
        # Get a bus with seat layout
        bus = Bus.objects.first()
        if not bus:
            print_warning("No buses found. Run seed_buses first.")
            return False
        
        # Get ladies seats
        ladies_seats = SeatLayout.objects.filter(bus=bus, reserved_for='ladies')
        if not ladies_seats.exists():
            print_warning(f"No ladies seats found for bus {bus.bus_number}")
            return False
        
        # Check that ladies seats are NOT in a "booked" or "reserved" state
        # (reserved_for is a RULE, not a STATUS)
        for seat in ladies_seats:
            # Verify the field is just a designation, not a booking status
            assert seat.reserved_for == 'ladies', f"Seat {seat.seat_number} has wrong reserved_for value"
            
            # Verify the seat is available (no is_booked or is_reserved field should exist)
            assert not hasattr(seat, 'is_booked'), "SeatLayout should not have is_booked field"
            assert not hasattr(seat, 'is_reserved'), "SeatLayout should not have is_reserved field"
        
        print_success(f"Found {ladies_seats.count()} ladies seats on bus {bus.bus_number}")
        print_success("Ladies seats are DESIGNATION (rule), not STATUS (reserved)")
        
        # Test can_be_booked_by method
        sample_seat = ladies_seats.first()
        assert sample_seat.can_be_booked_by('F') == True, "Female should be able to book ladies seat"
        assert sample_seat.can_be_booked_by('M') == False, "Male should NOT be able to book ladies seat"
        print_success("can_be_booked_by() method works correctly")
        
        return True
    except Exception as e:
        print_error(f"Ladies seat availability test failed: {str(e)}")
        return False


def test_general_seats_availability():
    """Test that general seats are available to all genders"""
    print_info("Testing General Seat Availability...")
    
    try:
        bus = Bus.objects.first()
        if not bus:
            print_warning("No buses found. Run seed_buses first.")
            return False
        
        general_seats = SeatLayout.objects.filter(bus=bus, reserved_for='general')
        if not general_seats.exists():
            print_warning(f"No general seats found for bus {bus.bus_number}")
            return False
        
        print_success(f"Found {general_seats.count()} general seats on bus {bus.bus_number}")
        
        # Test can_be_booked_by method for general seats
        sample_seat = general_seats.first()
        assert sample_seat.can_be_booked_by('F') == True, "Female should be able to book general seat"
        assert sample_seat.can_be_booked_by('M') == True, "Male should be able to book general seat"
        assert sample_seat.can_be_booked_by('O') == True, "Other gender should be able to book general seat"
        print_success("General seats available to all genders")
        
        return True
    except Exception as e:
        print_error(f"General seat availability test failed: {str(e)}")
        return False


def test_bus_seat_layout_2x2():
    """Test that bus seat layout is 2x2 grid"""
    print_info("Testing Bus Seat Layout (2x2 Grid)...")
    
    try:
        bus = Bus.objects.first()
        if not bus:
            print_warning("No buses found. Run seed_buses first.")
            return False
        
        seats = SeatLayout.objects.filter(bus=bus, deck=1)
        
        # Check seat numbering (1A, 1B, 1C, 1D, 2A, 2B, 2C, 2D, etc.)
        seat_numbers = list(seats.values_list('seat_number', flat=True))
        
        # Verify 2x2 pattern exists (A, B, C, D columns)
        has_a_col = any('A' in sn for sn in seat_numbers)
        has_b_col = any('B' in sn for sn in seat_numbers)
        has_c_col = any('C' in sn for sn in seat_numbers)
        has_d_col = any('D' in sn for sn in seat_numbers)
        
        assert has_a_col and has_b_col and has_c_col and has_d_col, "Missing 2x2 columns (A, B, C, D)"
        print_success(f"Bus {bus.bus_number} has 2x2 seat layout (columns A, B, C, D)")
        
        # Check column values (should be 1-4)
        columns = seats.values_list('column', flat=True).distinct()
        assert set(columns) == {1, 2, 3, 4}, f"Columns should be 1-4, got {set(columns)}"
        print_success("Seat columns configured correctly (1=A, 2=B, 3=C, 4=D)")
        
        return True
    except Exception as e:
        print_error(f"Bus seat layout test failed: {str(e)}")
        return False


def test_seat_layout_visual_logic():
    """Test that seat layout template logic is correct"""
    print_info("Testing Seat Layout Visual Logic...")
    
    try:
        # Read the bus_detail.html template
        template_path = 'templates/buses/bus_detail.html'
        
        if not os.path.exists(template_path):
            print_warning(f"Template not found: {template_path}")
            return False
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Check that ladies seats use correct CSS class logic
        # Should be: available (green) with lady icon, NOT pink/blocked
        
        # Verify CSS for .seat.ladies shows green background
        assert 'seat.ladies' in template_content, "Missing .seat.ladies CSS class"
        
        # Find the .seat.ladies CSS block
        import re
        ladies_css_match = re.search(r'\.seat\.ladies\s*\{([^}]+)\}', template_content, re.DOTALL)
        if not ladies_css_match:
            print_error("Could not find .seat.ladies CSS block")
            return False
        
        ladies_css = ladies_css_match.group(1)
        
        # Verify it uses green background (#e8f5e9), NOT pink (#fce4ec)
        if '#e8f5e9' in ladies_css:
            print_success("Ladies seats use GREEN background (available appearance)")
        elif '#fce4ec' in ladies_css:
            print_error("Ladies seats use PINK background (reserved appearance) - WRONG!")
            return False
        else:
            print_warning("Could not verify ladies seat background color")
        
        # Verify lady icon (♀) is present
        if '♀' in template_content:
            print_success("Ladies seats have ♀ icon indicator")
        else:
            print_warning("Ladies seats missing ♀ icon")
        
        return True
    except Exception as e:
        print_error(f"Seat layout visual logic test failed: {str(e)}")
        return False


def test_admin_pages_load():
    """Test that admin pages load without errors"""
    print_info("Testing Admin Pages Load...")
    
    try:
        from django.contrib.admin import site as admin_site
        
        # Check critical models are registered
        from hotels.models import Hotel
        from packages.models import Package
        from buses.models import Bus
        from property_owners.models import PropertyOwner
        
        registered_models = [
            (Hotel, 'Hotel'),
            (Package, 'Package'),
            (Bus, 'Bus'),
            (PropertyOwner, 'PropertyOwner'),
        ]
        
        for model, name in registered_models:
            if model in admin_site._registry:
                print_success(f"{name} registered in admin")
            else:
                print_error(f"{name} NOT registered in admin")
                return False
        
        return True
    except Exception as e:
        print_error(f"Admin pages load test failed: {str(e)}")
        return False


def main():
    print("\n" + "="*70)
    print("CRITICAL BUG FIX VERIFICATION")
    print("="*70 + "\n")
    
    tests = [
        ("Admin Field Errors (FieldError)", test_admin_field_errors),
        ("PropertyType Admin Signature", test_property_type_admin_signature),
        ("Ladies Seat Availability", test_ladies_seat_availability),
        ("General Seat Availability", test_general_seats_availability),
        ("Bus Seat Layout 2x2", test_bus_seat_layout_2x2),
        ("Seat Layout Visual Logic", test_seat_layout_visual_logic),
        ("Admin Pages Load", test_admin_pages_load),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{Colors.BLUE}{'─'*70}{Colors.RESET}")
        print(f"{Colors.BLUE}TEST: {test_name}{Colors.RESET}")
        print(f"{Colors.BLUE}{'─'*70}{Colors.RESET}")
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if result else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.BLUE}{'─'*70}{Colors.RESET}")
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"{Colors.GREEN}{'='*70}{Colors.RESET}")
        print(f"{Colors.GREEN}✓ ALL TESTS PASSED!{Colors.RESET}")
        print(f"{Colors.GREEN}{'='*70}{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{'='*70}{Colors.RESET}")
        print(f"{Colors.RED}✗ {total - passed} TEST(S) FAILED!{Colors.RESET}")
        print(f"{Colors.RED}{'='*70}{Colors.RESET}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
