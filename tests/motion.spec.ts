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

test('hero: the static headline (LCP) is visible before JS; after the loader the words lift once, from and back to visible, in place', async ({ page }) => {
  // what the HTML paints before any script runs
  await page.route(/\/assets\/.*\.js$/, (r) => r.abort())
  await page.goto('/')
  const staticH1 = page.locator('#hero-static h1')
  expect((await style(staticH1)).opacity).toBe(1)
  const before = (await staticH1.boundingBox())!
  await page.unroute(/\/assets\/.*\.js$/)

  // track every word's opacity and transform from the hand-off on
  await page.addInitScript(() => {
    const w = window as unknown as { __wave: { o: number; t: string }[] }
    w.__wave = []
    const f = () => {
      for (const el of document.querySelectorAll<HTMLElement>('.hero:not(#hero-static) .hero__word')) {
        const cs = getComputedStyle(el)
        if (getComputedStyle(el.closest('.hero')!).visibility === 'visible') w.__wave.push({ o: +cs.opacity, t: cs.transform })
      }
      requestAnimationFrame(f)
    }
    requestAnimationFrame(f)
  })
  await page.goto('/')
  await ready(page)
  await page.waitForTimeout(1600)
  const after = (await page.locator('.hero:not(#hero-static) h1').boundingBox())!
  // React's copy sits exactly where the static copy was (no shift at the hand-off)
  for (const k of ['x', 'y', 'width', 'height'] as const) expect(Math.abs(after[k] - before[k])).toBeLessThan(1.5)
  const wave = await page.evaluate(() => (window as unknown as { __wave: { o: number; t: string }[] }).__wave)
  expect(wave.some((s) => s.t !== 'none' && s.t !== 'matrix(1, 0, 0, 1, 0, 0)')).toBe(true) // it moved
  expect(Math.min(...wave.map((s) => s.o))).toBeGreaterThanOrEqual(0.5) // never from (or near) 0
  for (const w of await page.locator('.hero:not(#hero-static) .hero__word').all()) expect(await style(w)).toEqual(settled)
})

test('hero → content: the loop drifts and dims and the copy fades as the page scrolls', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  const media = page.locator('.home-hero .hero__media')
  const copy = page.locator('.home-hero .hero__copy')
  const still = /^(none|matrix\(1, 0, 0, 1, 0, 0\))$/
  expect((await style(media)).transform).toMatch(still)
  expect((await style(media)).opacity).toBe(1)
  await page.evaluate(() => scrollTo(0, innerHeight * 0.5))
  await expect.poll(async () => (await style(media)).transform).not.toMatch(still)
  expect((await style(media)).opacity).toBeLessThan(1)
  expect((await style(copy)).opacity).toBeLessThan(0.5)
})

test('navbar: shrinks and blurs past 40 px; the underline sits under the current page and slides to a hovered link', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  const bar = page.locator('.topbar')
  await expect(bar).not.toHaveClass(/is-scrolled/)
  await page.evaluate(() => scrollTo(0, 41))
  await expect(bar).toHaveClass(/is-scrolled/)
  await expect.poll(() => bar.evaluate((el) => getComputedStyle(el, '::after').opacity)).toBe('1')
  await page.evaluate(() => scrollTo(0, 0))
  await expect(bar).not.toHaveClass(/is-scrolled/)

  const line = page.locator('.nav__bar')
  const under = async (name: string) => {
    const l = (await page.locator('.nav > ul > li > .nav__link', { hasText: name }).first().boundingBox())!
    const b = (await line.boundingBox())!
    return Math.abs(b.x - l.x) < 2 && Math.abs(b.width - l.width) < 2
  }
  await expect.poll(() => under('Home')).toBe(true)
  await page.locator('.nav > ul > li > .nav__link', { hasText: 'News' }).hover()
  await expect.poll(() => under('News')).toBe(true)
  await page.mouse.move(700, 600)
  await expect.poll(() => under('Home')).toBe(true)
})

test('mobile menu opens with a stagger and closes again', async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  const page = await ctx.newPage()
  await page.goto('/news')
  const nav = page.locator('#site-nav')
  await expect(nav).toBeHidden()
  await page.getByRole('button', { name: 'Menu' }).click()
  const items = nav.locator(':scope > ul > li:not(.nav__bar)')
  const first = items.first()
  const last = items.last()
  // early on, the first item is further in than the last
  await page.waitForTimeout(120)
  expect(await first.evaluate((el) => +getComputedStyle(el).opacity)).toBeGreaterThan(await last.evaluate((el) => +getComputedStyle(el).opacity))
  await expect.poll(() => last.evaluate((el) => +getComputedStyle(el).opacity)).toBe(1)
  await expect(nav.getByRole('link', { name: 'Farmed shrimp' })).toBeVisible()
  await page.getByRole('button', { name: 'Close' }).click()
  await expect(nav).toBeHidden()
  await ctx.close()
})

test('page transitions: cross-document view transitions where supported, an AnimatePresence fade elsewhere', async ({ page }) => {
  await page.goto('/quote')
  expect(await page.evaluate(() => 'PageRevealEvent' in window)).toBe(true) // Chromium: the CSS crossfade
  const rule = await page.evaluate(() =>
    [...document.styleSheets].flatMap((s) => [...s.cssRules]).some((r) => r.cssText.startsWith('@view-transition')),
  )
  expect(rule).toBe(true)

  // without view transitions: the page fades out (0.35 s), then the next page opens at the top
  await page.addInitScript(() => delete (window as unknown as { PageRevealEvent?: unknown }).PageRevealEvent)
  await page.goto('/quote')
  await page.evaluate(() => scrollTo(0, 300))
  // the lowest opacity the page wrapper reaches before it unloads, kept across the navigation
  await page.evaluate(() => {
    const el = document.querySelector<HTMLElement>('#root > div')!
    sessionStorage.setItem('minOp', '1')
    const f = () => {
      sessionStorage.setItem('minOp', String(Math.min(+sessionStorage.getItem('minOp')!, +getComputedStyle(el).opacity)))
      requestAnimationFrame(f)
    }
    f()
  })
  await page.locator('.topbar .brand').click()
  await page.waitForURL(/\/$/)
  expect(+(await page.evaluate(() => sessionStorage.getItem('minOp')))!).toBeLessThan(0.5)
  expect(await page.evaluate(() => scrollY)).toBe(0)
})
