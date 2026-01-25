const { test, expect } = require('@playwright/test');

test('E2E – hotels page renders', async ({ page }) => {
  await page.goto('/hotels/');
  await expect(page.locator('body')).toBeVisible();
});
