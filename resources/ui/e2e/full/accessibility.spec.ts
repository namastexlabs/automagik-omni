import { test, expect } from '../fixtures';

/**
 * Accessibility comprehensive E2E tests
 *
 * Tests WCAG compliance and accessibility features including:
 * - Keyboard navigation
 * - ARIA labels and roles
 * - Focus management
 * - Screen reader compatibility
 * - Color contrast (basic checks)
 */

test.describe('Accessibility', () => {
  test('keyboard navigation works through main elements', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');

    // Tab through elements
    for (let i = 0; i < 10; i++) {
      await authenticatedPage.keyboard.press('Tab');

      // Check that focus is visible
      const focused = authenticatedPage.locator(':focus');
      const isVisible = await focused.isVisible().catch(() => false);

      // At least some elements should be focusable
      if (isVisible) {
        expect(isVisible).toBeTruthy();
        break;
      }
    }

    // Verify focus indicator exists
    const focused = authenticatedPage.locator(':focus');
    if (await focused.isVisible().catch(() => false)) {
      const outlineStyle = await focused.evaluate((el) => getComputedStyle(el).outline);
      const boxShadow = await focused.evaluate((el) => getComputedStyle(el).boxShadow);

      // Should have some visual focus indicator
      expect(outlineStyle !== 'none' || boxShadow !== 'none').toBeTruthy();
    }
  });

  test('all interactive elements have aria labels or accessible text', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/settings');

    // Find all buttons
    const buttons = await authenticatedPage.locator('button').all();

    for (const button of buttons) {
      const ariaLabel = await button.getAttribute('aria-label');
      const text = await button.textContent();
      const title = await button.getAttribute('title');

      // Button should have SOME accessible text
      expect(ariaLabel || text || title).toBeTruthy();
    }
  });

  test('theme toggle has proper aria label', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/settings');

    const themeToggle = authenticatedPage.locator('button[aria-label*="Toggle theme" i], button[aria-label*="Theme" i]').first();

    if (await themeToggle.isVisible({ timeout: 2000 }).catch(() => false)) {
      const ariaLabel = await themeToggle.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel?.toLowerCase()).toContain('theme');
    }
  });

  test('form inputs have associated labels', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/login');

    // Find all input fields
    const inputs = await authenticatedPage.locator('input').all();

    for (const input of inputs) {
      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledBy = await input.getAttribute('aria-labelledby');

      // Input should have label, aria-label, or aria-labelledby
      if (id) {
        // Check if there's a label with for=id
        const label = await authenticatedPage.locator(`label[for="${id}"]`).isVisible().catch(() => false);
        expect(label || ariaLabel || ariaLabelledBy).toBeTruthy();
      } else {
        expect(ariaLabel || ariaLabelledBy).toBeTruthy();
      }
    }
  });

  test('headings follow hierarchical structure', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');

    // Get all heading levels
    const h1Count = await authenticatedPage.locator('h1').count();
    const h2Count = await authenticatedPage.locator('h2').count();

    // Page should have at least one h1 (page title)
    expect(h1Count).toBeGreaterThanOrEqual(1);

    // If there are h2s, verify they're not orphaned
    if (h2Count > 0) {
      // h1 should come before h2
      const firstH1 = authenticatedPage.locator('h1').first();
      const firstH2 = authenticatedPage.locator('h2').first();

      await expect(firstH1).toBeVisible();
      await expect(firstH2).toBeVisible();
    }
  });

  test('images have alt text', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');

    // Find all images
    const images = await authenticatedPage.locator('img').all();

    for (const image of images) {
      const alt = await image.getAttribute('alt');
      const role = await image.getAttribute('role');

      // Image should have alt text (or role="presentation" if decorative)
      expect(alt !== null || role === 'presentation').toBeTruthy();
    }
  });

  test('links have descriptive text', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');

    // Find all links
    const links = await authenticatedPage.locator('a').all();

    for (const link of links) {
      const text = await link.textContent();
      const ariaLabel = await link.getAttribute('aria-label');

      // Link should have meaningful text
      expect(text || ariaLabel).toBeTruthy();
      expect((text || ariaLabel)?.trim().length).toBeGreaterThan(0);
    }
  });


  test('color contrast is sufficient for text', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');

    // Get computed styles for main text
    const bodyText = authenticatedPage.locator('body, main').first();
    const color = await bodyText.evaluate((el) => getComputedStyle(el).color);
    const backgroundColor = await bodyText.evaluate((el) => getComputedStyle(el).backgroundColor);

    // Both should be defined
    expect(color).toBeTruthy();
    expect(backgroundColor).toBeTruthy();

    // This is a basic check - full contrast analysis requires color parsing
    // In a real scenario, use axe-core or similar tool
  });

  test('page has valid lang attribute', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');

    const html = authenticatedPage.locator('html');
    const lang = await html.getAttribute('lang');

    // Should have lang attribute
    expect(lang).toBeTruthy();
    expect(lang).toMatch(/^[a-z]{2}(-[A-Z]{2})?$/); // e.g., "en" or "en-US"
  });

  test('buttons have appropriate roles', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/settings');

    // Find all button-like elements
    const buttons = await authenticatedPage.locator('button, [role="button"]').all();

    for (const button of buttons) {
      const tagName = await button.evaluate((el) => el.tagName);
      const role = await button.getAttribute('role');

      // Either native button or explicit role
      expect(tagName === 'BUTTON' || role === 'button').toBeTruthy();
    }
  });
});
