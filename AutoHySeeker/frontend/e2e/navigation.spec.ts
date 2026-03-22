import { test, expect } from '@playwright/test';

test.describe('Phase 1 Frontend Navigation E2E', () => {

  test('should navigate to Overview page by default', async ({ page }) => {
    await page.goto('/');
    
    // Check if the page title or a known element is visible
    // Depending on what Overview has. Assuming there's a heading or it redirects to dashboard.
    // The AppShell sidebar should be visible.
    const navExperiment = page.locator('nav').locator('text=Experiments').or(page.locator('nav').locator('text=实验'));
    await expect(navExperiment).toBeVisible();
  });

  test('should navigate to Experiments page', async ({ page }) => {
    await page.goto('/experiments');
    // Check for the heading in Experiments page
    const heading = page.getByRole('heading', { name: /Experiments|实验列表|实验/i });
    await expect(heading).toBeVisible();
  });

  test('should navigate to Diagnostics page', async ({ page }) => {
    await page.goto('/diagnostics');
    // Check for the heading in Diagnostics
    const heading = page.getByRole('heading', { name: /Diagnostics|系统诊断|硬件/i });
    await expect(heading).toBeVisible();
  });

  test('should navigate to Settings page', async ({ page }) => {
    await page.goto('/settings');
    const heading = page.getByRole('heading', { name: /Settings|设置/i }).first();
    await expect(heading).toBeVisible();
  });

  test('should navigate to Knowledge Hub page', async ({ page }) => {
    await page.goto('/knowledge');
    const heading = page.getByRole('heading', { name: /Knowledge|知识/i });
    await expect(heading).toBeVisible();
  });

});
