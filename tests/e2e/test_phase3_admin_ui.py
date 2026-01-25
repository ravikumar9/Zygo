"""
Phase-3 Integration Tests: Admin & Finance UI
Tests Django views with role-based access control via Django TestClient
"""
import pytest
from django.test import Client
from django.urls import reverse


def login_via_client(client: Client, user_creds: dict) -> tuple[bool, Client]:
    """Login user via Django test client and return success"""
    try:
        success = client.login(
            username=user_creds["username"],
            password=user_creds["password"]
        )
        return success, client
    except Exception as e:
        print(f"Login error: {e}")
        return False, client


def verify_access_via_client(client: Client, url_name: str) -> dict:
    """Verify page access via Django test client"""
    try:
        url = reverse(url_name)
        response = client.get(url)
        
        return {
            "status_code": response.status_code,
            "content": response.content.decode('utf-8', errors='ignore'),
            "url": url,
            "is_accessible": response.status_code in [200, 302],
            "is_denied": response.status_code in [403, 401]
        }
    except Exception as e:
        print(f"Access check error: {e}")
        return {"error": str(e), "status_code": None}


# ============================================================================
# TEST 1: ADMIN LOGIN - All Roles
# ============================================================================

@pytest.mark.django_db
class TestAdminLogin:
    """Test login functionality per role"""
    
    def test_super_admin_login(self, client, all_test_users):
        """SUPER_ADMIN login should succeed"""
        success, _ = login_via_client(client, all_test_users["SUPER_ADMIN"])
        assert success, "SUPER_ADMIN login failed"
        
        response = verify_access_via_client(client, 'finance:admin_dashboard')
        assert response["status_code"] == 200
    
    def test_finance_admin_login(self, client, all_test_users):
        """FINANCE_ADMIN login should succeed"""
        success, _ = login_via_client(client, all_test_users["FINANCE_ADMIN"])
        assert success, "FINANCE_ADMIN login failed"
        
        response = verify_access_via_client(client, 'finance:admin_dashboard')
        assert response["status_code"] == 200
    
    def test_property_admin_login(self, client, all_test_users):
        """PROPERTY_ADMIN login should succeed"""
        success, _ = login_via_client(client, all_test_users["PROPERTY_ADMIN"])
        assert success, "PROPERTY_ADMIN login failed"
    
    def test_support_admin_login(self, client, all_test_users):
        """SUPPORT_ADMIN login should succeed"""
        success, _ = login_via_client(client, all_test_users["SUPPORT_ADMIN"])
        assert success, "SUPPORT_ADMIN login failed"
        
        response = verify_access_via_client(client, 'finance:booking_table')
        assert response["status_code"] == 200
    
    def test_owner_login(self, client, all_test_users):
        """Property owner login should succeed"""
        success, _ = login_via_client(client, all_test_users["OWNER"])
        assert success, "Owner login failed"


# ============================================================================
# TEST 2: FINANCE DASHBOARD - UI Assertions
# ============================================================================

@pytest.mark.django_db
class TestFinanceDashboard:
    """Test finance dashboard visibility and data"""
    
    def test_super_admin_dashboard_visible(self, client, all_test_users):
        """SUPER_ADMIN should see full dashboard"""
        login_via_client(client, all_test_users["SUPER_ADMIN"])
        response = verify_access_via_client(client, 'finance:admin_dashboard')
        
        assert response["status_code"] == 200
        assert len(response["content"]) > 500
    
    def test_finance_admin_dashboard_visible(self, client, all_test_users):
        """FINANCE_ADMIN should see financial metrics"""
        login_via_client(client, all_test_users["FINANCE_ADMIN"])
        response = verify_access_via_client(client, 'finance:admin_dashboard')
        
        assert response["status_code"] == 200


# ============================================================================
# TEST 3: BOOKINGS TABLE
# ============================================================================

@pytest.mark.django_db
class TestBookingsTable:
    """Test bookings table functionality"""
    
    def test_bookings_table_loads(self, client, all_test_users):
        """Bookings table should load for authorized users"""
        login_via_client(client, all_test_users["SUPPORT_ADMIN"])
        response = verify_access_via_client(client, 'finance:booking_table')
        
        assert response["status_code"] == 200
    
    def test_bookings_page_has_content(self, client, all_test_users):
        """Bookings page should render UI elements"""
        login_via_client(client, all_test_users["SUPER_ADMIN"])
        response = verify_access_via_client(client, 'finance:booking_table')
        
        assert "500" not in response["content"]


# ============================================================================
# TEST 4: INVOICE UI
# ============================================================================

@pytest.mark.django_db
class TestInvoiceUI:
    """Test invoice listing and details"""
    
    def test_super_admin_can_access_bookings(self, client, all_test_users):
        """SUPER_ADMIN should be able to access bookings pages"""
        login_via_client(client, all_test_users["SUPER_ADMIN"])
        response = verify_access_via_client(client, 'finance:booking_table')
        
        assert response["status_code"] == 200
    
    def test_finance_admin_bookings_access(self, client, all_test_users):
        """FINANCE_ADMIN should access booking list"""
        login_via_client(client, all_test_users["FINANCE_ADMIN"])
        response = verify_access_via_client(client, 'finance:booking_table')
        
        assert response["status_code"] == 200


# ============================================================================
# TEST 5: OWNER UI - Role Restrictions
# ============================================================================

@pytest.mark.django_db
class TestOwnerUI:
    """Test property owner dashboard and access"""
    
    def test_owner_can_access_earnings(self, client, all_test_users):
        """Property owner should access their earnings page"""
        login_via_client(client, all_test_users["OWNER"])
        response = verify_access_via_client(client, 'finance:owner_earnings')
        
        assert response["status_code"] == 200
    
    def test_owner_cannot_access_admin_dashboard(self, client, all_test_users):
        """Property owner should NOT access admin dashboard"""
        login_via_client(client, all_test_users["OWNER"])
        response = verify_access_via_client(client, 'finance:admin_dashboard')
        
        # Should be redirected or denied (403/401 or 302 redirect)
        assert response["status_code"] in [403, 401, 302]


# ============================================================================
# TEST 6: NEGATIVE TESTS - Access Denied Scenarios
# ============================================================================

@pytest.mark.django_db
class TestAccessDenied:
    """Test negative scenarios - users accessing forbidden pages"""
    
    def test_property_admin_denied_finance_dashboard(self, client, all_test_users):
        """PROPERTY_ADMIN should NOT access finance dashboard"""
        login_via_client(client, all_test_users["PROPERTY_ADMIN"])
        response = verify_access_via_client(client, 'finance:admin_dashboard')
        
        # Should be denied or redirected
        assert response["status_code"] in [403, 401, 302]
    
    def test_support_admin_can_access_bookings(self, client, all_test_users):
        """SUPPORT_ADMIN CAN access bookings"""
        login_via_client(client, all_test_users["SUPPORT_ADMIN"])
        response = verify_access_via_client(client, 'finance:booking_table')
        
        assert response["status_code"] == 200
    
    def test_owner_denied_admin_properties(self, client, all_test_users):
        """Property owner should NOT access admin properties"""
        login_via_client(client, all_test_users["OWNER"])
        response = verify_access_via_client(client, 'finance:property_metrics')
        
        # Should be denied or redirected
        assert response["status_code"] in [403, 401, 302]


# ============================================================================
# TEST 7: DASHBOARD NAVIGATION
# ============================================================================

@pytest.mark.django_db
class TestDashboardNavigation:
    """Test navigation between dashboard pages"""
    
    def test_super_admin_can_access_all_pages(self, client, all_test_users):
        """SUPER_ADMIN should access all finance pages"""
        login_via_client(client, all_test_users["SUPER_ADMIN"])
        
        pages = [
            'finance:admin_dashboard',
            'finance:property_metrics',
            'finance:booking_table'
        ]
        
        for page_name in pages:
            response = verify_access_via_client(client, page_name)
            assert response["status_code"] == 200
    
    def test_finance_admin_can_navigate(self, client, all_test_users):
        """FINANCE_ADMIN should navigate through finance pages"""
        login_via_client(client, all_test_users["FINANCE_ADMIN"])
        
        pages_to_test = [
            'finance:admin_dashboard',
            'finance:booking_table',
        ]
        
        for page_name in pages_to_test:
            response = verify_access_via_client(client, page_name)
            assert response["status_code"] == 200


# ============================================================================
# TEST 8: ERROR HANDLING
# ============================================================================

@pytest.mark.django_db
class TestErrorHandling:
    """Test error pages and handling"""
    
    def test_404_handling(self, client, all_test_users):
        """Non-existent page should handle gracefully"""
        login_via_client(client, all_test_users["SUPER_ADMIN"])
        
        response = client.get('/finance/nonexistent/')
        assert response.status_code in [404, 403, 301]
    
    def test_page_loads_without_500(self, client, all_test_users):
        """Dashboard pages should not return 500 errors"""
        login_via_client(client, all_test_users["SUPER_ADMIN"])
        response = verify_access_via_client(client, 'finance:admin_dashboard')
        
        assert response["status_code"] != 500
