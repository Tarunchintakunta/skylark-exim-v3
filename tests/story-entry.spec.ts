import { expect, test, type Page } from '@playwright/test'

const ready = async (page: Page) => {
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 30_000 })
  await page.waitForSelector('#boot', { state: 'detached' })
}

/** Story Entry (#268): the three bento cards after the hero's intro. */

test('a card opens to the sheet and Esc brings back the page where it was', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  const card = page.locator('#story-entry [data-card="wild"]')
  await card.scrollIntoViewIfNeeded()
  const y = await page.evaluate(() => scrollY)
  await card.locator('.se-hit').click()
  await expect(card.locator('.se-panel')).toBeVisible()
  await expect(card.locator('.se-widget')).toHaveCount(6)
  await expect(card.locator('.se-close')).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(card.locator('.se-panel')).toBeHidden()
  await expect(card.locator('.se-hit')).toBeFocused()
  expect(Math.abs((await page.evaluate(() => scrollY)) - y)).toBeLessThan(4)
})

test('the start links open each story on its own path', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  await page.locator('#story-entry [data-card="farmed"] .se-hit').click()
  await page.locator('#story-entry [data-card="farmed"] .se-btn--primary').click()
  await page.waitForURL(/\/story#pond$/)
})

test('Europe is labelled as a region, not listed as a country', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  const world = page.locator('#story-entry [data-card="world"]')
  const text = await world.locator('.se-widgets').innerText()
  expect(text).toContain('Europe (region)')
  expect(text.split('·').map((s) => s.trim())).not.toContain('Europe')
  await expect(world.locator('.se-heading')).toHaveText(/Trusted in 15 markets/)
})

test.describe('phone', () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })

  test('the open sheet scrolls all six widgets fully into view above the safe area', async ({ page }) => {
    await page.goto('/')
    await ready(page)
    for (const id of ['wild', 'farmed', 'world']) {
      const card = page.locator(`#story-entry [data-card="${id}"]`)
      await card.scrollIntoViewIfNeeded()
      await card.locator('.se-hit').tap()
      const panel = card.locator('.se-panel')
      await expect(panel).toBeVisible()
      await expect(card.locator('.se-widget')).toHaveCount(6)
      const last = card.locator('.se-widget').last()
      await last.evaluate((el) => el.scrollIntoView({ block: 'end' }))
      await page.waitForTimeout(900) // the grow is 650 ms
      await expect(last).toBeInViewport({ ratio: 1 })
      const [w, p] = await Promise.all([last.boundingBox(), panel.boundingBox()])
      expect(p!.y + p!.height - (w!.y + w!.height)).toBeGreaterThanOrEqual(24)
      await card.locator('.se-close').tap()
      await expect(panel).toBeHidden()
    }
  })

  test('the cards have 24 px side margins', async ({ page }) => {
    await page.goto('/')
    await ready(page)
    const b = await page.locator('#story-entry .se-cell').first().boundingBox()
    expect(b!.x).toBe(24)
    expect(b!.width).toBe(390 - 48)
  })
})
