import { expect, test } from '@playwright/test'

const ready = (page: import('@playwright/test').Page) => page.waitForFunction(() => document.documentElement.dataset.ready === '1')

test('loads, loader completes, one h1', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  await expect(page.locator('h1')).toHaveCount(1)
  await expect(page.locator('.loader')).toHaveCount(0)
  await expect(page.locator('html')).not.toHaveClass(/is-locked/)
})

test('header toggle switches which origin runs first and keeps the hash; Ocean is the default', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  const ocean = page.getByRole('group', { name: 'Story path' }).getByRole('link', { name: 'Wild catch' })
  const pond = page.getByRole('group', { name: 'Story path' }).getByRole('link', { name: 'Farmed shrimp' })
  await expect(ocean).toHaveAttribute('aria-current', 'true')
  await expect(page.locator('[data-chapter="o1"]')).toHaveCount(1)
  await pond.click()
  await expect(pond).toHaveAttribute('aria-current', 'true')
  await expect(page).toHaveURL(/#pond$/)
  // one story with both origins: the chosen one runs first
  const order = await page.locator('[data-chapter]').evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.chapter))
  expect(order.indexOf('p1')).toBeGreaterThan(0)
  expect(order.indexOf('p1')).toBeLessThan(order.indexOf('o1'))
})

test('inside the film the toggle lands on the other path\'s first chapter', async ({ page }) => {
  await page.goto('/#ocean')
  await ready(page)
  const o2 = await page.locator('[data-chapter="o2"]').evaluate((el) => (el as HTMLElement).offsetTop + 50)
  await page.evaluate((y) => window.scrollTo(0, y), o2)
  await page.waitForTimeout(500)
  await page.getByRole('group', { name: 'Story path' }).getByRole('link', { name: 'Farmed shrimp' }).click()
  await expect(page).toHaveURL(/#pond$/)
  await page.waitForTimeout(500)
  const top = await page.locator('[data-chapter="p1"]').evaluate((el) => Math.round(el.getBoundingClientRect().top))
  expect(Math.abs(top)).toBeLessThan(4)
})

test('the hero is moving before the first scroll, then scrubbing takes over', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  const video = page.locator('video[src*="/opening_"]')
  const t1 = await video.evaluate((v: HTMLVideoElement) => v.currentTime)
  await page.waitForTimeout(700)
  const t2 = await video.evaluate((v: HTMLVideoElement) => v.currentTime)
  expect(t2).toBeGreaterThan(t1)
  // the logo reveal unlocks scrolling when it finishes
  await page.waitForSelector('#boot', { state: 'detached' })
  await page.mouse.move(700, 450)
  await page.mouse.wheel(0, 300)
  await page.waitForTimeout(600)
  expect(await video.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true)
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
  for (const id of ['products', 'about', 'contact']) {
    await page.locator(`.nav a[href="/#${id}"]`).click()
    await page.waitForTimeout(1800)
    const top = await page.locator(`#${id}`).evaluate((el) => el.getBoundingClientRect().top)
    expect(Math.abs(top)).toBeLessThan(80)
  }
})

test('Enquire on a species lands on #quote with category and species pre-filled', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  await page.evaluate(() => document.getElementById('products')!.scrollIntoView())
  await page.locator('#products').getByRole('button', { name: 'Shrimps', exact: true }).click()
  await page.getByRole('button', { name: 'Enquire about Black Tiger Shrimp' }).click()
  await page.waitForTimeout(1800)
  const top = await page.locator('#quote').evaluate((el) => el.getBoundingClientRect().top)
  expect(Math.abs(top)).toBeLessThan(80)
  const form = page.locator('form.rfq')
  await expect(form.getByLabel('Product category')).toHaveValue('shrimps')
  await expect(form.getByLabel('Black Tiger Shrimp', { exact: true })).toBeChecked()
  await expect(form.getByLabel('Vannamei', { exact: true })).not.toBeChecked()
})
