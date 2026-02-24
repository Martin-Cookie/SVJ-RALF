import { test, expect } from '@playwright/test';

async function loginOrRegister(page) {
  await page.goto('http://localhost:8000/');
  await page.waitForLoadState('domcontentloaded');

  // Registration flow (first time)
  if (page.url().includes('registrace')) {
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'testpass123');
    await page.fill('input[name="display_name"]', 'Test Admin');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/');
  }

  // Login flow
  if (page.url().includes('login')) {
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/');
  }

  // Ensure we're on dashboard
  await page.waitForLoadState('networkidle');
  // Verify we're not stuck on auth pages
  expect(page.url()).not.toContain('login');
  expect(page.url()).not.toContain('registrace');
}

test.describe('Interaction Check – Blok 1', () => {
  test.beforeEach(async ({ page }) => {
    await loginOrRegister(page);
  });

  test('dashboard loads with stats', async ({ page }) => {
    // The heading exists in the dashboard template
    const heading = page.getByRole('heading', { name: 'Dashboard' });
    await expect(heading).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Vlastníků', { exact: true })).toBeVisible();
    await expect(page.getByText('Jednotek', { exact: true })).toBeVisible();
  });

  test('sidebar navigation works', async ({ page }) => {
    const sidebarLinks = page.locator('#sidebar a');
    const count = await sidebarLinks.count();
    expect(count).toBeGreaterThanOrEqual(5);

    await page.click('#sidebar a[href="/"]');
    await expect(page).toHaveURL('http://localhost:8000/');
  });

  test('dark mode toggle works', async ({ page }) => {
    const html = page.locator('html');
    await page.click('#dark-toggle');
    await expect(html).toHaveClass(/dark/);
    await page.click('#dark-toggle');
    await expect(html).not.toHaveClass(/dark/);
  });

  test('keyboard shortcuts modal opens', async ({ page }) => {
    // Type ? character (which triggers the shortcut in app.js)
    await page.keyboard.type('?');
    await page.waitForTimeout(300);

    const modal = page.locator('#shortcuts-modal');
    // Modal should be visible (class 'flex' added, 'hidden' removed)
    await expect(page.getByRole('heading', { name: 'Klávesové zkratky' })).toBeVisible({ timeout: 3000 });

    // Press Escape to close
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
  });

  test('search bar focuses with Ctrl+K', async ({ page }) => {
    await page.keyboard.press('Control+k');
    const searchInput = page.locator('#global-search');
    await expect(searchInput).toBeFocused();
  });

  test('logout works', async ({ page }) => {
    await page.click('a[href="/logout"]');
    await expect(page).toHaveURL(/\/login/);
  });

  test('user info displayed in header', async ({ page }) => {
    await expect(page.getByText('Test Admin')).toBeVisible();
  });

  test('search page works', async ({ page }) => {
    await page.goto('/hledani?q=test');
    await expect(page.getByRole('heading', { name: 'Výsledky hledání' })).toBeVisible();
  });

  test('notifications page loads', async ({ page }) => {
    await page.goto('/notifikace');
    await expect(page.getByRole('heading', { name: 'Notifikace' })).toBeVisible();
    await expect(page.getByText('Žádné notifikace')).toBeVisible();
  });
});

test.describe('Interaction Check – Blok 2 (Vlastníci)', () => {
  test.beforeEach(async ({ page }) => {
    await loginOrRegister(page);
  });

  test('owners page loads with empty state', async ({ page }) => {
    await page.goto('/vlastnici');
    await expect(page.getByRole('heading', { name: 'Vlastníci', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Žádní vlastníci' })).toBeVisible();
  });

  test('owners sidebar link navigates correctly', async ({ page }) => {
    await page.click('#sidebar a[href="/vlastnici"]');
    await expect(page).toHaveURL(/\/vlastnici/);
    await expect(page.getByRole('heading', { name: 'Vlastníci', exact: true })).toBeVisible();
  });

  test('owners filter bubbles are visible', async ({ page }) => {
    await page.goto('/vlastnici');
    await expect(page.getByText('Všichni (0)')).toBeVisible();
    await expect(page.getByText('Fyzické (0)')).toBeVisible();
    await expect(page.getByText('Právnické (0)')).toBeVisible();
  });

  test('owners search input is present', async ({ page }) => {
    await page.goto('/vlastnici');
    const searchInput = page.locator('input[name="search"]');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('test');
    await searchInput.press('Enter');
    await expect(page).toHaveURL(/search=test/);
  });

  test('owners export button is visible', async ({ page }) => {
    await page.goto('/vlastnici');
    const exportLink = page.getByRole('link', { name: 'Export' });
    await expect(exportLink).toBeVisible();
  });

  test('keyboard shortcut G+V navigates to owners', async ({ page }) => {
    await page.keyboard.press('g');
    await page.waitForTimeout(100);
    await page.keyboard.press('v');
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/\/vlastnici/);
  });
});
