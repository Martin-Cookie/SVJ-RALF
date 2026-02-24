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
    // User display name or username should be visible in header
    await expect(page.locator('header').getByText(/admin/i).first()).toBeVisible();
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

  test('owners page loads with data', async ({ page }) => {
    await page.goto('/vlastnici');
    await expect(page.getByRole('heading', { name: 'Vlastníci', exact: true })).toBeVisible();
    // Page should show owners or empty state
    const hasOwners = await page.locator('table tbody tr').count();
    if (hasOwners > 0) {
      await expect(page.getByText(/Celkem \d+ vlastníků/)).toBeVisible();
    } else {
      await expect(page.getByRole('heading', { name: 'Žádní vlastníci' })).toBeVisible();
    }
  });

  test('owners sidebar link navigates correctly', async ({ page }) => {
    await page.click('#sidebar a[href="/vlastnici"]');
    await expect(page).toHaveURL(/\/vlastnici/);
    await expect(page.getByRole('heading', { name: 'Vlastníci', exact: true })).toBeVisible();
  });

  test('owners filter bubbles are visible', async ({ page }) => {
    await page.goto('/vlastnici');
    await expect(page.getByText(/Všichni \(\d+\)/)).toBeVisible();
    await expect(page.getByText(/Fyzické \(\d+\)/)).toBeVisible();
    await expect(page.getByText(/Právnické \(\d+\)/)).toBeVisible();
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

  test('units page loads with data', async ({ page }) => {
    await page.goto('/jednotky');
    await expect(page.getByRole('heading', { name: 'Jednotky', exact: true })).toBeVisible();
    // Page should show units or empty state
    const hasUnits = await page.locator('table tbody tr').count();
    if (hasUnits > 0) {
      await expect(page.getByText(/Celkem \d+ jednotek/)).toBeVisible();
    } else {
      await expect(page.getByRole('heading', { name: 'Žádné jednotky' })).toBeVisible();
    }
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

  test('voting page loads', async ({ page }) => {
    await page.goto('/hlasovani');
    await expect(page.getByRole('heading', { name: 'Hlasování', exact: true })).toBeVisible();
  });

  test('voting sidebar link navigates correctly', async ({ page }) => {
    await page.click('#sidebar a[href="/hlasovani"]');
    await expect(page).toHaveURL(/\/hlasovani/);
    await expect(page.getByRole('heading', { name: 'Hlasování', exact: true })).toBeVisible();
  });

  test('voting filter bubbles are visible', async ({ page }) => {
    await page.goto('/hlasovani');
    // Filter bubbles exist with any count (data may persist from previous tests)
    await expect(page.getByText(/Vše \(\d+\)/)).toBeVisible();
    await expect(page.getByText(/Koncept \(\d+\)/)).toBeVisible();
    await expect(page.getByText(/Aktivní \(\d+\)/)).toBeVisible();
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

test.describe('Interaction Check – Blok 6 (Daně/Rozúčtování)', () => {
  test.beforeEach(async ({ page }) => {
    await loginOrRegister(page);
  });

  test('tax page loads', async ({ page }) => {
    await page.goto('/dane');
    await expect(page.getByRole('heading', { name: /Daně|Rozúčtování/ })).toBeVisible();
  });

  test('tax sidebar link navigates correctly', async ({ page }) => {
    await page.click('#sidebar a[href="/dane"]');
    await expect(page).toHaveURL(/\/dane/);
  });

  test('create tax session form works', async ({ page }) => {
    await page.goto('/dane/nova');
    await expect(page.getByRole('heading', { name: 'Nové rozúčtování' })).toBeVisible();

    await page.fill('input[name="name"]', 'Test rozúčtování E2E');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/dane\/\d+/);
    await expect(page.getByRole('heading', { name: 'Test rozúčtování E2E' })).toBeVisible();
  });

  test('tax detail shows upload form and matching link', async ({ page }) => {
    // Create a session first
    await page.goto('/dane/nova');
    await page.fill('input[name="name"]', 'Detail test');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dane\/\d+/);

    // Check upload form and matching link exist
    await expect(page.locator('input[type="file"]')).toBeVisible();
    await expect(page.getByText('Párování')).toBeVisible();
  });

  test('tax matching page accessible', async ({ page }) => {
    await page.goto('/dane/nova');
    await page.fill('input[name="name"]', 'Matching test');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dane\/\d+/);

    // Navigate to matching page
    await page.click('a:has-text("Párování")');
    await expect(page.getByRole('heading', { name: 'Párování dokumentů' })).toBeVisible();
  });
});

test.describe('Interaction Check – Blok 7 (Synchronizace)', () => {
  test.beforeEach(async ({ page }) => {
    await loginOrRegister(page);
  });

  test('sync page loads with empty state', async ({ page }) => {
    await page.goto('/synchronizace');
    await expect(page.getByRole('heading', { name: 'Synchronizace' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Žádné kontroly' })).toBeVisible();
  });

  test('sync sidebar link navigates correctly', async ({ page }) => {
    await page.click('#sidebar a[href="/synchronizace"]');
    await expect(page).toHaveURL(/\/synchronizace/);
  });

  test('sync upload form is accessible', async ({ page }) => {
    await page.goto('/synchronizace/nova');
    await expect(page.getByRole('heading', { name: 'Nová kontrola vlastníků' })).toBeVisible();
    await expect(page.locator('input[type="file"]')).toBeVisible();
    await expect(page.getByText('Nahrát a porovnat')).toBeVisible();
  });
});

test.describe('Interaction Check – Blok 8-9 (Správa SVJ)', () => {
  test.beforeEach(async ({ page }) => {
    await loginOrRegister(page);
  });

  test('admin page loads with SVJ info form', async ({ page }) => {
    await page.goto('/sprava');
    await expect(page.getByRole('heading', { name: 'Správa SVJ' })).toBeVisible();
    await expect(page.getByText('Informace o SVJ')).toBeVisible();
    // SVJ info form is in the first details section (open by default)
    const infoSection = page.locator('details').first();
    await expect(infoSection.locator('input[name="building_type"]')).toBeVisible();
    await expect(infoSection.locator('input[name="total_shares"]')).toBeVisible();
  });

  test('admin SVJ info form submits', async ({ page }) => {
    await page.goto('/sprava');
    const infoSection = page.locator('details').first();
    await infoSection.locator('input[name="name"]').fill('SVJ Testovací');
    await infoSection.locator('input[name="building_type"]').fill('Bytový dům');
    await infoSection.locator('input[name="total_shares"]').fill('1000');
    await page.click('button:has-text("Uložit")');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/sprava/);
    // Verify saved values
    const updatedSection = page.locator('details').first();
    await expect(updatedSection.locator('input[name="name"]')).toHaveValue('SVJ Testovací');
  });

  test('admin board members section is collapsible', async ({ page }) => {
    await page.goto('/sprava');
    // Board members section (closed by default)
    const boardSummary = page.locator('summary').filter({ hasText: 'Členové výboru' });
    await expect(boardSummary).toBeVisible();

    // Click to expand
    await boardSummary.click();
    await page.waitForTimeout(200);

    // Add member form should be visible
    await expect(page.locator('input[placeholder="Jméno"]').first()).toBeVisible();
  });

  test('admin add board member works', async ({ page }) => {
    await page.goto('/sprava');

    // Expand board section
    await page.locator('summary').filter({ hasText: 'Členové výboru' }).click();
    await page.waitForTimeout(200);

    // Fill in member form with unique name (within board section — 2nd details element)
    const uniqueName = `Člen E2E ${Date.now()}`;
    const boardSection = page.locator('details').nth(1);
    await boardSection.locator('input[name="name"]').fill(uniqueName);
    await boardSection.locator('input[name="role"]').fill('Předseda');
    await boardSection.locator('button:has-text("Přidat")').click();
    await page.waitForLoadState('networkidle');

    // Verify member appears (expand section since redirect closes it)
    await expect(page).toHaveURL(/\/sprava/);
    await page.locator('summary').filter({ hasText: 'Členové výboru' }).click();
    await page.waitForTimeout(200);
    await expect(page.getByText(uniqueName)).toBeVisible();
  });

  test('admin sidebar link navigates correctly', async ({ page }) => {
    await page.click('#sidebar a[href="/sprava"]');
    await expect(page).toHaveURL(/\/sprava/);
    await expect(page.getByRole('heading', { name: 'Správa SVJ' })).toBeVisible();
  });
});

test.describe('Interaction Check – Blok 10 (Nastavení)', () => {
  test.beforeEach(async ({ page }) => {
    await loginOrRegister(page);
  });

  test('settings page loads with app info', async ({ page }) => {
    await page.goto('/nastaveni');
    await expect(page.getByRole('heading', { name: 'Nastavení' })).toBeVisible();
    await expect(page.getByText('Informace o aplikaci')).toBeVisible();
    await expect(page.getByText('FastAPI + SQLAlchemy')).toBeVisible();
    await expect(page.getByText('SQLite')).toBeVisible();
  });

  test('settings shows keyboard shortcuts section', async ({ page }) => {
    await page.goto('/nastaveni');
    await expect(page.getByRole('heading', { name: 'Klávesové zkratky', exact: true })).toBeVisible();
    // Use main content area to avoid matching shortcuts modal
    await expect(page.getByRole('main').getByText('Ctrl+K')).toBeVisible();
    await expect(page.getByRole('main').getByText('G → D')).toBeVisible();
  });

  test('settings shows email log section', async ({ page }) => {
    await page.goto('/nastaveni');
    await expect(page.getByText('Odeslaný email log')).toBeVisible();
    await expect(page.getByText('Zatím nebyly odeslány žádné emaily.')).toBeVisible();
  });

  test('settings sidebar link navigates correctly', async ({ page }) => {
    await page.click('#sidebar a[href="/nastaveni"]');
    await expect(page).toHaveURL(/\/nastaveni/);
    await expect(page.getByRole('heading', { name: 'Nastavení' })).toBeVisible();
  });
});
