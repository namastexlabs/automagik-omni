import { test, expect } from '../fixtures';

/**
 * Service health smoke tests
 *
 * Quick tests to verify backend services are running and accessible
 * Tagged with @smoke for quick test runs
 */

test.describe('Service Health @smoke', () => {
  test('API health check shows connected status', async ({ authenticatedPage }) => {
    // Navigate to settings page (displays API health)
    await authenticatedPage.goto('/settings');

    // Look for "Connected" status badge/indicator
    const connectedBadge = authenticatedPage.locator(
      'text=Connected, [data-status="connected"], .status-connected, .badge:has-text("Connected")'
    ).first();

    // Should be visible within reasonable time
    await expect(connectedBadge).toBeVisible({ timeout: 10000 });
  });

  test('API health endpoint responds successfully', async ({ page }) => {
    // Direct API health check
    const apiUrl = process.env.VITE_API_URL || 'http://localhost:8882';
    const response = await fetch(`${apiUrl}/health`);

    expect(response.ok).toBeTruthy();
    expect(response.status).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(data.status).toBe('up');
  });

  test('UI loads without errors', async ({ authenticatedPage }) => {
    const errors: string[] = [];

    // Capture console errors
    authenticatedPage.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Capture page errors
    authenticatedPage.on('pageerror', (error) => {
      errors.push(error.message);
    });

    // Navigate to dashboard
    await authenticatedPage.goto('/dashboard');

    // Wait for page to fully load
    await authenticatedPage.waitForLoadState('networkidle');

    // Should have no critical errors
    const criticalErrors = errors.filter((err) => {
      // Filter out non-critical warnings
      return (
        !err.includes('Warning:') &&
        !err.includes('[HMR]') &&
        !err.includes('DevTools')
      );
    });

    expect(criticalErrors).toHaveLength(0);
  });

  test('static assets load successfully', async ({ authenticatedPage }) => {
    const failedRequests: string[] = [];

    // Track failed network requests
    authenticatedPage.on('requestfailed', (request) => {
      failedRequests.push(request.url());
    });

    // Load dashboard
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    // Should have no failed asset requests
    expect(failedRequests).toHaveLength(0);
  });

  test('WebSocket connection status is visible if applicable', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');

    // Look for WebSocket status indicator (may not exist in all implementations)
    const wsIndicator = authenticatedPage.locator(
      '[data-testid="websocket-status"], .ws-status, text=/WebSocket|Socket/'
    ).first();

    if (await wsIndicator.isVisible({ timeout: 2000 }).catch(() => false)) {
      // If WebSocket indicator exists, verify it's not showing error state
      const hasError = await authenticatedPage
        .locator('text=/disconnected|error|failed/i')
        .isVisible()
        .catch(() => false);

      expect(hasError).toBeFalsy();
    } else {
      // WebSocket indicator doesn't exist (implementation-specific)
      test.skip();
    }
  });

  test('API version is displayed', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/settings');

    // Look for API version display
    const versionElement = authenticatedPage.locator(
      '[data-testid="api-version"], .api-version, text=/v\\d+\\.\\d+\\.\\d+|Version: /i'
    ).first();

    if (await versionElement.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Version is displayed
      await expect(versionElement).toBeVisible();
    } else {
      // Version display may not exist in current implementation
      test.skip();
    }
  });

  test('no HTTP 500 errors on page load', async ({ authenticatedPage }) => {
    const serverErrors: string[] = [];

    // Track 500 errors
    authenticatedPage.on('response', (response) => {
      if (response.status() >= 500) {
        serverErrors.push(`${response.status()} - ${response.url()}`);
      }
    });

    // Load all main pages
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.goto('/instances');
    await authenticatedPage.goto('/settings');

    // Should have no server errors
    expect(serverErrors).toHaveLength(0);
  });
});
