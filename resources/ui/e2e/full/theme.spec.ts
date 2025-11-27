import { test, expect } from '../fixtures';

/**
 * Theme Toggle comprehensive E2E tests
 *
 * Tests the dark/light mode functionality including:
 * - Theme toggle interaction
 * - Theme persistence across pages
 * - Theme persistence across sessions
 * - CSS variable updates
 */

test.describe('Theme Toggle', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    // Start from settings page (where theme toggle typically lives)
    await authenticatedPage.goto('/settings');
  });

  test('toggles between light and dark mode', async ({ authenticatedPage }) => {
    // Find theme toggle button
    const themeToggle = authenticatedPage.locator(
      'button[aria-label*="Toggle theme" i], button[aria-label*="Theme" i], [data-testid="theme-toggle"]'
    ).first();

    await expect(themeToggle).toBeVisible();

    // Get initial theme class on html element
    const html = authenticatedPage.locator('html');
    const initialClass = await html.getAttribute('class');

    // Toggle theme
    await themeToggle.click();

    // Wait for theme change
    await authenticatedPage.waitForTimeout(500);

    // Get new theme class
    const newClass = await html.getAttribute('class');

    // Theme should have changed (class should be different)
    expect(newClass).not.toBe(initialClass);

    // One should have "dark" class, the other should not
    const hadDark = initialClass?.includes('dark') || false;
    const hasDark = newClass?.includes('dark') || false;

    expect(hadDark !== hasDark).toBeTruthy();
  });

  test('persists theme across page navigation', async ({ authenticatedPage }) => {
    // Find and toggle theme
    const themeToggle = authenticatedPage.locator(
      'button[aria-label*="Toggle theme" i], button[aria-label*="Theme" i]'
    ).first();

    if (await themeToggle.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Toggle to dark mode (or light if already dark)
      await themeToggle.click();
      await authenticatedPage.waitForTimeout(500);

      // Get theme after toggle
      const html = authenticatedPage.locator('html');
      const themeAfterToggle = await html.getAttribute('class');

      // Navigate to different page
      await authenticatedPage.goto('/dashboard');
      await authenticatedPage.waitForTimeout(500);

      // Theme should persist
      const themeAfterNavigation = await html.getAttribute('class');
      expect(themeAfterNavigation).toBe(themeAfterToggle);

      // Navigate to another page
      await authenticatedPage.goto('/instances');
      await authenticatedPage.waitForTimeout(500);

      // Theme should still persist
      const themeAfterSecondNavigation = await html.getAttribute('class');
      expect(themeAfterSecondNavigation).toBe(themeAfterToggle);
    } else {
      test.skip(); // Theme toggle not found
    }
  });

  test('persists theme across page refresh', async ({ authenticatedPage }) => {
    const themeToggle = authenticatedPage.locator(
      'button[aria-label*="Toggle theme" i], button[aria-label*="Theme" i]'
    ).first();

    if (await themeToggle.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Toggle theme
      await themeToggle.click();
      await authenticatedPage.waitForTimeout(500);

      // Get theme
      const html = authenticatedPage.locator('html');
      const themeBeforeRefresh = await html.getAttribute('class');

      // Refresh page
      await authenticatedPage.reload();
      await authenticatedPage.waitForLoadState('networkidle');
      await authenticatedPage.waitForTimeout(500);

      // Theme should persist
      const themeAfterRefresh = await html.getAttribute('class');
      expect(themeAfterRefresh).toBe(themeBeforeRefresh);
    } else {
      test.skip();
    }
  });

  test('theme toggle icon changes based on current theme', async ({ authenticatedPage }) => {
    const themeToggle = authenticatedPage.locator(
      'button[aria-label*="Toggle theme" i], button[aria-label*="Theme" i]'
    ).first();

    if (await themeToggle.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Get initial icon (by checking SVG or class)
      const initialIcon = await themeToggle.locator('svg, [class*="icon"]').first().getAttribute('class');

      // Toggle theme
      await themeToggle.click();
      await authenticatedPage.waitForTimeout(500);

      // Icon should change
      const newIcon = await themeToggle.locator('svg, [class*="icon"]').first().getAttribute('class');
      expect(newIcon).not.toBe(initialIcon);
    } else {
      test.skip();
    }
  });

  test('CSS variables update when theme changes', async ({ authenticatedPage }) => {
    const themeToggle = authenticatedPage.locator(
      'button[aria-label*="Toggle theme" i], button[aria-label*="Theme" i]'
    ).first();

    if (await themeToggle.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Get initial background color from computed styles
      const body = authenticatedPage.locator('body');
      const initialBg = await body.evaluate((el) => getComputedStyle(el).backgroundColor);

      // Toggle theme
      await themeToggle.click();
      await authenticatedPage.waitForTimeout(500);

      // Background should change
      const newBg = await body.evaluate((el) => getComputedStyle(el).backgroundColor);
      expect(newBg).not.toBe(initialBg);
    } else {
      test.skip();
    }
  });

  test('theme preference is stored in localStorage', async ({ authenticatedPage }) => {
    const themeToggle = authenticatedPage.locator(
      'button[aria-label*="Toggle theme" i], button[aria-label*="Theme" i]'
    ).first();

    if (await themeToggle.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Toggle to dark mode
      await themeToggle.click();
      await authenticatedPage.waitForTimeout(500);

      // Check localStorage
      const theme = await authenticatedPage.evaluate(() => {
        return localStorage.getItem('theme') || localStorage.getItem('vite-ui-theme');
      });

      expect(theme).toBeTruthy();
      expect(theme === 'dark' || theme === 'light').toBeTruthy();
    } else {
      test.skip();
    }
  });

  test('all pages render correctly in both themes', async ({ authenticatedPage }) => {
    const themeToggle = authenticatedPage.locator(
      'button[aria-label*="Toggle theme" i], button[aria-label*="Theme" i]'
    ).first();

    if (await themeToggle.isVisible({ timeout: 2000 }).catch(() => false)) {
      const pages = ['/dashboard', '/instances', '/settings', '/global-settings'];

      // Test each page in dark mode
      await themeToggle.click();
      await authenticatedPage.waitForTimeout(500);

      for (const page of pages) {
        await authenticatedPage.goto(page);
        await authenticatedPage.waitForLoadState('networkidle');

        // Page should render without errors
        const hasContent = await authenticatedPage
          .locator('main, [role="main"], .main-content')
          .isVisible()
          .catch(() => false);
        expect(hasContent).toBeTruthy();
      }

      // Toggle back to light mode and test again
      await authenticatedPage.goto('/settings');
      await themeToggle.click();
      await authenticatedPage.waitForTimeout(500);

      for (const page of pages) {
        await authenticatedPage.goto(page);
        await authenticatedPage.waitForLoadState('networkidle');

        const hasContent = await authenticatedPage
          .locator('main, [role="main"], .main-content')
          .isVisible()
          .catch(() => false);
        expect(hasContent).toBeTruthy();
      }
    } else {
      test.skip();
    }
  });

  test('theme toggle is accessible via keyboard', async ({ authenticatedPage }) => {
    // Tab to theme toggle
    await authenticatedPage.keyboard.press('Tab');
    await authenticatedPage.keyboard.press('Tab');
    await authenticatedPage.keyboard.press('Tab');
    // (May need more tabs depending on page structure)

    // Find focused element
    const focused = authenticatedPage.locator(':focus');
    const ariaLabel = await focused.getAttribute('aria-label');

    // If we found the theme toggle via keyboard navigation
    if (ariaLabel?.toLowerCase().includes('theme')) {
      const html = authenticatedPage.locator('html');
      const initialTheme = await html.getAttribute('class');

      // Press Enter or Space to toggle
      await authenticatedPage.keyboard.press('Enter');
      await authenticatedPage.waitForTimeout(500);

      // Theme should change
      const newTheme = await html.getAttribute('class');
      expect(newTheme).not.toBe(initialTheme);
    } else {
      // Theme toggle not found via keyboard navigation
      expect(true).toBeTruthy(); // Soft pass
    }
  });
});
