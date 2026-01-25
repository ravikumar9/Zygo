// Admin change reflects live
const { test, expect } = require('@playwright/test');

test('Admin change reflects live', async ({ page }) => {
  await page.goto('/admin/');
  await page.fill('#id_username, input[name="username"]', 'admin');
  await page.fill('#id_password, input[name="password"]', 'admin123');
  await page.getByRole('button', { name: /Log in|Login/i }).click();

  // Change base price for RoomType id=1
  await page.goto('/admin/hotels/roomtype/1/change/');
  await page.fill('#id_base_price, input[name="base_price"]', '18000');
  await page.getByRole('button', { name: /Save/i }).click().catch(async () => {
    await page.locator('input[name="_save"], [type="submit"]').first().click();
  });

  // Verify live page reflects update
  await page.goto('/hotels/6/');
  await expect(page.locator('.room-price, [class*="price"]').first()).toContainText('18000');
});
