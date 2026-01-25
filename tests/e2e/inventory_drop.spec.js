// Inventory drops visibly after booking
const { test, expect } = require('@playwright/test');

test('Inventory drops visibly', async ({ page }) => {
  await page.goto('/hotels/6/');

  const badge = page.locator('.inventory-badge, [class*="inventory"], [class*="left"]').first();

  const before = (await badge.innerText()).trim();
  await page.getByRole('button', { name: /Select Room/i }).click();
  await page.getByRole('button', { name: /Confirm Booking|Confirm/i }).click();

  await page.reload();

  const after = (await badge.innerText()).trim();
  expect(before).not.toBe(after);
});
