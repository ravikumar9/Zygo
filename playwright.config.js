import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  use: {
    headless: false,
    slowMo: 700,
    baseURL: 'http://127.0.0.1:8000',
    screenshot: 'on',
    video: 'on',
    trace: 'on',
  },
  reporter: [
    ['html', { open: 'never' }],
    ['list']
  ],
});
