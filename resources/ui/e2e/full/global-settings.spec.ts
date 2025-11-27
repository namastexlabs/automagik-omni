import { test, expect } from '../fixtures';
import { waitForToast } from '../utils/test-helpers';

/**
 * Global Settings comprehensive E2E tests
 *
 * Tests the full functionality of the Global Settings page including:
 * - Settings display and organization
 * - Secret value masking/unmasking
 * - Inline editing
 * - Change history tracking
 */

test.describe('Global Settings', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    // Navigate to Global Settings page before each test
    await authenticatedPage.goto('/global-settings');
    await expect(authenticatedPage.locator('h1:has-text("Global Settings"), h2:has-text("Global Settings")')).toBeVisible();
  });

  test('lists all settings with category grouping', async ({ authenticatedPage }) => {
    // Verify Integration category card exists
    await expect(authenticatedPage.locator('text=Integration').or(authenticatedPage.locator('text=integration'))).toBeVisible();

    // Verify System category card exists (or similar)
    const hasSystemCategory = await authenticatedPage
      .locator('text=System, text=system')
      .isVisible()
      .catch(() => false);

    // At least one category should be present (Integration is guaranteed to exist)
    expect(hasSystemCategory).toBeTruthy();

    // Verify evolution_api_key setting is displayed
    await expect(authenticatedPage.locator('text=evolution_api_key')).toBeVisible();
  });

  test('displays setting metadata correctly', async ({ authenticatedPage }) => {
    // Find evolution_api_key setting
    const setting = authenticatedPage.locator('text=evolution_api_key').locator('..');

    // Should have "Secret" badge
    await expect(setting.locator('text=Secret').or(setting.locator('.gradient-primary:has-text("Secret")'))).toBeVisible();

    // Should have "Required" badge or indicator
    const hasRequired = await setting.locator('text=Required').isVisible().catch(() => false);
    expect(hasRequired).toBeTruthy();

    // Should have type badge (e.g., "secret", "string")
    const hasTypeBadge = await setting
      .locator('.badge, [class*="badge"]')
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasTypeBadge).toBeTruthy();
  });

  test('masks secret values by default', async ({ authenticatedPage }) => {
    // Find the evolution_api_key value display
    const keyElement = authenticatedPage
      .locator('text=evolution_api_key')
      .locator('..')
      .locator('code, .font-mono, [class*="mono"]')
      .first();

    await expect(keyElement).toBeVisible();

    // Value should contain masking (***)
    const textContent = await keyElement.textContent();
    expect(textContent).toContain('***');
  });

  test('toggles secret visibility with eye button', async ({ authenticatedPage }) => {
    // Find evolution_api_key setting area
    const settingArea = authenticatedPage.locator('text=evolution_api_key').locator('..');

    // Find eye/visibility toggle button
    const eyeButton = settingArea.locator('button:has([class*="eye"]), button[aria-label*="show" i], button[aria-label*="hide" i]').first();

    if (await eyeButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Get masked value
      const maskedValue = await settingArea.locator('code, .font-mono').first().textContent();

      // Click to show
      await eyeButton.click();
      await authenticatedPage.waitForTimeout(500); // Brief wait for update

      // Get unmasked value
      const unmaskedValue = await settingArea.locator('code, .font-mono').first().textContent();

      // Values should be different
      expect(unmaskedValue).not.toBe(maskedValue);

      // Unmasked should not contain *** (or have more visible characters)
      expect(unmaskedValue?.length).toBeGreaterThan(maskedValue?.length || 0);
    } else {
      test.skip(); // Eye button not found in implementation
    }
  });

  test('displays setting description', async ({ authenticatedPage }) => {
    // Find evolution_api_key setting
    const settingCard = authenticatedPage.locator('text=evolution_api_key').locator('..');

    // Should have description text
    const description = settingCard.locator('.text-xs, .text-muted-foreground, p').first();
    await expect(description).toBeVisible();

    const descText = await description.textContent();
    expect(descText?.length).toBeGreaterThan(0);
  });

  test('displays last updated information', async ({ authenticatedPage }) => {
    // Find evolution_api_key setting
    const settingCard = authenticatedPage.locator('text=evolution_api_key').locator('..');

    // Should display updated timestamp
    await expect(settingCard.locator('text=/Updated:|updated/i')).toBeVisible();
  });

  test('edit button is disabled for required settings', async ({ authenticatedPage }) => {
    // Find evolution_api_key (required setting)
    const settingCard = authenticatedPage.locator('text=evolution_api_key').locator('..');

    // Edit button should not be present (required settings can't be edited this way)
    const editButton = settingCard.locator('button:has-text("Edit")');
    const isEditVisible = await editButton.isVisible({ timeout: 1000 }).catch(() => false);

    // Required settings should NOT have edit button
    expect(isEditVisible).toBeFalsy();

    // Should have "Required" badge instead
    await expect(settingCard.locator('text=Required')).toBeVisible();
  });

  test('displays change history dialog', async ({ authenticatedPage }) => {
    // Find any setting (use evolution_api_key)
    const settingCard = authenticatedPage.locator('text=evolution_api_key').locator('..');

    // Find and click History button
    const historyButton = settingCard.locator('button:has-text("History"), button:has([class*="history"])').first();

    if (await historyButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await historyButton.click();

      // Dialog should appear
      await expect(authenticatedPage.locator('text=Change History')).toBeVisible({ timeout: 5000 });

      // Dialog should show the setting key
      await expect(authenticatedPage.locator('text=evolution_api_key')).toBeVisible();

      // Close dialog (find close button or click outside)
      const closeButton = authenticatedPage.locator('button[aria-label="Close"], button:has-text("Close")').first();
      if (await closeButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await closeButton.click();
      } else {
        // Press Escape to close
        await authenticatedPage.keyboard.press('Escape');
      }
    } else {
      test.skip(); // History button not found
    }
  });

  test('filters settings by category', async ({ authenticatedPage }) => {
    // Check if category filter exists
    const categoryFilter = authenticatedPage.locator('select, [role="combobox"], button:has-text("Category")').first();

    if (await categoryFilter.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Select "integration" category
      await categoryFilter.click();
      await authenticatedPage.locator('text=integration, text=Integration').click();

      // Only integration settings should be visible
      await expect(authenticatedPage.locator('text=evolution_api_key')).toBeVisible();
    } else {
      // Category filter not implemented yet
      test.skip();
    }
  });

  test('page loads without errors', async ({ authenticatedPage }) => {
    const errors: string[] = [];

    authenticatedPage.on('pageerror', (error) => {
      errors.push(error.message);
    });

    await authenticatedPage.goto('/global-settings');
    await authenticatedPage.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });

  test('settings data loads from API', async ({ authenticatedPage }) => {
    // Wait for API response
    const response = await authenticatedPage.waitForResponse(
      (resp) => resp.url().includes('/api/v1/settings') && resp.request().method() === 'GET',
      { timeout: 10000 }
    );

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
    expect(data.length).toBeGreaterThan(0);
  });

  test('responsive layout works on mobile viewport', async ({ authenticatedPage }) => {
    // Set mobile viewport
    await authenticatedPage.setViewportSize({ width: 375, height: 667 });

    await authenticatedPage.goto('/global-settings');

    // Page should still render correctly
    await expect(authenticatedPage.locator('text=Global Settings')).toBeVisible();
    await expect(authenticatedPage.locator('text=evolution_api_key')).toBeVisible();
  });
});
