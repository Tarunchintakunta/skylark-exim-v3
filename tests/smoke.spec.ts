import { expect, test } from '@playwright/test'

const ready = (page: import('@playwright/test').Page) => page.waitForFunction(() => document.documentElement.dataset.ready === '1')

test('loads, loader completes, one h1', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  await expect(page.locator('h1')).toHaveCount(1)
  await expect(page.locator('.loader')).toHaveCount(0)
  await expect(page.locator('html')).not.toHaveClass(/is-locked/)
})

test('path buttons switch the chapter list and the hash', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  const ocean = page.getByRole('button', { name: /^the ocean/i })
  const pond = page.getByRole('button', { name: /^the pond/i })
  await expect(ocean).toHaveAttribute('aria-pressed', 'true')
  await pond.click()
  await expect(pond).toHaveAttribute('aria-pressed', 'true')
  await expect(page).toHaveURL(/#pond$/)
  await expect(page.locator('[data-chapter="p1"]')).toHaveCount(1)
  await expect(page.locator('[data-chapter="o1"]')).toHaveCount(0)
  await page.keyboard.press('ArrowLeft')
  await expect(ocean).toHaveAttribute('aria-pressed', 'true')
  await expect(page.locator('[data-chapter="o1"]')).toHaveCount(1)
})

test('RFQ shows validation errors, then falls back to a pre-filled mailto', async ({ page }) => {
  await page.route('**/api/rfq', (r) => r.fulfill({ json: { ok: false, fallback: 'mailto' } }))
  await page.goto('/')
  await ready(page)
  await page.evaluate(() => document.getElementById('quote')!.scrollIntoView())
  const form = page.locator('form.rfq')
  await form.getByRole('button', { name: 'Send request' }).click()
  await expect(form.getByRole('alert').first()).toBeVisible()
  await form.getByLabel('Name').fill('Test Buyer')
  await form.getByLabel('Company').fill('Test Imports')
  await form.getByLabel('Country').fill('Japan')
  await form.getByLabel('Email').fill('buyer@example.com')
  await form.getByRole('button', { name: 'Send request' }).click()
  const link = page.getByRole('link', { name: 'open the pre-filled email' })
  await expect(link).toHaveAttribute('href', /^mailto:info@skylarkexim\.com\?subject=Export%20quote%20request/)
})

test('every nav link lands on its section', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  for (const id of ['products', 'why', 'about', 'quote']) {
    await page.locator(`.nav a[href="#${id}"]`).click()
    await page.waitForTimeout(1800)
    const top = await page.locator(`#${id}`).evaluate((el) => el.getBoundingClientRect().top)
    expect(Math.abs(top)).toBeLessThan(80)
  }
})
