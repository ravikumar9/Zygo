// Wallet deduction must be seen for authenticated user
const { test, expect } = require('@playwright/test');

test('Wallet deduction visible', async ({ page }) => {
  await page.goto('/login/');
  await page.fill('#id_username, input[name="username"]', 'walletuser');
  await page.fill('#id_password, input[name="password"]', 'test123');
  await page.getByRole('button', { name: /Login|Sign in/i }).click();

  await page.goto('/hotels/6/');
  await page.getByRole('button', { name: /Select Room/i }).click();

  await expect(page.locator('.wallet-balance, [class*="wallet"][class*="balance"]').first()).toBeVisible();
});
