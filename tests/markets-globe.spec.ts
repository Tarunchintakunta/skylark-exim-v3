import { expect, test, type Page } from '@playwright/test'

/**
 * How fast the homepage Markets globe shows (#274). `enter`: the globe's box enters the viewport. `poster`: the first
 * frame with the poster loaded while the box is on screen. `live`: the live globe has drawn and taken over
 * (`is-globe-live`: it turns under a drag from then on). The visitor reads the hero for two seconds, then scrolls down
 * to Markets with the wheel at about 1,500 px/s, like a normal wheel or swipe, and stops there.
 */
type R = { poster: number; live: number }

async function measure(page: Page): Promise<R> {
  await page.goto('/')
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 30_000 })
  await page.waitForSelector('#boot', { state: 'detached' })
  await page.waitForTimeout(2000)
  await page.evaluate(() => {
    const w = window as unknown as { __g: { enter: number; poster: number; live: number } }
    w.__g = { enter: -1, poster: -1, live: -1 }
    const box = document.querySelector<HTMLElement>('[data-globe]')!
    let on = false
    new IntersectionObserver(([e]) => {
      on = e.isIntersecting
      if (on && w.__g.enter < 0) w.__g.enter = performance.now()
    }).observe(box)
    const poll = () => {
      const img = box.querySelector('img')
      if (on && w.__g.poster < 0 && img?.complete && img.naturalWidth) w.__g.poster = performance.now()
      if (on && w.__g.live < 0 && box.classList.contains('is-globe-live')) w.__g.live = performance.now()
      if (w.__g.live < 0) requestAnimationFrame(poll)
    }
    requestAnimationFrame(poll)
  })
  // wheel down until the globe's box sits in the middle of the viewport
  await page.mouse.move(700, 450)
  for (let i = 0; i < 200; i++) {
    const top = await page.locator('[data-globe]').evaluate((el) => el.getBoundingClientRect().top)
    if (top < 150) break
    await page.mouse.wheel(0, 75)
    await page.waitForTimeout(50)
  }
  await page.waitForFunction(() => (window as unknown as { __g: { live: number } }).__g.live > 0, null, { timeout: 30_000 })
  return page.evaluate(() => {
    const g = (window as unknown as { __g: { enter: number; poster: number; live: number } }).__g
    return { poster: Math.max(0, Math.round(g.poster - g.enter)), live: Math.round(g.live - g.enter) }
  })
}

test('markets globe: poster at once, live globe within a second', async ({ page }) => {
  const r = await measure(page)
  console.log('markets globe', JSON.stringify(r))
  expect(r.poster, 'poster on screen after the globe enters view (ms)').toBeLessThanOrEqual(300)
  expect(r.live, 'live globe after the globe enters view (ms)').toBeLessThanOrEqual(1000)
})
