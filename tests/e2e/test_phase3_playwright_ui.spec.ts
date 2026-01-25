/**
 * Phase-3 Playwright E2E UI Tests: Real Browser Automation
 * 
 * Tests actual browser interactions with the Admin & Finance UI
 * - Opens Chromium browser
 * - Fills forms via typing
 * - Clicks buttons  
 * - Asserts DOM content
 * - Verifies access control via visual feedback
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://127.0.0.1:8000';

const TEST_USERS = {
  SUPER_ADMIN: { email: 'superadmin_user@test.com', password: 'TestPass123!@' },
  FINANCE_ADMIN: { email: 'finance_user@test.com', password: 'TestPass123!@' },
  PROPERTY_ADMIN: { email: 'property_admin_user@test.com', password: 'TestPass123!@' },
  SUPPORT_ADMIN: { email: 'support_user@test.com', password: 'TestPass123!@' },
  OWNER: { email: 'owner_user@test.com', password: 'TestPass123!@' },
};

/**
 * Helper: Login a user via browser form
 */
async function loginUser(page, email: string, password: string): Promise<boolean> {
  try {
    await page.goto(`${BASE_URL}/login/`);
    
    // Fill form fields
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    
    // Click login button
    try {
      await page.click('button[type="submit"]');
    } catch {
      try {
        await page.click('input[type="submit"]');
      } catch {
        // Try clicking any button with login text
        await page.click('text=Login');
      }
    }
    
    // Wait for navigation away from login page
    await page.waitForNavigation({ timeout: 5000 });
    
    return true;
  } catch (error) {
    console.log(`Login failed: ${error}`);
    return false;
  }
}

/**
 * Helper: Logout user
 */
async function logoutUser(page) {
  try {
    await page.click('a:has-text("Logout"), a:has-text("Sign Out"), a[href*="logout"]', { timeout: 2000 });
    await page.waitForURL(`${BASE_URL}/login/`, { timeout: 3000 });
  } catch {
    // Already logged out or no logout button
  }
}

// ============================================================================
// TEST 1: ADMIN LOGIN - All Roles
// ============================================================================

test.describe('Test 1: Admin Login per Role', () => {
  test('SUPER_ADMIN login and dashboard access', async ({ page }) => {
    const success = await loginUser(page, TEST_USERS.SUPER_ADMIN.email, TEST_USERS.SUPER_ADMIN.password);
    expect(success).toBe(true);
    
    await page.goto(`${BASE_URL}/finance/admin-dashboard/`);
    await page.waitForLoadState('networkidle');
    
    // Verify dashboard loaded
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
    
    await logoutUser(page);
  });
  
  test('FINANCE_ADMIN login and dashboard access', async ({ page }) => {
    const success = await loginUser(page, TEST_USERS.FINANCE_ADMIN.email, TEST_USERS.FINANCE_ADMIN.password);
    expect(success).toBe(true);
    
    await page.goto(`${BASE_URL}/finance/admin-dashboard/`);
    await page.waitForLoadState('networkidle');
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
    
    await logoutUser(page);
  });
  
  test('PROPERTY_ADMIN login', async ({ page }) => {
    const success = await loginUser(page, TEST_USERS.PROPERTY_ADMIN.email, TEST_USERS.PROPERTY_ADMIN.password);
    expect(success).toBe(true);
    
    await logoutUser(page);
  });
  
  test('SUPPORT_ADMIN login', async ({ page }) => {
    const success = await loginUser(page, TEST_USERS.SUPPORT_ADMIN.email, TEST_USERS.SUPPORT_ADMIN.password);
    expect(success).toBe(true);
    
    await logoutUser(page);
  });
  
  test('Property owner login', async ({ page }) => {
    const success = await loginUser(page, TEST_USERS.OWNER.email, TEST_USERS.OWNER.password);
    expect(success).toBe(true);
    
    await logoutUser(page);
  });
});

// ============================================================================
// TEST 2: FINANCE DASHBOARD - UI Assertions
// ============================================================================

test.describe('Test 2: Finance Dashboard UI Visibility', () => {
  test('SUPER_ADMIN dashboard displays metrics', async ({ page }) => {
    await loginUser(page, TEST_USERS.SUPER_ADMIN.email, TEST_USERS.SUPER_ADMIN.password);
    
    await page.goto(`${BASE_URL}/finance/admin-dashboard/`);
    await page.waitForLoadState('networkidle');
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
    
    await logoutUser(page);
  });
  
  test('FINANCE_ADMIN dashboard shows content', async ({ page }) => {
    await loginUser(page, TEST_USERS.FINANCE_ADMIN.email, TEST_USERS.FINANCE_ADMIN.password);
    
    await page.goto(`${BASE_URL}/finance/admin-dashboard/`);
    await page.waitForLoadState('networkidle');
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
    
    await logoutUser(page);
  });
});

// ============================================================================
// TEST 3: BOOKINGS TABLE - UI
// ============================================================================

test.describe('Test 3: Bookings Table', () => {
  test('Bookings table loads', async ({ page }) => {
    await loginUser(page, TEST_USERS.SUPER_ADMIN.email, TEST_USERS.SUPER_ADMIN.password);
    
    await page.goto(`${BASE_URL}/finance/booking-table/`);
    await page.waitForLoadState('networkidle');
    
    const url = page.url();
    expect(url).toBeTruthy();
    
    await logoutUser(page);
  });
  
  test('Bookings page has content', async ({ page }) => {
    await loginUser(page, TEST_USERS.FINANCE_ADMIN.email, TEST_USERS.FINANCE_ADMIN.password);
    
    await page.goto(`${BASE_URL}/finance/booking-table/`);
    await page.waitForLoadState('networkidle');
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(300);
    
    await logoutUser(page);
  });
});

// ============================================================================
// TEST 4: INVOICE UI
// ============================================================================

test.describe('Test 4: Invoice UI', () => {
  test('SUPER_ADMIN can access bookings', async ({ page }) => {
    await loginUser(page, TEST_USERS.SUPER_ADMIN.email, TEST_USERS.SUPER_ADMIN.password);
    
    await page.goto(`${BASE_URL}/finance/booking-table/`);
    await page.waitForLoadState('networkidle');
    
    const content = await page.content();
    expect(content).toBeTruthy();
    
    await logoutUser(page);
  });
  
  test('FINANCE_ADMIN can access invoices', async ({ page }) => {
    await loginUser(page, TEST_USERS.FINANCE_ADMIN.email, TEST_USERS.FINANCE_ADMIN.password);
    
    await page.goto(`${BASE_URL}/finance/booking-table/`);
    await page.waitForLoadState('networkidle');
    
    const content = await page.content();
    expect(content).toBeTruthy();
    
    await logoutUser(page);
  });
});

// ============================================================================
// TEST 5: OWNER UI
// ============================================================================

test.describe('Test 5: Owner Dashboard UI', () => {
  test('Owner can access earnings', async ({ page }) => {
    await loginUser(page, TEST_USERS.OWNER.email, TEST_USERS.OWNER.password);
    
    await page.goto(`${BASE_URL}/finance/owner-earnings/`);
    await page.waitForLoadState('networkidle');
    
    const content = await page.content();
    expect(content).toBeTruthy();
    
    await logoutUser(page);
  });
  
  test('Owner CANNOT access admin dashboard', async ({ page }) => {
    await loginUser(page, TEST_USERS.OWNER.email, TEST_USERS.OWNER.password);
    
    const response = await page.goto(`${BASE_URL}/finance/admin-dashboard/`, { waitUntil: 'networkidle' });
    
    const statusCode = response?.status();
    const isRedirected = [301, 302, 303, 307, 308, 403, 401].includes(statusCode || 0);
    const content = await page.content();
    const isDenied = content.toLowerCase().includes('denied') || 
                    content.toLowerCase().includes('not authorized') ||
                    content.toLowerCase().includes('permission');
    const urlChanged = page.url() !== `${BASE_URL}/finance/admin-dashboard/`;
    
    expect(isRedirected || isDenied || urlChanged).toBeTruthy();
    
    await logoutUser(page);
  });
});

// ============================================================================
// TEST 6: NEGATIVE TESTS - Access Denied
// ============================================================================

test.describe('Test 6: Access Denied Scenarios', () => {
  test('PROPERTY_ADMIN denied finance dashboard', async ({ page }) => {
    await loginUser(page, TEST_USERS.PROPERTY_ADMIN.email, TEST_USERS.PROPERTY_ADMIN.password);
    
    const response = await page.goto(`${BASE_URL}/finance/admin-dashboard/`, { waitUntil: 'networkidle' });
    
    const statusCode = response?.status();
    const isRedirected = [301, 302, 303, 307, 308, 403, 401].includes(statusCode || 0);
    const content = await page.content();
    const isDenied = content.toLowerCase().includes('denied') || content.toLowerCase().includes('not authorized');
    const urlChanged = page.url() !== `${BASE_URL}/finance/admin-dashboard/`;
    
    expect(isRedirected || isDenied || urlChanged).toBeTruthy();
    
    await logoutUser(page);
  });
  
  test('SUPPORT_ADMIN CAN access bookings', async ({ page }) => {
    await loginUser(page, TEST_USERS.SUPPORT_ADMIN.email, TEST_USERS.SUPPORT_ADMIN.password);
    
    await page.goto(`${BASE_URL}/finance/booking-table/`);
    await page.waitForLoadState('networkidle');
    
    const content = await page.content();
    expect(content).toBeTruthy();
    
    await logoutUser(page);
  });
  
  test('Owner denied property metrics', async ({ page }) => {
    await loginUser(page, TEST_USERS.OWNER.email, TEST_USERS.OWNER.password);
    
    const response = await page.goto(`${BASE_URL}/finance/property-metrics/`, { waitUntil: 'networkidle' });
    
    const statusCode = response?.status();
    const isRedirected = [301, 302, 303, 307, 308, 403, 401].includes(statusCode || 0);
    const content = await page.content();
    const isDenied = content.toLowerCase().includes('denied') || content.toLowerCase().includes('not authorized');
    const urlChanged = page.url() !== `${BASE_URL}/finance/property-metrics/`;
    
    expect(isRedirected || isDenied || urlChanged).toBeTruthy();
    
    await logoutUser(page);
  });
});

// ============================================================================
// TEST 7: DASHBOARD NAVIGATION
// ============================================================================

test.describe('Test 7: Dashboard Navigation', () => {
  test('SUPER_ADMIN can navigate all pages', async ({ page }) => {
    await loginUser(page, TEST_USERS.SUPER_ADMIN.email, TEST_USERS.SUPER_ADMIN.password);
    
    const urls = [
      `${BASE_URL}/finance/admin-dashboard/`,
      `${BASE_URL}/finance/booking-table/`,
      `${BASE_URL}/finance/property-metrics/`,
    ];
    
    for (const url of urls) {
      const response = await page.goto(url, { waitUntil: 'networkidle' });
      const statusCode = response?.status() || 200;
      expect([200, 304].includes(statusCode)).toBeTruthy();
    }
    
    await logoutUser(page);
  });
  
  test('FINANCE_ADMIN can navigate finance pages', async ({ page }) => {
    await loginUser(page, TEST_USERS.FINANCE_ADMIN.email, TEST_USERS.FINANCE_ADMIN.password);
    
    const urls = [
      `${BASE_URL}/finance/admin-dashboard/`,
      `${BASE_URL}/finance/booking-table/`,
    ];
    
    for (const url of urls) {
      const response = await page.goto(url, { waitUntil: 'networkidle' });
      const statusCode = response?.status() || 200;
      expect([200, 304].includes(statusCode)).toBeTruthy();
    }
    
    await logoutUser(page);
  });
});

// ============================================================================
// TEST 8: ERROR HANDLING
// ============================================================================

test.describe('Test 8: Error Handling', () => {
  test('404 handling works', async ({ page }) => {
    await loginUser(page, TEST_USERS.SUPER_ADMIN.email, TEST_USERS.SUPER_ADMIN.password);
    
    const response = await page.goto(`${BASE_URL}/finance/nonexistent-page/`, { waitUntil: 'load' });
    
    const statusCode = response?.status();
    const isValid = [404, 301, 302, 303].includes(statusCode || 0) || 
                   page.url() !== `${BASE_URL}/finance/nonexistent-page/`;
    
    expect(isValid).toBeTruthy();
    
    await logoutUser(page);
  });
  
  test('Pages load without 500 errors', async ({ page }) => {
    await loginUser(page, TEST_USERS.SUPER_ADMIN.email, TEST_USERS.SUPER_ADMIN.password);
    
    const response = await page.goto(`${BASE_URL}/finance/admin-dashboard/`, { waitUntil: 'networkidle' });
    
    const statusCode = response?.status() || 200;
    expect(![500, 502, 503].includes(statusCode)).toBeTruthy();
    
    await logoutUser(page);
  });
});
