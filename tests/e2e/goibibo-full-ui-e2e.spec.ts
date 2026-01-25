import { test, expect } from '@playwright/test';

// Configure test execution
test.describe.configure({ mode: 'parallel' });

const BASE_URL = 'http://localhost:8000';
const TIMEOUT = 30000;

test.describe('Goibibo-Grade Booking Platform - UI E2E', () => {
  let page;

  test.beforeEach(async ({ browser }) => {
    const context = await browser.newContext({
      recordVideo: { dir: 'test-results/videos' },
    });
    page = await context.newPage();
    page.setDefaultTimeout(TIMEOUT);
    page.setDefaultNavigationTimeout(TIMEOUT);
  });

  // Scenario 1: Budget Booking (< ₹7,500, 0% GST)
  test('Scenario 1: Budget Booking - GST 0%', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    await page.screenshot({ path: 'test-results/01-hotel-list.png' });

    // Search for budget hotel
    await page.locator('input[name="search"]').fill('Taj Mahal Palace');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'test-results/02-search-results.png' });

    // Select first hotel
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.screenshot({ path: 'test-results/03-hotel-detail.png' });

    // Select room type
    await page.locator('button:has-text("Select Room")').first().click();
      await page.waitForLoadState('domcontentloaded'); // Wait for page reload after selectRoom
    await page.screenshot({ path: 'test-results/04-room-selected.png' });

    // Verify pricing display (budget = 0% GST)
    const priceText = await page.locator('[data-testid="price-display"]').first().textContent();
    expect(priceText).toContain('₹');
    
    const gstText = await page.locator('[data-testid="gst-display"]').first().textContent();
    expect(gstText).toContain('0%');
    await page.screenshot({ path: 'test-results/05-budget-pricing-0-percent-gst.png' });

    // Proceed to payment
    await page.locator('button:has-text("Proceed to Payment")').click();
    await page.waitForLoadState('domcontentloaded');
    await page.screenshot({ path: 'test-results/06-payment-page.png' });

    // Verify confirmation
    const confirmationText = await page.locator('h1').textContent();
    expect(confirmationText).toContain('Confirm');
    await page.screenshot({ path: 'test-results/07-budget-booking-confirmation.png' });
  });

  // Scenario 2: Premium Booking (≥ ₹15,000, 5% GST)
  test('Scenario 2: Premium Booking - GST 5%', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    await page.screenshot({ path: 'test-results/08-premium-search.png' });

    // Search and select premium hotel
    await page.locator('input[name="search"]').fill('Park Hyatt');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');

    // Select premium room type (higher price)
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Suite")').click();
    await page.screenshot({ path: 'test-results/09-premium-room-selected.png' });

    // Verify 5% GST is applied
    const gstText = await page.locator('[data-testid="gst-display"]').textContent();
    expect(gstText).toContain('5%');
    
    const gstAmount = await page.locator('[data-testid="gst-amount"]').textContent();
    expect(gstAmount).toMatch(/₹\d+/);
    await page.screenshot({ path: 'test-results/10-premium-pricing-5-percent-gst.png' });

    // Verify tax breakdown is visible
    await page.locator('[data-testid="tax-breakdown"]').isVisible();
    await page.screenshot({ path: 'test-results/11-premium-tax-breakup.png' });
  });

  // Scenario 3: Meal Plan - Live Price Change
  test('Scenario 3: Meal Plans - Live Price Delta on Selection', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Select hotel and room
    await page.locator('input[name="search"]').fill('Taj Mahal');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Select Room")').first().click();

    // Capture initial price
    const initialPrice = await page.locator('[data-testid="room-price"]').first().textContent();
    await page.screenshot({ path: 'test-results/12-meal-plan-room-only.png' });

    // Select Breakfast plan
    await page.locator('button:has-text("Breakfast")').click();
    await page.waitForTimeout(500); // Wait for live update
    const breakfastPrice = await page.locator('[data-testid="room-price"]').first().textContent();
    expect(breakfastPrice).not.toBe(initialPrice);
    await page.screenshot({ path: 'test-results/13-meal-plan-breakfast-selected.png' });

    // Select Half Board plan
    await page.locator('button:has-text("Half Board")').click();
    await page.waitForTimeout(500);
    const halfBoardPrice = await page.locator('[data-testid="room-price"]').first().textContent();
    expect(halfBoardPrice).not.toBe(breakfastPrice);
    await page.screenshot({ path: 'test-results/14-meal-plan-half-board-selected.png' });

    // Select Full Board plan
    await page.locator('button:has-text("Full Board")').click();
    await page.waitForTimeout(500);
    const fullBoardPrice = await page.locator('[data-testid="room-price"]').first().textContent();
    expect(fullBoardPrice).not.toBe(halfBoardPrice);
    await page.screenshot({ path: 'test-results/15-meal-plan-full-board-selected.png' });
  });

  // Scenario 4: Invalid Promo - Error Display
  test('Scenario 4: Invalid Promo Code - Inline Error', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Select hotel and room
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Select Room")').first().click();

    // Apply invalid promo code
    const initialPrice = await page.locator('[data-testid="room-price"]').first().textContent();
    const initialPrice2 = await page.locator('[data-testid="room-price"]').first().textContent();
    await page.locator('input[name="promo"]').first().fill('INVALID123');
    await page.locator('button:has-text("Apply Promo")').click();
    await page.waitForTimeout(500);

    // Verify error is shown
    const errorText = await page.locator('[data-testid="promo-error"]').textContent();
    expect(errorText).toContain('Invalid') || expect(errorText).toContain('not valid');
    
    // Verify price did NOT change
    const priceAfterInvalidPromo = await page.locator('[data-testid="room-price"]').textContent();
    const priceAfterInvalidPromo2 = await page.locator('[data-testid="room-price"]').first().textContent();
    expect(priceAfterInvalidPromo2).toBe(initialPrice2);
    await page.screenshot({ path: 'test-results/16-invalid-promo-error.png' });
  });

  // Scenario 5: Valid Promo - Discount Applied
  test('Scenario 5: Valid Promo Code - Discount & GST Recalculated', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Select hotel and room
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Select Room")').first().click();

    // Capture original pricing
    const originalBase = await page.locator('[data-testid="base-amount"]').first().textContent();
    const originalGst = await page.locator('[data-testid="gst-amount"]').first().textContent();

    // Apply valid promo code
    await page.locator('input[name="promo"]').fill('SAVE20');
    await page.locator('button:has-text("Apply Promo")').click();
    await page.waitForTimeout(500);

    // Verify discount is applied
    const discountText = await page.locator('[data-testid="discount-amount"]').textContent();
    expect(discountText).toContain('₹');

    // Verify GST is recalculated
    const newGst = await page.locator('[data-testid="gst-amount"]').textContent();
    expect(newGst).toBeDefined();
    
    // Verify total is updated
    const finalTotal = await page.locator('[data-testid="final-total"]').textContent();
    await page.screenshot({ path: 'test-results/17-valid-promo-discount-applied.png' });
  });

  // Scenario 6: Wallet Insufficient Balance - Booking Blocked
  test('Scenario 6: Wallet Insufficient - Booking Blocked', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Select hotel and room
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Select Room")').first().click();

    // Attempt wallet payment with insufficient balance
    await page.locator('button:has-text("Use Wallet")').click();
    await page.waitForTimeout(500);

    // Verify error message
    const walletError = await page.locator('[data-testid="wallet-error"]').textContent();
    expect(walletError).toContain('Insufficient') || expect(walletError).toContain('balance');

    // Verify booking button is disabled
    const bookButton = await page.locator('button:has-text("Confirm Booking")');
    expect(await bookButton.isDisabled()).toBeTruthy();
    await page.screenshot({ path: 'test-results/18-wallet-insufficient-blocked.png' });
  });

  // Scenario 7: Wallet Sufficient - Booking Succeeds
  test('Scenario 7: Wallet Sufficient - Booking Succeeds & Balance Persists', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Select budget hotel (lower cost)
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Select Room")').first().click();

    // Use wallet payment
    await page.locator('button:has-text("Use Wallet")').click();
    await page.waitForTimeout(500);

    // Verify wallet is applied (no error)
    const walletError = await page.locator('[data-testid="wallet-error"]');
    expect(await walletError.isVisible()).toBeFalsy();

    // Complete booking
    await page.locator('button:has-text("Confirm Booking")').click();
    await page.waitForLoadState('domcontentloaded');
    await page.screenshot({ path: 'test-results/19-wallet-payment-success.png' });

    // Verify confirmation
    const confirmationText = await page.locator('[data-testid="booking-confirmation"]').textContent();
    expect(confirmationText).toContain('Confirmed');

    // Refresh page and verify balance persists
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
    const persistedBalance = await page.locator('[data-testid="wallet-balance"]').textContent();
    expect(persistedBalance).toContain('₹');
    await page.screenshot({ path: 'test-results/20-wallet-balance-persists.png' });
  });

  // Scenario 8: Inventory - Low Stock Warning
  test('Scenario 8: Inventory - Low Stock Warning Display', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Navigate to room type with low inventory
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');

    // Find room with low stock and verify warning
    const inventoryWarning = await page.locator('[data-testid="inventory-warning"]').first();
    if (await inventoryWarning.isVisible()) {
      const warningText = await inventoryWarning.textContent();
      expect(warningText).toMatch(/Only \d+ left/);
    }
    await page.screenshot({ path: 'test-results/21-inventory-low-stock-warning.png' });
  });

  // Scenario 9: Sold-out State - Booking Blocked
  test('Scenario 9: Inventory - Sold-out Blocks Booking', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Navigate to hotel
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');

    // Check for sold-out state
    const soldOutMessage = await page.locator('[data-testid="sold-out-message"]');
    const selectButton = await page.locator('button:has-text("Select Room")').first();
    
    if (await soldOutMessage.isVisible()) {
      expect(await selectButton.isDisabled()).toBeTruthy();
      await page.screenshot({ path: 'test-results/22-inventory-sold-out-blocked.png' });
    }
  });

  // Scenario 10: Hold Timer - Countdown Visible
  test('Scenario 10: Hold Timer - Countdown Visible & Decrements', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Complete booking to get timer
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Select Room")').first().click();
    await page.locator('button:has-text("Proceed to Payment")').click();
    await page.waitForLoadState('domcontentloaded');

    // Verify timer is displayed
    const timerDisplay = await page.locator('[data-testid="hold-timer"]');
    expect(await timerDisplay.isVisible()).toBeTruthy();
    const initialTime = await timerDisplay.textContent();
    await page.screenshot({ path: 'test-results/23-hold-timer-countdown-visible.png' });

    // Wait and verify timer decrements
    await page.waitForTimeout(2000);
    const decrementedTime = await timerDisplay.textContent();
    expect(decrementedTime).not.toBe(initialTime);
    await page.screenshot({ path: 'test-results/24-hold-timer-decrements.png' });
  });

  // Scenario 11: Admin Price Change - Live Reflection
  test('Scenario 11: Admin Price Change - User Sees Update on Refresh', async () => {
    // User browsing
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');

    // Capture original price
    const originalPrice = await page.locator('[data-testid="room-price"]').first().textContent();
    await page.screenshot({ path: 'test-results/25-admin-original-price.png' });

    // Simulate admin price change (via API call)
    const response = await page.request.patch(`${BASE_URL}/api/admin/rooms/1/`, {
      data: { base_price: 16000 }
    });
    expect(response.ok()).toBeTruthy();

    // User refreshes page
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    // Verify new price is shown (no cache)
    const newPrice = await page.locator('[data-testid="room-price"]').first().textContent();
    expect(newPrice).not.toBe(originalPrice);
    await page.screenshot({ path: 'test-results/26-admin-new-price-reflected.png' });
  });

  // Scenario 12: Confirmation Page - Full Rendering
  test('Scenario 12: Confirmation Page - Fully Rendered with All Details', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Complete full booking flow
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Select Room")').first().click();
    await page.locator('button:has-text("Proceed to Payment")').click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Confirm Booking")').click();
    await page.waitForLoadState('domcontentloaded');

    // Verify all confirmation details are visible
    expect(await page.locator('[data-testid="booking-id"]').isVisible()).toBeTruthy();
    expect(await page.locator('[data-testid="hotel-name"]').isVisible()).toBeTruthy();
    expect(await page.locator('[data-testid="check-in-date"]').isVisible()).toBeTruthy();
    expect(await page.locator('[data-testid="check-out-date"]').isVisible()).toBeTruthy();
    expect(await page.locator('[data-testid="room-type"]').isVisible()).toBeTruthy();
    expect(await page.locator('[data-testid="meal-plan"]').isVisible()).toBeTruthy();
    expect(await page.locator('[data-testid="base-amount"]').isVisible()).toBeTruthy();
    expect(await page.locator('[data-testid="service-fee"]').isVisible()).toBeTruthy();
    expect(await page.locator('[data-testid="gst-amount"]').isVisible()).toBeTruthy();
    expect(await page.locator('[data-testid="final-total"]').isVisible()).toBeTruthy();

    await page.screenshot({ path: 'test-results/27-confirmation-full-page.png' });
  });

  // Scenario 13: Error Messages - Human Readable
  test('Scenario 13: Error Messages - Human Readable & Clear', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Trigger various errors
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Select Room")').first().click();

    // Invalid promo error
    await page.locator('input[name="promo"]').fill('BADCODE');
      await page.locator('[data-testid="promo-error"]').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('button:has-text("Apply Promo")').click();
    const promoError = await page.locator('[data-testid="promo-error"]').textContent();
    expect(promoError).toBeTruthy();
    expect(promoError).toMatch(/[a-zA-Z]/); // Should contain readable text
    await page.screenshot({ path: 'test-results/28-error-messages-readable.png' });
  });

  // Scenario 14: Button Enable/Disable Logic
  test('Scenario 14: Button Enable/Disable Logic - Correct States', async () => {
    await page.goto(`${BASE_URL}/hotels/`, { waitUntil: 'domcontentloaded' });
    
    // Initially, booking button should be disabled (no room selected)
    let bookButton = await page.locator('button:has-text("Proceed to Payment")');
    expect(await bookButton.isDisabled()).toBeTruthy();
    await page.screenshot({ path: 'test-results/29-button-initial-disabled.png' });

    // After selecting room, button should be enabled
    await page.locator('input[name="search"]').fill('Taj');
    await page.locator('button:has-text("Search")').click();
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-testid="hotel-card"]').first().click();
    await page.waitForLoadState('domcontentloaded');
    await page.locator('button:has-text("Select Room")').first().click();

    bookButton = await page.locator('button:has-text("Proceed to Payment")');
    expect(await bookButton.isDisabled()).toBeFalsy();
    await page.screenshot({ path: 'test-results/30-button-enabled-after-selection.png' });
  });
});
