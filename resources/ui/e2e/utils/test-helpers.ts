import { Page, expect } from '@playwright/test';

/**
 * Test helper utilities for Automagik Omni E2E tests
 */

// ============================================================================
// Onboarding Test Configuration
// ============================================================================

/**
 * Test credentials for internal infrastructure
 * These are used for E2E tests against deployed instances
 */
export const TEST_CONFIG = {
  postgres: {
    host: '10.114.1.135',
    password: 'REDACTED',
    port: 5432,
    database: 'automagik_omni',
    user: 'automagik',
  },
  redis: {
    host: '10.114.1.114',
    port: 6379,
  },
};

// ============================================================================
// Onboarding Helpers
// ============================================================================

/**
 * Wait for page to be fully loaded (network idle + no spinners)
 */
export async function waitForPageReady(page: Page) {
  await page.waitForLoadState('networkidle');
  // Wait for any loading spinners to disappear
  const spinner = page.locator('[class*="animate-spin"], [class*="loading"]');
  if (await spinner.isVisible({ timeout: 1000 }).catch(() => false)) {
    await spinner.waitFor({ state: 'hidden', timeout: 30000 });
  }
}

/**
 * Clear all storage to ensure fresh state
 * Must be called AFTER navigating to a page first
 */
export async function clearBrowserState(page: Page) {
  try {
    // Clear localStorage
    await page.evaluate(() => {
      localStorage.clear();
    });
  } catch (e) {
    // Ignore errors if page isn't loaded yet
  }
}

/**
 * Navigate to onboarding wizard (goes to root for proper redirect flow)
 *
 * The app will redirect based on setup status:
 * - requires_setup=true -> /onboarding/setup (Database)
 * - requires_setup=false && !authenticated -> /onboarding/api-key
 * - authenticated -> /dashboard
 */
export async function goToOnboarding(page: Page) {
  // Navigate first to get proper page context
  await page.goto('/');

  // Now clear storage
  await clearBrowserState(page);

  // Reload to trigger fresh redirect based on cleared state
  await page.reload();
  await waitForPageReady(page);

  // Wait for redirect to settle
  await page.waitForTimeout(500);
}

/**
 * Navigate directly to database setup step
 */
export async function goToSetupStep(page: Page) {
  await page.goto('/onboarding/setup');
  await clearBrowserState(page);
  await page.reload();
  await waitForPageReady(page);
}

/**
 * Detect which onboarding step we're on
 */
export async function detectCurrentStep(page: Page): Promise<'setup' | 'api-key' | 'channels' | 'dashboard' | 'unknown'> {
  const url = page.url();

  if (url.includes('/onboarding/setup')) return 'setup';
  if (url.includes('/onboarding/api-key')) return 'api-key';
  if (url.includes('/onboarding/channels')) return 'channels';
  if (url.includes('/dashboard')) return 'dashboard';

  // Check page content
  const hasDatabase = await page.getByText(/Database|PostgreSQL|SQLite/i).first().isVisible({ timeout: 1000 }).catch(() => false);
  if (hasDatabase) return 'setup';

  const hasApiKey = await page.getByText(/API Key|Your API Key/i).first().isVisible({ timeout: 1000 }).catch(() => false);
  if (hasApiKey) return 'api-key';

  const hasChannels = await page.getByText(/Channel|WhatsApp/i).first().isVisible({ timeout: 1000 }).catch(() => false);
  if (hasChannels) return 'channels';

  return 'unknown';
}

/**
 * Fill database setup form with PostgreSQL config
 */
export async function fillDatabaseSetup(page: Page, config = TEST_CONFIG.postgres) {
  // Select PostgreSQL (click the card/button)
  const postgresOption = page.locator('text=PostgreSQL').first();
  if (await postgresOption.isVisible({ timeout: 2000 }).catch(() => false)) {
    await postgresOption.click();
  }

  // Fill connection details - try multiple selector strategies
  const hostInput = page.getByLabel(/Host/i).or(page.locator('input[name*="host"]')).first();
  const portInput = page.getByLabel(/Port/i).or(page.locator('input[name*="port"]')).first();
  const passwordInput = page.getByLabel(/Password/i).or(page.locator('input[type="password"]')).first();
  const databaseInput = page.getByLabel(/Database/i).or(page.locator('input[name*="database"]')).first();

  if (await hostInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await hostInput.fill(config.host);
  }
  if (await portInput.isVisible({ timeout: 1000 }).catch(() => false)) {
    await portInput.fill(String(config.port));
  }
  if (await passwordInput.isVisible({ timeout: 1000 }).catch(() => false)) {
    await passwordInput.fill(config.password);
  }
  if (await databaseInput.isVisible({ timeout: 1000 }).catch(() => false)) {
    await databaseInput.fill(config.database);
  }
}

/**
 * Fill channel setup form - enable WhatsApp
 */
export async function fillChannelSetup(page: Page) {
  // Look for WhatsApp toggle/switch
  const whatsappToggle = page.getByRole('switch', { name: /WhatsApp/i })
    .or(page.locator('[data-channel="whatsapp"]'))
    .or(page.locator('text=WhatsApp').locator('..').getByRole('switch'))
    .first();

  if (await whatsappToggle.isVisible({ timeout: 2000 }).catch(() => false)) {
    // Check if not already enabled
    const isChecked = await whatsappToggle.isChecked().catch(() => false);
    if (!isChecked) {
      await whatsappToggle.click();
    }
  }
}

/**
 * Click Next/Continue button in wizard
 */
export async function clickNextInWizard(page: Page) {
  const nextButton = page.getByRole('button', { name: /Next|Continue/i }).first();
  await nextButton.click();
  await waitForPageReady(page);
}

/**
 * Click Finish/Complete button in wizard
 */
export async function clickFinishInWizard(page: Page) {
  const finishButton = page.getByRole('button', { name: /Finish|Complete|Get Started/i }).first();
  await finishButton.click();
}

/**
 * Wait for a toast notification to appear with specific message
 *
 * @param page - Playwright page object
 * @param message - Expected toast message text
 * @param timeout - Max wait time in milliseconds (default: 5000)
 */
export async function waitForToast(page: Page, message: string, timeout = 5000) {
  const toastLocator = page.locator(`text=${message}`);
  await expect(toastLocator).toBeVisible({ timeout });
}

/**
 * Wait for a service to be ready by polling its health endpoint
 *
 * @param url - Service health endpoint URL
 * @param timeout - Max wait time in milliseconds (default: 30000)
 * @throws Error if service doesn't become ready within timeout
 */
export async function waitForServiceReady(url: string, timeout = 30000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return; // Service is ready
      }
    } catch (error) {
      // Service not ready yet, continue polling
    }

    // Wait 1 second before next attempt
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw new Error(`Service not ready after ${timeout}ms: ${url}`);
}

/**
 * Wait for API response and verify it's successful
 *
 * @param page - Playwright page object
 * @param urlPattern - URL pattern to match (string or regex)
 * @param timeout - Max wait time in milliseconds (default: 10000)
 */
export async function waitForAPIResponse(
  page: Page,
  urlPattern: string | RegExp,
  timeout = 10000
) {
  const response = await page.waitForResponse(urlPattern, { timeout });
  expect(response.ok()).toBeTruthy();
  return response;
}

/**
 * Fill form field and wait for it to be filled
 *
 * @param page - Playwright page object
 * @param selector - Field selector
 * @param value - Value to fill
 */
export async function fillAndVerify(page: Page, selector: string, value: string) {
  await page.fill(selector, value);
  await expect(page.locator(selector)).toHaveValue(value);
}

/**
 * Click element and wait for navigation
 *
 * @param page - Playwright page object
 * @param selector - Element selector
 * @param expectedURL - Expected URL after navigation (string or regex)
 */
export async function clickAndNavigate(
  page: Page,
  selector: string,
  expectedURL: string | RegExp
) {
  await page.click(selector);
  await page.waitForURL(expectedURL);
}
