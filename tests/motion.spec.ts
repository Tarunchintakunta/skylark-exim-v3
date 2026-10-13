import { expect, test, type Locator, type Page } from '@playwright/test'

// #236-#238: Motion on the homepage, /quote and /news (transform and opacity only, reduced motion respected).

const ready = async (page: Page) => {
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 30_000 })
  await page.waitForSelector('#boot', { state: 'detached' })
}
const style = (l: Locator) => l.evaluate((el) => ({ opacity: +getComputedStyle(el).opacity, transform: getComputedStyle(el).transform }))
const settled = { opacity: 1, transform: 'none' }

test('homepage sections rise in once, as they are scrolled to', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  const title = page.locator('#plant .section__title')
  expect((await style(title)).opacity).toBe(0) // below the fold: not revealed yet
  await title.scrollIntoViewIfNeeded()
  await expect.poll(() => style(title)).toEqual(settled)
  // the stills stagger after the heading and settle too
  const last = page.locator('#plant .plant-still').last()
  await last.scrollIntoViewIfNeeded()
  await expect.poll(() => style(last)).toEqual(settled)
  // once: scrolling away and back does not hide it again
  await page.evaluate(() => scrollTo(0, 0))
  await page.waitForTimeout(300)
  expect((await style(title)).opacity).toBe(1)
})

test('a product card lifts 4 px on hover and its still zooms 1.03', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  const card = page.locator('#products .pcard').first()
  await card.scrollIntoViewIfNeeded()
  await expect.poll(() => style(card)).toEqual(settled)
  await card.hover()
  await expect.poll(async () => (await style(card)).transform).toBe('matrix(1, 0, 0, 1, 0, -4)')
  await expect.poll(async () => (await style(card.locator('.pcard__img'))).transform).toBe('matrix(1.03, 0, 0, 1.03, 0, 0)')
  await expect.poll(async () => (await style(card.locator('.pcard__shadow'))).opacity).toBe(1)
})

test('a story card poster drifts with the mouse and settles back', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  const link = page.locator('#intro .story-card__link').first()
  await link.scrollIntoViewIfNeeded()
  const img = link.locator('.story-card__img')
  const box = (await link.boundingBox())!
  await page.mouse.move(box.x + box.width * 0.9, box.y + box.height * 0.2)
  await page.mouse.move(box.x + box.width * 0.95, box.y + box.height * 0.1, { steps: 4 })
  await expect.poll(async () => (await style(img)).transform).not.toBe('none')
  await page.mouse.move(0, 0)
  await expect.poll(async () => (await style(img)).transform, { timeout: 5000 }).toMatch(/^(none|matrix\(1, 0, 0, 1, 0, 0\))$/)
})

test('/quote and /news: the h1 (LCP) is visible from the first frame; the content below rises in', async ({ page }) => {
  for (const [url, below] of [['/quote', '.quote-aside'], ['/news', '.news-grid li, .news-empty']] as const) {
    await page.goto(url)
    expect((await style(page.locator('h1'))).opacity).toBe(1)
    await expect.poll(() => style(page.locator(below).first())).toEqual(settled)
  }
})

test.describe('reduced motion', () => {
  test.use({ reducedMotion: 'reduce' })
  test('no rise and no hover lift; content still ends fully visible', async ({ page }) => {
    await page.goto('/')
    await ready(page)
    const title = page.locator('#plant .section__title')
    await title.scrollIntoViewIfNeeded()
    // Motion's reducedMotion="user" drops transform animation: y is never off 0, opacity alone fades
    const seen = await title.evaluate(
      (el) =>
        new Promise<string[]>((done) => {
          const out: string[] = []
          const t0 = performance.now()
          const f = () => (out.push(getComputedStyle(el).transform), performance.now() - t0 < 900 ? requestAnimationFrame(f) : done(out))
          f()
        }),
    )
    expect(seen.filter((t) => t !== 'none' && t !== 'matrix(1, 0, 0, 1, 0, 0)')).toEqual([])
    await expect.poll(async () => (await style(title)).opacity).toBe(1)
    const card = page.locator('#products .pcard').first()
    await card.scrollIntoViewIfNeeded()
    await card.hover()
    await page.waitForTimeout(500)
    expect((await style(card)).transform).toMatch(/^(none|matrix\(1, 0, 0, 1, 0, 0\))$/)
  })
})
