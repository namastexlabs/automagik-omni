import { test as base, Page } from '@playwright/test';

/**
 * Custom Playwright fixtures for Automagik Omni E2E tests
 *
 * Provides pre-authenticated pages and other shared test utilities
 */

type Fixtures = {
  authenticatedPage: Page;
};

export const test = base.extend<Fixtures>({
  authenticatedPage: async ({ page }, use) => {
    // Navigate to login page
    await page.goto('/login');

    // Get API key from environment (fallback to test key)
    const apiKey = process.env.TEST_API_KEY || 'test-api-key-for-development';

    // Fill in API key and submit
    await page.fill('input[name="apiKey"]', apiKey);
    await page.click('button[type="submit"]');

    // Wait for redirect to dashboard (authentication success)
    await page.waitForURL('/dashboard', { timeout: 10000 });

    // Provide authenticated page to test
    await use(page);

    // Cleanup handled automatically
  },
});

export { expect } from '@playwright/test';
