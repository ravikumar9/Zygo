import { test, expect } from '@playwright/test';

test('FULL hotel booking E2E – visible UI', async ({ page }) => {
  // 1. Login (REQUIRED)
  await page.goto('/login/');
  await page.fill('#id_username', 'walletuser');
  await page.fill('#id_password', 'test123');
  await page.click('button[type="submit"]');

  // 2. Home
  await page.goto('/');

  // 3. Search hotel
  await page.selectOption('select[name="city_id"]', '3');
  await page.fill('input[name="checkin"]', '2026-02-15');
  await page.fill('input[name="checkout"]', '2026-02-17');
  await page.click('button:has-text("Search Hotels")');

  // 4. Open hotel
  await page.click('.hotel-card >> nth=0');

  // 5. Scroll to rooms
  await page.locator('#available-rooms').scrollIntoViewIfNeeded();

  // 6. Select meal plan
  const meal = page.locator('select.meal-plan').first();
  await meal.selectOption({ label: 'Breakfast Included' });

  // 7. Select room
  await page.click('button:has-text("Select Room")');

  // 8. Confirm booking (WAIT!)
  await Promise.all([
    page.waitForURL(/bookings\/.*\/confirm/),
    page.click('button:has-text("Confirm Booking")')
  ]);

  // 9. ASSERT confirmation UI
  await expect(page.locator('text=Booking Confirmed')).toBeVisible();

  // 10. Pause so YOU can see it
  await page.waitForTimeout(5000);
});
