import { test, expect } from '@playwright/test';

test.describe.serial('Assistant Chat Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/dashboard');
    await page.waitForLoadState('networkidle');
  });

  test('Test 1: Hello buddy - basic chat', async ({ page }) => {
    // Open assistant panel
    await page.click('[data-testid="assistant-button"]');
    await expect(page.locator('[data-testid="assistant-panel"]')).toBeVisible();
    
    // Send first message
    const input = page.locator('[data-testid="assistant-input"]');
    await input.fill('Hello buddy');
    await page.click('[data-testid="assistant-send"]');
    
    // Wait for response (up to 400s)
    await expect(page.locator('[data-testid="assistant-message-assistant"]').last()).toBeVisible({ timeout: 400000 });
    
    // Verify no timeout banner
    await expect(page.locator('[data-testid="assistant-error"]')).not.toBeVisible();
    
    // Verify input re-enabled
    await expect(input).toBeEnabled();
    
    // Verify no credentials in browser
    const pageContent = await page.content();
    expect(pageContent).not.toContain('nvapi-');
    expect(pageContent).not.toContain('NVIDIA_API_KEY');
  });

  test('Test 2: What does headline CPI mean?', async ({ page }) => {
    const input = page.locator('[data-testid="assistant-input"]');
    await input.fill('What does headline CPI mean?');
    await page.click('[data-testid="assistant-send"]');
    
    // Wait for response
    await expect(page.locator('[data-testid="assistant-message-assistant"]').last()).toBeVisible({ timeout: 400000 });
    
    // Verify conceptual explanation badge
    await expect(page.locator('[data-testid="assistant-badge"]').last()).toContainText('Conceptual explanation');
    
    // Verify no timeout banner
    await expect(page.locator('[data-testid="assistant-error"]')).not.toBeVisible();
    
    // Verify input re-enabled
    await expect(input).toBeEnabled();
  });

  test('Test 3: What is India\'s current CPI?', async ({ page }) => {
    const input = page.locator('[data-testid="assistant-input"]');
    await input.fill('What is India\'s current CPI?');
    await page.click('[data-testid="assistant-send"]');
    
    // Wait for response
    await expect(page.locator('[data-testid="assistant-message-assistant"]').last()).toBeVisible({ timeout: 400000 });
    
    // Verify "data not connected" badge
    await expect(page.locator('[data-testid="assistant-badge"]').last()).toContainText('Data not connected');
    
    // Verify no timeout banner
    await expect(page.locator('[data-testid="assistant-error"]')).not.toBeVisible();
    
    // Verify input re-enabled
    await expect(input).toBeEnabled();
    
    // Verify no secrets in backend logs (check via browser console)
    const pageContent = await page.content();
    expect(pageContent).not.toContain('nvapi-');
    expect(pageContent).not.toContain('NVIDIA_API_KEY');
  });
});