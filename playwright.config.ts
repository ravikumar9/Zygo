import { defineConfig, devices } from '@playwright/test';

/**
 * PHASE 1 PROPERTY OWNER REGISTRATION - PLAYWRIGHT VERIFICATION
 * 
 * Configuration for automated verification of:
 * ✅ Owner registration flow (DRAFT → PENDING → APPROVED)
 * ✅ Admin approval workflow
 * ✅ User visibility rules (DRAFT/PENDING hidden, APPROVED visible)
 * ✅ All mandatory fields working
 * 
 * Run with:
 *   npm test                     # All tests (headless)
 *   npm test -- --headed         # With UI visible
 *   npm test -- --debug          # With debugger
 *   npm test -- --grep "Test 1"  # Specific tests
 */

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/*.spec.ts',
  
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],

  use: {
    baseURL: 'http://127.0.0.1:8000',
    trace: 'on',
    screenshot: 'on',
    video: 'on',
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        headless: process.env.HEADLESS !== 'false',
      },
    },
  ],

  webServer: {
    command: 'C:\\Users\\ravi9\\Downloads\\cgpt\\Go_explorer_clear\\.venv-1\\Scripts\\python.exe manage.py runserver 127.0.0.1:8000',
    url: 'http://127.0.0.1:8000/admin/',
    reuseExistingServer: false,
    timeout: 120000,
  },

  timeout: 60000,
  globalTimeout: 3600000,
});
