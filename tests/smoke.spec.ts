import { expect, test } from '@playwright/test'

test('home renders one h1', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('h1')).toHaveCount(1)
})
