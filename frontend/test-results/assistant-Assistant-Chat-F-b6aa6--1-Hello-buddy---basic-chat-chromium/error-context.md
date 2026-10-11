# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: assistant.spec.ts >> Assistant Chat Flow >> Test 1: Hello buddy - basic chat
- Location: tests\assistant.spec.ts:9:7

# Error details

```
Error: expect(locator).toBeEnabled() failed

Locator:  locator('[data-testid="assistant-input"]')
Expected: enabled
Received: disabled
Timeout:  5000ms

Call log:
  - Expect "toBeEnabled" locator('[data-testid="assistant-input"]') with timeout 5000ms
  - waiting for locator('[data-testid="assistant-input"]')
    14 × locator resolved to <textarea rows="1" disabled data-testid="assistant-input" aria-label="Message Policy Assistant" placeholder="Ask about this page... (Enter to send, Shift+Enter for new line)" class="w-full min-h-[44px] max-h-[160px] resize-none rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 pr-12 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-300/30 disabled:cursor-not-allowed disabled:opacity-50"></textarea>
       - unexpected value "disabled"

```

```yaml
- textbox "Message Policy Assistant" [disabled]:
  - /placeholder: Ask about this page... (Enter to send, Shift+Enter for new line)
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe.serial('Assistant Chat Flow', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     await page.goto('http://localhost:3000/dashboard');
  6  |     await page.waitForLoadState('networkidle');
  7  |   });
  8  | 
  9  |   test('Test 1: Hello buddy - basic chat', async ({ page }) => {
  10 |     // Open assistant panel
  11 |     await page.click('[data-testid="assistant-button"]');
  12 |     await expect(page.locator('[data-testid="assistant-panel"]')).toBeVisible();
  13 |     
  14 |     // Send first message
  15 |     const input = page.locator('[data-testid="assistant-input"]');
  16 |     await input.fill('Hello buddy');
  17 |     await page.click('[data-testid="assistant-send"]');
  18 |     
  19 |     // Wait for response (up to 400s)
  20 |     await expect(page.locator('[data-testid="assistant-message-assistant"]').last()).toBeVisible({ timeout: 400000 });
  21 |     
  22 |     // Verify no timeout banner
  23 |     await expect(page.locator('[data-testid="assistant-error"]')).not.toBeVisible();
  24 |     
  25 |     // Verify input re-enabled
> 26 |     await expect(input).toBeEnabled();
     |                         ^ Error: expect(locator).toBeEnabled() failed
  27 |     
  28 |     // Verify no credentials in browser
  29 |     const pageContent = await page.content();
  30 |     expect(pageContent).not.toContain('nvapi-');
  31 |     expect(pageContent).not.toContain('NVIDIA_API_KEY');
  32 |   });
  33 | 
  34 |   test('Test 2: What does headline CPI mean?', async ({ page }) => {
  35 |     const input = page.locator('[data-testid="assistant-input"]');
  36 |     await input.fill('What does headline CPI mean?');
  37 |     await page.click('[data-testid="assistant-send"]');
  38 |     
  39 |     // Wait for response
  40 |     await expect(page.locator('[data-testid="assistant-message-assistant"]').last()).toBeVisible({ timeout: 400000 });
  41 |     
  42 |     // Verify conceptual explanation badge
  43 |     await expect(page.locator('[data-testid="assistant-badge"]').last()).toContainText('Conceptual explanation');
  44 |     
  45 |     // Verify no timeout banner
  46 |     await expect(page.locator('[data-testid="assistant-error"]')).not.toBeVisible();
  47 |     
  48 |     // Verify input re-enabled
  49 |     await expect(input).toBeEnabled();
  50 |   });
  51 | 
  52 |   test('Test 3: What is India\'s current CPI?', async ({ page }) => {
  53 |     const input = page.locator('[data-testid="assistant-input"]');
  54 |     await input.fill('What is India\'s current CPI?');
  55 |     await page.click('[data-testid="assistant-send"]');
  56 |     
  57 |     // Wait for response
  58 |     await expect(page.locator('[data-testid="assistant-message-assistant"]').last()).toBeVisible({ timeout: 400000 });
  59 |     
  60 |     // Verify "data not connected" badge
  61 |     await expect(page.locator('[data-testid="assistant-badge"]').last()).toContainText('Data not connected');
  62 |     
  63 |     // Verify no timeout banner
  64 |     await expect(page.locator('[data-testid="assistant-error"]')).not.toBeVisible();
  65 |     
  66 |     // Verify input re-enabled
  67 |     await expect(input).toBeEnabled();
  68 |     
  69 |     // Verify no secrets in backend logs (check via browser console)
  70 |     const pageContent = await page.content();
  71 |     expect(pageContent).not.toContain('nvapi-');
  72 |     expect(pageContent).not.toContain('NVIDIA_API_KEY');
  73 |   });
  74 | });
```