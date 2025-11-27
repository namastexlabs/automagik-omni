import { Page, expect } from '@playwright/test';

/**
 * Test helper utilities for Automagik Omni E2E tests
 */

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
