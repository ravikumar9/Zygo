import { test, expect } from '@playwright/test';

test('CORRECTED hotel booking E2E – visual confirmation required', async ({ page }) => {
  // 1. Login (REQUIRED for wallet access)
  await page.goto('/users/login/');
  await page.fill('#id_email', 'wallet@test.com');
  await page.fill('#id_password', 'test123');
  await page.click('button:has-text("Login")');
  
  // Wait for login to complete
  await page.waitForURL('/', { timeout: 10000 });
  
  // 2. Home page
  await page.goto('/');
  
  // 3. Search hotels
  await page.selectOption('select[name="city_id"]', '3');
  await page.fill('input[name="checkin"]', '2026-02-15');
  await page.fill('input[name="checkout"]', '2026-02-17');
  await page.click('button:has-text("Search Hotels")');
  
  // 4. Wait for search results container
  await page.waitForSelector('.row.g-4', { timeout: 15000 });
  
  // Log hotel cards count
  const hotelCards = page.locator('.col-md-4 .card');
  const count = await hotelCards.count();
  console.log('HOTELS FOUND:', count);
  
  if (count === 0) {
    await page.screenshot({ path: 'NO_HOTELS_FOUND.png', fullPage: true });
    throw new Error('No hotels rendered after search');
  }
  
  // 5. Click first hotel
  await hotelCards.first().locator('a.btn-primary').click();
  
  // 6. Wait for hotel detail page
  await page.waitForURL(/\/hotels\/\d+/, { timeout: 10000 });
  console.log('Hotel detail page loaded:', await page.title());
  
  // 7. Wait for booking form to load
  await page.waitForSelector('input[placeholder*="ID"], input[type="date"]', { timeout: 15000 });
  console.log('Booking form loaded');
  
  // 8. Fill check-in date (first date input)
  const dateInputs = page.locator('input[type="date"]');
  const dateCount = await dateInputs.count();
  console.log('Date inputs found:', dateCount);
  
  if (dateCount >= 2) {
    await dateInputs.nth(0).fill('2026-02-15');
    await dateInputs.nth(1).fill('2026-02-17');
  }
  
  // 9. Select room type from dropdown
  const roomSelect = page.locator('select').first();
  await page.waitForTimeout(500);
  
  const options = await roomSelect.locator('option').all();
  console.log('Room select options:', options.length);
  
  // Select second option (first is placeholder)
  await roomSelect.selectOption({ index: 1 });
  await page.waitForTimeout(1000);
  console.log('Room type selected');
  
  // 10. Fill guest details using exact IDs from booking-form.html
  await page.fill('#guest_name', 'Test User E2E');
  await page.fill('#guest_email', 'e2e@test.com');
  await page.fill('#guest_phone', '9876543210');
  console.log('Guest details filled');
  
  // 11. Wait for submit button to become enabled
  const submitButton = page.locator('button[type="submit"], input[type="submit"], button:has-text("Book"), button:has-text("Submit")');
  await expect(submitButton.first()).toBeEnabled({ timeout: 5000 });
  console.log('Submit button enabled');
  
  // 12. Submit form and wait for navigation  
  await Promise.all([
    page.waitForURL(/\/bookings\/.*\/confirm/, { timeout: 15000 }),
    submitButton.first().click()
  ]);
  
  console.log('✅ NAVIGATED TO:', page.url());
  
  // 13. HARD ASSERT: Booking confirmed page visible
  await expect(page.locator('text=Booking Confirmed, text=Booking Summary, h2')).toBeVisible();
  
  // 14. Visual pause - MUST SEE CONFIRMATION
  await page.waitForTimeout(5000);
  
  console.log('✅ BOOKING CONFIRMED - E2E COMPLETE');
});
