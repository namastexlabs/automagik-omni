import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Automagik Omni E2E tests
 *
 * E2E tests run against DEPLOYED instance (not local code):
 * - Default: https://omni.genieos.namastex.io
 * - Override: E2E_BASE_URL environment variable
 *
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI for stability */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter - verbose for debugging */
  reporter: [
    ['html'],
    ['list'], // Shows test progress in terminal
  ],

  /* Shared settings for all projects */
  use: {
    /* Base URL - defaults to deployed instance */
    baseURL: process.env.E2E_BASE_URL || 'https://omni.genieos.namastex.io',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',

    /* Capture screenshot only on failure */
    screenshot: 'only-on-failure',

    /* Capture video only on failure */
    video: 'retain-on-failure',

    /* Longer timeout for deployed instance (network latency) */
    actionTimeout: 30000,
    navigationTimeout: 60000,
  },

  /* Global test timeout */
  timeout: 120000,

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* NO webServer - we test deployed instance, not local code */
});
