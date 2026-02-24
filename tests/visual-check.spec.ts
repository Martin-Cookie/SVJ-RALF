import { test } from '@playwright/test';

const viewports = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
];

const ITER = process.env.ITER || '1';
const PHASE = process.env.PHASE || 'build';

test.describe('Visual Check', () => {
  for (const vp of viewports) {
    test(`${vp.name} screenshot`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      // Try to go to dashboard first
      await page.goto('/');
      await page.waitForLoadState('domcontentloaded');

      // If redirected to registration page, register
      if (page.url().includes('registrace')) {
        await page.fill('input[name="username"]', 'admin');
        await page.fill('input[name="password"]', 'testpass123');
        await page.fill('input[name="display_name"]', 'Test Admin');
        await page.click('button[type="submit"]');
        await page.waitForLoadState('domcontentloaded');
      }

      // If on login page, login
      if (page.url().includes('login')) {
        await page.fill('input[name="username"]', 'admin');
        await page.fill('input[name="password"]', 'testpass123');
        await page.click('button[type="submit"]');
        await page.waitForLoadState('domcontentloaded');
      }

      // Now on dashboard
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: `screenshots/iter-${ITER}-${PHASE}-${vp.name}-dashboard.png`,
        fullPage: true,
      });

      // Owners page (empty state)
      await page.goto('/vlastnici');
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: `screenshots/iter-${ITER}-${PHASE}-${vp.name}-owners.png`,
        fullPage: true,
      });

      // Units page
      await page.goto('/jednotky');
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: `screenshots/iter-${ITER}-${PHASE}-${vp.name}-units.png`,
        fullPage: true,
      });

      // Voting page
      await page.goto('/hlasovani');
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: `screenshots/iter-${ITER}-${PHASE}-${vp.name}-voting.png`,
        fullPage: true,
      });

      // Tax page
      await page.goto('/dane');
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: `screenshots/iter-${ITER}-${PHASE}-${vp.name}-tax.png`,
        fullPage: true,
      });

      // Sync page
      await page.goto('/synchronizace');
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: `screenshots/iter-${ITER}-${PHASE}-${vp.name}-sync.png`,
        fullPage: true,
      });

      // Admin page
      await page.goto('/sprava');
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: `screenshots/iter-${ITER}-${PHASE}-${vp.name}-admin.png`,
        fullPage: true,
      });

      // Settings page
      await page.goto('/nastaveni');
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: `screenshots/iter-${ITER}-${PHASE}-${vp.name}-settings.png`,
        fullPage: true,
      });

      // Login page
      await page.goto('/logout');
      await page.waitForLoadState('networkidle');
      await page.screenshot({
        path: `screenshots/iter-${ITER}-${PHASE}-${vp.name}-login.png`,
        fullPage: true,
      });
    });
  }
});
