# E2E Testing Guide

Comprehensive end-to-end testing for Automagik Omni UI using Playwright.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Debugging](#debugging)
- [CI/CD Integration](#cicd-integration)
- [Best Practices](#best-practices)

## Quick Start

```bash
# Install dependencies
cd resources/ui
npm install

# Run visual tests (headed mode - watch the browser)
make play

# Run quick smoke tests
make play-quick

# Run tests in headless mode (for CI)
make test-ui
```

## Test Structure

```
e2e/
├── fixtures.ts           # Shared test fixtures (authenticated page, etc.)
├── utils/
│   └── test-helpers.ts   # Reusable utility functions
├── smoke/                # Quick smoke tests (~2 minutes)
│   ├── auth.spec.ts      # Authentication critical path (5 tests)
│   ├── navigation.spec.ts # Page navigation (7 tests)
│   └── health.spec.ts    # Service health checks (7 tests)
└── full/                 # Comprehensive test suites (~5-10 minutes)
    ├── global-settings.spec.ts  # Global Settings page (13 tests)
    ├── instances.spec.ts        # Instances management (12 tests)
    ├── theme.spec.ts            # Dark/light mode (8 tests)
    └── accessibility.spec.ts    # WCAG compliance (15 tests)
```

### Test Categories

**Smoke Tests** (`e2e/smoke/`)
- Critical path validation
- Fast execution (<2 minutes)
- Run on every commit
- Tagged with `@smoke` for filtering

**Comprehensive Tests** (`e2e/full/`)
- Full feature coverage
- Detailed validation
- Run before releases and in CI
- Include edge cases and error scenarios

## Running Tests

### Local Development

**Visual Testing (Headed Mode)**

Watch tests execute in a real browser:

```bash
# Comprehensive tests
make play
# or
npm run test:e2e:ui

# Quick smoke tests only
make play-quick
# or
npm run test:quick:ui
```

**Headless Mode**

Run tests in the background (faster):

```bash
# All tests
make test-ui
# or
npm run test:e2e

# Smoke tests only
make test-ui-quick
# or
npm run test:quick
```

### Environment Setup

Tests use `.env.test` configuration:

```env
VITE_API_URL=http://localhost:8882
VITE_PORT=9882
```

Set `TEST_API_KEY` environment variable:

```bash
export TEST_API_KEY=your-test-api-key
```

### Test Reports

Playwright generates HTML reports after each run:

```bash
# View the latest report
npx playwright show-report
```

Reports include:
- Test execution timeline
- Screenshots on failure
- Video recordings (on failure)
- Network activity
- Console logs

## Writing Tests

### Using Fixtures

All tests should use the `authenticatedPage` fixture for authenticated routes:

```typescript
import { test, expect } from '../fixtures';

test('my test', async ({ authenticatedPage }) => {
  // Page is already logged in and on /dashboard
  await authenticatedPage.goto('/settings');
  // Test your feature...
});
```

### Using Helper Functions

Import utilities from `utils/test-helpers.ts`:

```typescript
import { waitForToast, fillAndVerify, clickAndNavigate } from '../utils/test-helpers';

test('submit form', async ({ authenticatedPage }) => {
  await fillAndVerify(authenticatedPage, '#input', 'value');
  await clickAndNavigate(authenticatedPage, 'button', '/success');
  await waitForToast(authenticatedPage, 'Success!');
});
```

### Test Naming Conventions

Use descriptive test names that explain what's being validated:

```typescript
// Good
test('login with valid credentials redirects to dashboard', async ({ page }) => {
  // ...
});

// Bad
test('login test', async ({ page }) => {
  // ...
});
```

### Tagging Tests

Tag smoke tests for quick execution:

```typescript
test('critical feature works @smoke', async ({ authenticatedPage }) => {
  // ...
});
```

Run tagged tests:

```bash
npm run test:quick     # Run @smoke tests
```

## Debugging

### Debug Mode

Run Playwright in debug mode with inspector:

```bash
npx playwright test --debug
```

### Headed Mode with Slow Motion

Watch tests execute slowly:

```bash
npx playwright test --headed --slow-mo=1000
```

### Screenshots and Videos

Playwright automatically captures:
- Screenshots on failure (`.screenshot` option)
- Videos on failure (`.video` option)
- Full page traces on retry (`.trace` option)

Find artifacts in:
- `playwright-report/` - HTML report
- `test-results/` - Videos and screenshots

### Console Logs

View browser console in test output:

```typescript
page.on('console', msg => console.log(msg.text()));
```

### Selective Test Execution

Run specific tests:

```bash
# Single file
npx playwright test auth.spec.ts

# Single test
npx playwright test -g "login with valid credentials"

# Exclude tests
npx playwright test --grep-invert @slow
```

## CI/CD Integration

Tests run automatically in GitHub Actions on:
- Pull requests to `main` or `dev`
- Pushes to `dev` branch

### Workflow Jobs

**`test-ui` Job** (`.github/workflows/pr-tests.yml`)

```yaml
- Checkout code
- Setup Node.js 20
- Install UI dependencies
- Install Playwright browsers
- Setup Python 3.12 backend
- Start backend services (SQLite)
- Run Playwright tests (headless)
- Upload test reports (7 day retention)
- Upload videos on failure
```

### Test Artifacts

Failed test artifacts are uploaded to GitHub:
- **Playwright Report** - Full HTML report (always uploaded)
- **Videos** - Test execution videos (failure only)

Access artifacts from the GitHub Actions run summary.

### Environment Variables

CI sets these automatically:

```yaml
CI: true
TEST_API_KEY: test-api-key-for-playwright
DATABASE_URL: sqlite:///data/test.db
```

## Best Practices

### 1. Use Fixtures for Common Setup

Define fixtures in `fixtures.ts` for reusable setup:

```typescript
export const test = base.extend<Fixtures>({
  authenticatedPage: async ({ page }, use) => {
    // Login logic
    await use(page);
  },
});
```

### 2. Wait for Elements, Don't Use Timeouts

```typescript
// Good
await expect(page.locator('.element')).toBeVisible();

// Bad
await page.waitForTimeout(2000);
```

### 3. Use Specific Selectors

```typescript
// Good - specific and resilient
await page.locator('button[aria-label="Submit form"]').click();
await page.locator('[data-testid="login-button"]').click();

// Bad - fragile and non-specific
await page.locator('.btn-primary').click();
```

### 4. Test User Flows, Not Implementation

Focus on what users do, not how the code works:

```typescript
// Good - tests user behavior
test('user can log in and view dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[name="apiKey"]', 'valid-key');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('/dashboard');
});

// Bad - tests internal implementation
test('AuthService.login() is called', async ({ page }) => {
  // Don't test internal methods
});
```

### 5. Keep Tests Independent

Each test should run in isolation:

```typescript
// Good - self-contained
test('delete instance', async ({ authenticatedPage }) => {
  // Create test data
  const instance = await createTestInstance();

  // Test deletion
  await authenticatedPage.goto(`/instances/${instance.id}`);
  await authenticatedPage.click('[aria-label="Delete"]');

  // Verify
  await expect(page.locator('.instance')).not.toBeVisible();
});

// Bad - depends on previous test
test('create instance', async ({ authenticatedPage }) => {
  // Creates instance
});

test('delete instance', async ({ authenticatedPage }) => {
  // Assumes instance from previous test exists
});
```

### 6. Use Soft Assertions for Non-Critical Checks

```typescript
// Multiple validations - continue on failure
await expect.soft(page.locator('.title')).toBeVisible();
await expect.soft(page.locator('.description')).toBeVisible();
await expect(page.locator('.content')).toBeVisible(); // Hard assertion
```

### 7. Handle Flaky Tests

Use retries and auto-waiting:

```typescript
// Playwright auto-waits for elements
await page.click('button'); // Waits for button to be visible and enabled

// Configure retries in playwright.config.ts
retries: process.env.CI ? 2 : 0
```

### 8. Test Accessibility

Include accessibility checks in your tests:

```typescript
test('form has proper labels', async ({ authenticatedPage }) => {
  const input = authenticatedPage.locator('input[name="email"]');
  const label = authenticatedPage.locator('label[for="email"]');

  await expect(label).toBeVisible();
  await expect(input).toHaveAttribute('aria-label');
});
```

### 9. Clean Up Test Data

Ensure tests clean up after themselves:

```typescript
test('create and delete instance', async ({ authenticatedPage }) => {
  let instanceId: string;

  try {
    // Create
    instanceId = await createInstance();

    // Test
    await authenticatedPage.goto(`/instances/${instanceId}`);
    // ...
  } finally {
    // Cleanup
    if (instanceId) {
      await deleteInstance(instanceId);
    }
  }
});
```

### 10. Use Page Object Pattern for Complex Pages

For complex pages, create page objects:

```typescript
// pages/SettingsPage.ts
export class SettingsPage {
  constructor(private page: Page) {}

  async toggleTheme() {
    await this.page.click('[aria-label="Toggle theme"]');
  }

  async updateSetting(name: string, value: string) {
    await this.page.fill(`[name="${name}"]`, value);
    await this.page.click('button[type="submit"]');
  }
}

// In test
import { SettingsPage } from './pages/SettingsPage';

test('update setting', async ({ authenticatedPage }) => {
  const settings = new SettingsPage(authenticatedPage);
  await settings.updateSetting('apiKey', 'new-key');
});
```

## Test Coverage

Current test coverage:

- **Authentication** (5 tests) - Login, logout, protected routes
- **Navigation** (7 tests) - Page routing, breadcrumbs, sidebar
- **Health Checks** (7 tests) - API status, UI loading, error handling
- **Global Settings** (13 tests) - Settings CRUD, filtering, history
- **Instances** (12 tests) - Instance management, status, actions
- **Theme** (8 tests) - Dark/light mode, persistence, accessibility
- **Accessibility** (15 tests) - WCAG compliance, keyboard nav, screen readers

**Total: 67 tests** covering critical user flows and comprehensive features.

## Additional Resources

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright API Reference](https://playwright.dev/docs/api/class-playwright)
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
