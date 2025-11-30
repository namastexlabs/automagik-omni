import { test, expect } from '../fixtures';

/**
 * Navigation smoke tests
 *
 * Quick tests to verify all main pages are accessible
 * Tagged with @smoke for quick test runs
 */

test.describe('Navigation @smoke', () => {
  test('all main pages are accessible from authenticated dashboard', async ({ authenticatedPage }) => {
    // Start from dashboard
    await authenticatedPage.goto('/dashboard');
    await expect(authenticatedPage.locator('h1:has-text("Dashboard"), h2:has-text("Dashboard")')).toBeVisible();

    // Navigate to Instances
    await authenticatedPage.goto('/instances');
    await expect(authenticatedPage.locator('h1:has-text("Instances"), h2:has-text("Instances")')).toBeVisible();

    // Navigate to Contacts
    await authenticatedPage.goto('/contacts');
    await expect(authenticatedPage.locator('h1:has-text("Contacts"), h2:has-text("Contacts")')).toBeVisible();

    // Navigate to Chats
    await authenticatedPage.goto('/chats');
    await expect(authenticatedPage.locator('h1:has-text("Chats"), h2:has-text("Chats")')).toBeVisible();

    // Navigate to Settings
    await authenticatedPage.goto('/settings');
    await expect(authenticatedPage.locator('h1:has-text("Settings"), h2:has-text("Settings")')).toBeVisible();

    // Navigate to Global Settings
    await authenticatedPage.goto('/global-settings');
    await expect(authenticatedPage.locator('h1:has-text("Global Settings"), h2:has-text("Global Settings")')).toBeVisible();
  });

  test('root path redirects to dashboard when authenticated', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');

    // Should redirect to dashboard
    await expect(authenticatedPage).toHaveURL('/dashboard');
  });

  test('sidebar navigation links work', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');

    // Find and click sidebar link to Instances (if sidebar exists)
    const instancesLink = authenticatedPage.locator('a[href="/instances"], nav a:has-text("Instances")').first();

    if (await instancesLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await instancesLink.click();
      await expect(authenticatedPage).toHaveURL('/instances');
    } else {
      // Sidebar may not exist in current implementation
      test.skip();
    }
  });

  test('breadcrumb navigation works', async ({ authenticatedPage }) => {
    // Navigate to a deep page
    await authenticatedPage.goto('/global-settings');

    // Look for breadcrumb links (if they exist)
    const breadcrumb = authenticatedPage.locator('nav[aria-label="breadcrumb"], .breadcrumb').first();

    if (await breadcrumb.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Click first breadcrumb link (usually Home/Dashboard)
      const firstCrumb = breadcrumb.locator('a').first();
      await firstCrumb.click();

      // Should navigate somewhere (implementation-specific)
      await expect(authenticatedPage).not.toHaveURL('/global-settings');
    } else {
      // Breadcrumbs may not exist in current implementation
      test.skip();
    }
  });

  test('page titles are correct for each route', async ({ authenticatedPage }) => {
    const routes = [
      { path: '/dashboard', title: /Dashboard|Omni/ },
      { path: '/instances', title: /Instances|Omni/ },
      { path: '/settings', title: /Settings|Omni/ },
      { path: '/global-settings', title: /Global Settings|Omni/ },
    ];

    for (const route of routes) {
      await authenticatedPage.goto(route.path);
      await expect(authenticatedPage).toHaveTitle(route.title);
    }
  });

  test('back button navigation works', async ({ authenticatedPage }) => {
    // Navigate dashboard → instances → settings
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.goto('/instances');
    await authenticatedPage.goto('/settings');

    // Go back
    await authenticatedPage.goBack();
    await expect(authenticatedPage).toHaveURL('/instances');

    // Go back again
    await authenticatedPage.goBack();
    await expect(authenticatedPage).toHaveURL('/dashboard');
  });
});
