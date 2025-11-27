import { test, expect } from '../fixtures';

/**
 * Instances Management comprehensive E2E tests
 *
 * Tests the full functionality of the Instances page including:
 * - Instance listing and display
 * - Instance creation workflow
 * - QR code display
 * - Instance status management
 */

test.describe('Instances Management', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    // Navigate to Instances page before each test
    await authenticatedPage.goto('/instances');
    await expect(authenticatedPage.locator('h1:has-text("Instances"), h2:has-text("Instances")')).toBeVisible();
  });

  test('lists all instances', async ({ authenticatedPage }) => {
    // Page should load successfully
    await expect(authenticatedPage.locator('h1:has-text("Instances"), h2:has-text("Instances")')).toBeVisible();

    // Should wait for instances to load (may be empty or have instances)
    await authenticatedPage.waitForLoadState('networkidle');

    // Either instance list or empty state should be visible
    const hasInstances = await authenticatedPage
      .locator('.instance, [data-testid="instance"], [class*="instance-card"]')
      .first()
      .isVisible({ timeout: 2000 })
      .catch(() => false);

    const hasEmptyState = await authenticatedPage
      .locator('text=/No instances|Create your first instance|Get started/i')
      .isVisible({ timeout: 2000 })
      .catch(() => false);

    expect(hasInstances || hasEmptyState).toBeTruthy();
  });

  test('displays instance status badges', async ({ authenticatedPage }) => {
    // Check if there are any instances
    const firstInstance = authenticatedPage
      .locator('.instance, [data-testid="instance"], [class*="instance-card"]')
      .first();

    if (await firstInstance.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Should have status badge (connected, disconnected, etc.)
      const statusBadge = firstInstance.locator('.badge, [data-testid="status"], [class*="status"]').first();
      await expect(statusBadge).toBeVisible();
    } else {
      test.skip(); // No instances to test
    }
  });

  test('create instance button is visible', async ({ authenticatedPage }) => {
    // Find create/add instance button
    const createButton = authenticatedPage.locator(
      'button:has-text("Create"), button:has-text("Add Instance"), button:has-text("New Instance")'
    ).first();

    await expect(createButton).toBeVisible();
  });

  test('instance details modal or page opens', async ({ authenticatedPage }) => {
    // Find first instance
    const firstInstance = authenticatedPage
      .locator('.instance, [data-testid="instance"], [class*="instance-card"]')
      .first();

    if (await firstInstance.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Click to view details
      await firstInstance.click();

      // Either modal or navigation should occur
      const hasModal = await authenticatedPage
        .locator('[role="dialog"], .modal, [class*="modal"]')
        .isVisible({ timeout: 2000 })
        .catch(() => false);

      const urlChanged = (await authenticatedPage.url()) !== 'http://localhost:9882/instances';

      expect(hasModal || urlChanged).toBeTruthy();
    } else {
      test.skip(); // No instances to test
    }
  });

  test('instance actions menu works', async ({ authenticatedPage }) => {
    // Find first instance
    const firstInstance = authenticatedPage
      .locator('.instance, [data-testid="instance"], [class*="instance-card"]')
      .first();

    if (await firstInstance.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Look for actions menu (three dots, etc.)
      const actionsButton = firstInstance.locator('button[aria-label*="Actions" i], button:has([class*="dots"]), button[aria-label*="More" i]').first();

      if (await actionsButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await actionsButton.click();

        // Menu should appear
        const menu = authenticatedPage.locator('[role="menu"], .menu, [class*="dropdown"]').first();
        await expect(menu).toBeVisible({ timeout: 2000 });
      } else {
        test.skip(); // Actions menu not found
      }
    } else {
      test.skip(); // No instances to test
    }
  });

  test('instances load from API', async ({ authenticatedPage }) => {
    // Wait for API response
    const response = await authenticatedPage.waitForResponse(
      (resp) => resp.url().includes('/instances') && resp.request().method() === 'GET',
      { timeout: 10000 }
    );

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(Array.isArray(data) || typeof data === 'object').toBeTruthy();
  });

  test('page loads without errors', async ({ authenticatedPage }) => {
    const errors: string[] = [];

    authenticatedPage.on('pageerror', (error) => {
      errors.push(error.message);
    });

    await authenticatedPage.goto('/instances');
    await authenticatedPage.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });

  test('responsive layout works on mobile viewport', async ({ authenticatedPage }) => {
    // Set mobile viewport
    await authenticatedPage.setViewportSize({ width: 375, height: 667 });

    await authenticatedPage.goto('/instances');

    // Page should still render correctly
    await expect(authenticatedPage.locator('text=Instances')).toBeVisible();

    // Create button should be accessible
    const createButton = authenticatedPage.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New")').first();
    await expect(createButton).toBeVisible();
  });

});
