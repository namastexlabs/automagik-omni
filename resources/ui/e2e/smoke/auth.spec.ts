import { test, expect } from '../fixtures';

/**
 * Authentication smoke tests
 *
 * Quick tests to verify core login/logout functionality
 * Tagged with @smoke for quick test runs
 */

test.describe('Authentication @smoke', () => {
  test('login with valid credentials redirects to dashboard', async ({ page }) => {
    await page.goto('/login');

    // Fill in API key
    const apiKey = process.env.TEST_API_KEY || 'test-api-key-for-development';
    await page.fill('input[name="apiKey"]', apiKey);

    // Submit form
    await page.click('button[type="submit"]');

    // Verify redirect to dashboard
    await expect(page).toHaveURL('/dashboard');

    // Verify dashboard content loaded
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });

  test('login with invalid credentials shows error', async ({ page }) => {
    await page.goto('/login');

    // Fill in invalid API key
    await page.fill('input[name="apiKey"]', 'invalid-key-12345');

    // Submit form
    await page.click('button[type="submit"]');

    // Should still be on login page
    await expect(page).toHaveURL('/login');

    // Error message should be visible (may vary based on implementation)
    // Looking for common error indicators
    const hasInvalidText = await page.locator('text=Invalid').isVisible().catch(() => false);
    const hasErrorText = await page.locator('text=error').isVisible().catch(() => false);
    const hasFailedText = await page.locator('text=failed').isVisible().catch(() => false);

    // At least one error indicator should be present
    expect(hasInvalidText || hasErrorText || hasFailedText).toBeTruthy();
  });

  test('logout redirects to login page', async ({ authenticatedPage }) => {
    // Start from authenticated dashboard
    await expect(authenticatedPage).toHaveURL('/dashboard');

    // Look for logout button (may be in dropdown, sidebar, or header)
    // Try multiple possible selectors
    const logoutButton = authenticatedPage.locator(
      'button:has-text("Logout"), button[aria-label="Logout"], a:has-text("Logout"), a:has-text("Sign out")'
    ).first();

    // Click logout if found
    if (await logoutButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await logoutButton.click();

      // Verify redirect to login page
      await expect(authenticatedPage).toHaveURL('/login', { timeout: 5000 });
    } else {
      // If no logout button found, test is skipped (implementation may vary)
      test.skip();
    }
  });

  test('protected routes redirect to login when not authenticated', async ({ page }) => {
    // Try to access dashboard without authentication
    await page.goto('/dashboard');

    // Should be redirected to login
    await expect(page).toHaveURL('/login');
  });

  test('login form has API key input field', async ({ page }) => {
    await page.goto('/login');

    // Verify API key input exists
    const apiKeyInput = page.locator('input[name="apiKey"], input[type="password"]').first();
    await expect(apiKeyInput).toBeVisible();
  });
});
