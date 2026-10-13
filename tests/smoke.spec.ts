import { expect, test } from '@playwright/test'

const ready = (page: import('@playwright/test').Page) => page.waitForFunction(() => document.documentElement.dataset.ready === '1')

test('loads, loader completes, one h1', async ({ page }) => {
  await page.goto('/story')
  await ready(page)
  await expect(page.locator('h1')).toHaveCount(1)
  await expect(page.locator('.loader')).toHaveCount(0)
  await expect(page.locator('html')).not.toHaveClass(/is-locked/)
})

test('header toggle swaps the story and keeps the hash; Ocean is the default', async ({ page }) => {
  await page.goto('/story')
  await ready(page)
  const ocean = page.getByRole('group', { name: 'Story path' }).getByRole('link', { name: 'Wild catch' })
  const pond = page.getByRole('group', { name: 'Story path' }).getByRole('link', { name: 'Farmed shrimp' })
  await expect(ocean).toHaveAttribute('aria-current', 'true')
  await expect(page.locator('[data-chapter="o1"]')).toHaveCount(1)
  await pond.click()
  await expect(pond).toHaveAttribute('aria-current', 'true')
  await expect(page).toHaveURL(/#pond$/)
  // two separate stories (#219): the pond path has no ocean chapter
  await expect(page.locator('[data-chapter="p1"]')).toHaveCount(1)
  await expect(page.locator('[data-chapter="o1"]')).toHaveCount(0)
})

test('inside the film the toggle lands on the other path\'s first chapter', async ({ page }) => {
  await page.goto('/story#ocean')
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

test('the hero loop plays, loops, and hands over to the scrubbed story on scroll (#197)', async ({ page }) => {
  await page.goto('/story')
  await ready(page)
  const loop = page.locator('video.hero__video')
  await expect(loop).toHaveAttribute('loop', '')
  const t1 = await loop.evaluate((v: HTMLVideoElement) => v.currentTime)
  await page.waitForTimeout(700)
  const t2 = await loop.evaluate((v: HTMLVideoElement) => v.currentTime)
  expect(t2).toBeGreaterThan(t1)
  // the logo reveal unlocks scrolling when it finishes
  await page.waitForSelector('#boot', { state: 'detached' })
  await page.mouse.move(700, 450)
  const start = await page.locator('[data-chapter="start"]').evaluate((el) => (el as HTMLElement).offsetHeight)
  for (let y = 0; y < start * 0.45; y += 100) {
    await page.mouse.wheel(0, 100)
    await page.waitForTimeout(60)
  }
  await page.waitForTimeout(800)
  // past the hand-off: the loop has faded out and paused, the opening shot scrubs underneath
  expect(await page.locator('.hero__media').evaluate((el) => (el as HTMLElement).style.opacity)).toBe('0')
  expect(await loop.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true)
  const shown = await page.evaluate(() => [...document.querySelectorAll<HTMLVideoElement>('video.stage__video')].filter((v) => v.style.opacity === '1').map((v) => v.currentSrc))
  expect(shown.join()).toContain('/opening_')
})

test('RFQ shows validation errors, then falls back to a pre-filled mailto', async ({ page }) => {
  await page.route('**/api/rfq', (r) => r.fulfill({ json: { ok: false, fallback: 'mailto' } }))
  await page.goto('/quote')
  await ready(page)
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

test('every homepage nav link lands on its section', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  await page.waitForSelector('#boot', { state: 'detached' })
  for (const id of ['products', 'markets', 'about', 'contact']) {
    await page.locator(`.nav a[href="/#${id}"]`).click()
    await page.waitForTimeout(1800)
    const top = await page.locator(`#${id}`).evaluate((el) => el.getBoundingClientRect().top)
    expect(Math.abs(top)).toBeLessThan(80)
  }
})

test('Enquire on a species opens /quote with category and species pre-filled', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  await page.evaluate(() => document.getElementById('products')!.scrollIntoView())
  await page.locator('#products').getByRole('button', { name: 'Shrimps', exact: true }).click()
  await page.getByRole('button', { name: 'Enquire about Black Tiger Shrimp' }).click()
  await page.waitForURL(/\/quote#/)
  await ready(page)
  const form = page.locator('form.rfq')
  await expect(form.getByLabel('Product category')).toHaveValue('shrimps')
  await expect(form.getByLabel('Black Tiger Shrimp', { exact: true })).toBeChecked()
  await expect(form.getByLabel('Vannamei', { exact: true })).not.toBeChecked()
})
