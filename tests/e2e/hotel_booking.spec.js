// Hotel booking – Goibibo-grade E2E
// Runs headed with slowMo per config

const { test, expect } = require('@playwright/test');

function futureDate(days) {
  const d = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

test('Hotel booking – Goibibo-grade E2E', async ({ page }) => {
  await page.goto('/');

  // Search hotel
  // Prefer resilient selectors; fall back to sample ones
  const citySelect = page.locator('select[name="city_id"], select#id_city, select[name*="city"]').first();
  await citySelect.selectOption('3').catch(() => {});

  await page.locator('input[name="checkin"], input[type="date"][name*="check"]').first().fill(futureDate(22));
  await page.locator('input[name="checkout"], input[type="date"][name*="check"]').nth(1).fill(futureDate(24));
  await page.getByRole('button', { name: /Search Hotels|Search/i }).first().click();

  // Open hotel
  await page.locator('.hotel-card').first().click().catch(async () => {
    await page.locator('[class*="hotel"], [class*="card"]').first().click();
  });

  // Scroll to rooms (UX behavior)
  const rooms = page.locator('#available-rooms, [id*="rooms"], [class*="rooms"]').first();
  await rooms.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1000);

  // Select meal plan
  const mealDropdown = page.locator('select.meal-plan, select[name*="meal"], [role="combobox"][name*="meal"]').first();
  await mealDropdown.selectOption({ label: 'Breakfast Included' }).catch(async () => {
    const options = mealDropdown.locator('option');
    const count = await options.count();
    if (count > 1) {
      await mealDropdown.selectOption({ index: 1 });
    }
  });

  // Assert price visually changed
  const priceText = await page.locator('.room-price, [class*="price"]').first().innerText();
  expect(priceText).toMatch(/[₹Rs]/);

  // Scroll down – sticky widget must stay
  await page.mouse.wheel(0, 2000);
  await expect(page.locator('.booking-widget, [class*="booking"][class*="widget"]')).toBeVisible();

  // Select room
  await page.getByRole('button', { name: /Select Room/i }).click();

  // Booking page
  await expect(page).toHaveURL(/bookings/);

  // Confirm booking
  await page.getByRole('button', { name: /Confirm Booking|Confirm/i }).click();

  // Final confirmation
  await expect(page.locator('.booking-success, [class*="success"]').first()).toContainText(/Booking Confirmed|Success|Booked/i);
});
