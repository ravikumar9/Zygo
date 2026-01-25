const { test, expect } = require('@playwright/test');

test('Complete hotel booking E2E flow', async ({ page }) => {
  // 1. Login
  await page.goto('/users/login/');
  await page.fill('#id_email', 'wallet@test.com');
  await page.fill('#id_password', 'test123');
  await page.click('button[type="submit"]');
  await page.waitForLoadState('networkidle');
  console.log('✅ Login successful');

  // 2. Search for hotels
  await page.goto('/hotels/?city_id=3&checkin=2026-02-15&checkout=2026-02-17');
  await page.waitForSelector('.hotel-card, .card', { timeout: 10000 });
  const hotels = await page.$$('.hotel-card, .card');
  console.log(`✅ Found ${hotels.length} hotels`);
  expect(hotels.length).toBeGreaterThan(0);

  // 3. Click first hotel (use "View & Book" link)
  await page.click('a:has-text("View & Book")');
  await page.waitForLoadState('networkidle');
  console.log('✅ Hotel detail page loaded');

  // 4. Wait for booking form to be ready
  await page.waitForSelector('#hotel-booking-form', { timeout: 10000 });
  
  // 5. Fill check-in and check-out dates
  await page.fill('#check_in', '2026-02-15');
  await page.fill('#check_out', '2026-02-17');
  console.log('✅ Dates filled');

  // 6. Select room type (required for button to enable)
  await page.selectOption('#room_type_id', { index: 1 });
  console.log('✅ Room type selected');

  // 7. Wait for button to become enabled
  await page.waitForFunction(() => {
    const btn = document.getElementById('book-btn');
    return btn && !btn.disabled;
  }, { timeout: 5000 });
  console.log('✅ Button enabled after room selection');

  // 8. Fill guest details
  await page.fill('#guest_name', 'Test User E2E');
  await page.fill('#guest_email', 'e2e@test.com');
  await page.fill('#guest_phone', '9876543210');
  console.log('✅ Guest details filled');

  // 9. Submit booking
  const [response] = await Promise.all([
    page.waitForResponse(response => response.url().includes('/book/') && response.status() === 200),
    page.click('#book-btn')
  ]);
  console.log('✅ Booking submitted');

  // 10. Wait for redirect to confirmation page
  await page.waitForURL(/\/bookings\/.*\/confirm/, { timeout: 15000 });
  console.log(`✅ Redirected to: ${page.url()}`);

  // 11. Verify confirmation page
  await expect(page.locator('text=/booking confirmed|booking summary/i')).toBeVisible({ timeout: 10000 });
  console.log('✅ Booking confirmed page visible');

  // 12. Pause for visual verification
  await page.waitForTimeout(5000);
});
