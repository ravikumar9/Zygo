import { test, expect } from '@playwright/test';

test('Hotel booking E2E - Full flow to confirmation', async ({ page }) => {
  // 1. Login
  await page.goto('/users/login/');
  await page.fill('#id_email', 'wallet@test.com');
  await page.fill('#id_password', 'test123');
  await page.click('button:has-text("Login")');
  await page.waitForURL('/', { timeout: 10000 });
  console.log('✅ Login successful');
  
  // 2. Search hotels
  await page.goto('/');
  await page.selectOption('select[name="city_id"]', '3');
  await page.fill('input[name="checkin"]', '2026-02-15');
  await page.fill('input[name="checkout"]', '2026-02-17');
  await page.click('button:has-text("Search Hotels")');
  
  // 3. Wait for results and click first hotel
  await page.waitForSelector('.row.g-4', { timeout: 15000 });
  const hotelCards = page.locator('.col-md-4 .card');
  const count = await hotelCards.count();
  console.log(`✅ Found ${count} hotels`);
  
  await hotelCards.first().locator('a.btn-primary').click();
  await page.waitForURL(/\/hotels\/\d+/, { timeout: 10000 });
  console.log('✅ Hotel detail page loaded');
  
  // 4. Fill booking form on hotel detail page (Goibibo form)
  await page.fill('input[name="checkin_date"]', '2026-02-15');
  await page.fill('input[name="checkout_date"]', '2026-02-17');
  
  const roomSelect = page.locator('select[name="room_type"]');
  await roomSelect.selectOption({ index: 1 });
  console.log('✅ Room selected');
  
  // 5. Click Continue to Checkout
  await Promise.all([
    page.waitForURL(/\/hotels\/\d+\/book/, { timeout: 15000 }),
    page.click('button:has-text("Continue to Checkout")')
  ]);
  console.log('✅ Booking page loaded:', page.url());
  
  // 6. Fill guest details
  await page.waitForSelector('input[name="guest_name"], input[name="customer_name"]', { timeout: 10000 });
  await page.fill('input[name="guest_name"], input[name="customer_name"]', 'Test User E2E');
  await page.fill('input[name="guest_email"], input[name="customer_email"]', 'e2e@test.com');
  await page.fill('input[name="guest_phone"], input[name="customer_phone"]', '9876543210');
  console.log('✅ Guest details filled');
  
  // 7. Submit booking
  await Promise.all([
    page.waitForURL(/\/bookings\/.*\/confirm/, { timeout: 15000 }),
    page.click('button[type="submit"]')
  ]);
  
  console.log('✅✅✅ CONFIRMATION PAGE REACHED:', page.url());
  
  // 8. Verify confirmation page
  await expect(page.locator('h2, h1')).toBeVisible();
  
  // 9. Visual pause - MUST SEE THIS
  await page.waitForTimeout(5000);
  
  console.log('✅✅✅ BOOKING CONFIRMED - E2E COMPLETE ✅✅✅');
});
