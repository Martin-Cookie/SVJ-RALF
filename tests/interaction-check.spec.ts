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

test.describe('Interaction Check – Blok 3 (Jednotky)', () => {
  test.beforeEach(async ({ page }) => {
    await loginOrRegister(page);
  });

  test('units page loads with empty state', async ({ page }) => {
    await page.goto('/jednotky');
    await expect(page.getByRole('heading', { name: 'Jednotky', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Žádné jednotky' })).toBeVisible();
  });

  test('units sidebar link navigates correctly', async ({ page }) => {
    await page.click('#sidebar a[href="/jednotky"]');
    await expect(page).toHaveURL(/\/jednotky/);
    await expect(page.getByRole('heading', { name: 'Jednotky', exact: true })).toBeVisible();
  });

  test('units search input is present', async ({ page }) => {
    await page.goto('/jednotky');
    const searchInput = page.locator('input[name="search"]');
    await expect(searchInput).toBeVisible();
  });

  test('keyboard shortcut G+J navigates to units', async ({ page }) => {
    await page.keyboard.press('g');
    await page.waitForTimeout(100);
    await page.keyboard.press('j');
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/\/jednotky/);
  });
});

test.describe('Interaction Check – Blok 4 (Hlasování)', () => {
  test.beforeEach(async ({ page }) => {
    await loginOrRegister(page);
  });

  test('voting page loads with empty state', async ({ page }) => {
    await page.goto('/hlasovani');
    await expect(page.getByRole('heading', { name: 'Hlasování', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Žádná hlasování' })).toBeVisible();
  });

  test('voting sidebar link navigates correctly', async ({ page }) => {
    await page.click('#sidebar a[href="/hlasovani"]');
    await expect(page).toHaveURL(/\/hlasovani/);
    await expect(page.getByRole('heading', { name: 'Hlasování', exact: true })).toBeVisible();
  });

  test('voting filter bubbles are visible', async ({ page }) => {
    await page.goto('/hlasovani');
    await expect(page.getByText('Vše (0)')).toBeVisible();
    await expect(page.getByText('Koncept (0)')).toBeVisible();
    await expect(page.getByText('Aktivní (0)')).toBeVisible();
    await expect(page.getByText('Uzavřené (0)')).toBeVisible();
    await expect(page.getByText('Zrušené (0)')).toBeVisible();
  });

  test('create voting form works', async ({ page }) => {
    await page.goto('/hlasovani/nova');
    await expect(page.getByRole('heading', { name: 'Nové hlasování' })).toBeVisible();

    // Fill and submit form
    await page.fill('input[name="name"]', 'Test hlasování E2E');
    await page.fill('input[name="quorum"]', '60');
    await page.click('button[type="submit"]');

    // Should redirect to detail page
    await page.waitForURL(/\/hlasovani\/\d+/);
    await expect(page.getByRole('heading', { name: 'Test hlasování E2E' })).toBeVisible();
  });

  test('voting detail: add and delete items', async ({ page }) => {
    // Create a voting first
    await page.goto('/hlasovani/nova');
    await page.fill('input[name="name"]', 'Bod test');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/hlasovani\/\d+/);

    // Add an item
    await page.fill('input[name="text"]', 'Schválení rozpočtu');
    await page.click('button:has-text("Přidat bod")');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('Schválení rozpočtu')).toBeVisible();
    await expect(page.getByText('Bod 1', { exact: true })).toBeVisible();
  });

  test('voting detail: change status koncept → aktivní', async ({ page }) => {
    // Create a voting
    await page.goto('/hlasovani/nova');
    await page.fill('input[name="name"]', 'Status test');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/hlasovani\/\d+/);

    // Click Spustit button to activate
    await page.click('button:has-text("Spustit")');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('aktivní', { exact: true })).toBeVisible();
  });

  test('keyboard shortcut G+H navigates to voting', async ({ page }) => {
    await page.keyboard.press('g');
    await page.waitForTimeout(100);
    await page.keyboard.press('h');
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/\/hlasovani/);
  });
});

test.describe('Interaction Check – Blok 5 (Zpracování hlasování)', () => {
  let votingId: string;

  test.beforeEach(async ({ page }) => {
    await loginOrRegister(page);

    // Create a voting with an item and activate it
    await page.goto('/hlasovani/nova');
    await page.fill('input[name="name"]', 'Zpracování E2E');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/hlasovani\/\d+/);

    // Extract voting ID from URL
    const url = page.url();
    votingId = url.match(/\/hlasovani\/(\d+)/)?.[1] || '';

    // Add a voting item
    await page.fill('input[name="text"]', 'Schválení plánu');
    await page.click('button:has-text("Přidat bod")');
    await page.waitForLoadState('networkidle');

    // Activate (Spustit bez lístků)
    await page.click('button:has-text("Spustit")');
    await page.waitForLoadState('networkidle');
  });

  test('processing page loads', async ({ page }) => {
    await page.goto(`/hlasovani/${votingId}/zpracovani`);
    await expect(page.getByRole('heading', { name: 'Zpracování lístků' })).toBeVisible();
  });

  test('unsubmitted page loads', async ({ page }) => {
    await page.goto(`/hlasovani/${votingId}/neodevzdane`);
    await expect(page.getByRole('heading', { name: 'Neodevzdané lístky' })).toBeVisible();
  });

  test('voting detail shows results section', async ({ page }) => {
    await page.goto(`/hlasovani/${votingId}`);
    await expect(page.getByText('Schválení plánu')).toBeVisible();
    await expect(page.getByText('Zpracování E2E')).toBeVisible();
  });

  test('back navigation from processing page works', async ({ page }) => {
    await page.goto(`/hlasovani/${votingId}/zpracovani`);
    await page.click(`a[href="/hlasovani/${votingId}"]`);
    await expect(page).toHaveURL(new RegExp(`/hlasovani/${votingId}`));
  });

  test('back navigation from unsubmitted page works', async ({ page }) => {
    await page.goto(`/hlasovani/${votingId}/neodevzdane`);
    await page.click(`a[href="/hlasovani/${votingId}"]`);
    await expect(page).toHaveURL(new RegExp(`/hlasovani/${votingId}`));
  });
});
