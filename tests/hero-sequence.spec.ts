import { expect, test, type Page } from '@playwright/test'

const ready = async (page: Page) => {
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 30_000 })
  await page.waitForSelector('#boot', { state: 'detached' })
}
const heroScroll = async (page: Page, f: number) => {
  await page.waitForFunction(() => !document.documentElement.classList.contains('lenis-scrolling'))
  await page.evaluate((f) => {
    const s = document.querySelector<HTMLElement>('.home-hero')!
    window.scrollTo(0, (s.offsetHeight - innerHeight) * f)
  }, f)
}
const pixels = (page: Page) =>
  page.evaluate(() => {
    const c = document.querySelector<HTMLCanvasElement>('.seq__canvas')!
    const d = c.getContext('2d')!.getImageData(0, 0, c.width, c.height).data
    let h = 0
    for (let i = 0; i < d.length; i += 4097) h = (h * 31 + d[i]) | 0
    return h
  })
const visible = (page: Page, sel: string) =>
  page.locator(`.home-hero .hero ${sel}`).first().evaluate((el) => getComputedStyle(el).visibility === 'visible' && +getComputedStyle(el).opacity > 0.9)

for (const [label, vp, set, frames] of [
  ['desktop', { width: 1440, height: 900 }, '1920', 60],
  ['phone', { width: 375, height: 812 }, 'm', 48],
] as const) {
  test(`${label}: frames load coarse first and each one only once, from the ${set} set`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: vp })
    const page = await ctx.newPage()
    const order: number[] = []
    page.on('request', (r) => {
      const m = r.url().match(new RegExp(`/media/hero-seq_${set}_(\\d+)\\.(avif|webp)`))
      if (m) order.push(+m[1] - 1)
    })
    await page.goto('/')
    await ready(page)
    // standing still at the top: the coarse passes come first, so after a handful of frames the whole set is already
    // covered at low density (any scroll position has a frame within a few indices) rather than filled from the start
    await expect.poll(() => new Set(order).size, { timeout: 30_000 }).toBeGreaterThanOrEqual(8)
    const coarse = [...new Set(order)].slice(0, 8).sort((a, b) => a - b)
    expect(coarse[0]).toBe(0)
    const gaps = coarse.slice(1).map((v, i) => v - coarse[i])
    expect(Math.max(...gaps, frames - 1 - coarse[coarse.length - 1])).toBeLessThanOrEqual(Math.ceil(frames / 3))
    // and in the end the whole set is in, each frame fetched exactly once (the bitmap cap costs a decode, not a request)
    await expect.poll(() => new Set(order).size, { timeout: 60_000 }).toBe(frames)
    expect(order.length).toBe(new Set(order).size)
    await ctx.close()
  })

  test(`${label}: the canvas scrubs through the frames with scroll, forwards and back, with no layout shift`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: vp })
    const page = await ctx.newPage()
    await page.addInitScript(() => {
      const w = window as unknown as { __cls: number }
      w.__cls = 0
      new PerformanceObserver((l) => l.getEntries().forEach((e) => (w.__cls += (e as unknown as { value: number }).value))).observe({ type: 'layout-shift', buffered: true })
    })
    await page.goto('/')
    await ready(page)
    await page.mouse.wheel(0, 20)
    await expect(page.locator('.seq')).toHaveAttribute('data-painted', 'true')
    const frame = async () => +(await page.locator('.seq').getAttribute('data-frame'))!
    const at0 = await pixels(page)
    expect(await frame()).toBeLessThanOrEqual(1)
    await heroScroll(page, 0.5)
    await expect.poll(frame, { timeout: 10_000 }).toBeGreaterThan(frames * 0.4)
    await expect.poll(frame).toBeLessThan(frames * 0.6)
    expect(await pixels(page)).not.toBe(at0)
    await heroScroll(page, 0)
    await expect.poll(frame, { timeout: 10_000 }).toBeLessThanOrEqual(1)
    const box = (await page.locator('.seq__stage').boundingBox())!
    expect(box.y).toBe(0)
    expect(await page.evaluate(() => (window as unknown as { __cls: number }).__cls)).toBe(0)
    await ctx.close()
  })
}

test('copy over the scroll: headline from the start, supporting line by 50 %, the CTA by 100 %', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  expect(await visible(page, '.hero__title')).toBe(true)
  expect(await visible(page, '.hero__body')).toBe(false)
  expect(await visible(page, '.hero__contact')).toBe(false)
  await heroScroll(page, 0.55)
  await expect.poll(() => visible(page, '.hero__body')).toBe(true)
  expect(await visible(page, '.hero__contact')).toBe(false)
  await heroScroll(page, 1)
  await expect.poll(() => visible(page, '.hero__contact')).toBe(true)
  await expect.poll(() => visible(page, '.hero__fork')).toBe(true)
})

test('the static headline (LCP) paints before any script and React takes over in the same place', async ({ page }) => {
  await page.route(/\/assets\/.*\.js$/, (r) => r.abort())
  await page.goto('/')
  const h1 = page.locator('#hero-static h1')
  expect(await h1.evaluate((el) => +getComputedStyle(el).opacity)).toBe(1)
  expect(await page.locator('#hero-static .hero__body').evaluate((el) => getComputedStyle(el).visibility)).toBe('hidden')
  const before = (await h1.boundingBox())!
  await page.unroute(/\/assets\/.*\.js$/)
  await page.goto('/')
  await ready(page)
  const after = (await page.locator('.home-hero .hero__title').boundingBox())!
  for (const k of ['x', 'y', 'width', 'height'] as const) expect(Math.abs(after[k] - before[k])).toBeLessThan(1.5)
})

test('resize from landscape to portrait swaps to the portrait set', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.goto('/')
  await ready(page)
  await expect(page.locator('.seq')).toHaveAttribute('data-set', '1920')
  await page.setViewportSize({ width: 768, height: 1024 })
  await expect(page.locator('.seq')).toHaveAttribute('data-set', 'm')
  await page.mouse.wheel(0, 20)
  await expect(page.locator('.seq')).toHaveAttribute('data-painted', 'true')
})

test('refresh mid-hero lands on the right frame and copy', async ({ page }) => {
  await page.goto('/')
  await ready(page)
  await heroScroll(page, 0.95)
  await page.waitForTimeout(800)
  await page.reload()
  await ready(page)
  expect(await page.evaluate(() => scrollY)).toBeGreaterThan(500)
  await expect.poll(() => visible(page, '.hero__contact')).toBe(true)
})

test.describe('reduced motion', () => {
  test.use({ reducedMotion: 'reduce' })
  test('a static hero image, no pin, no scrub, all copy visible', async ({ page }) => {
    await page.goto('/')
    await ready(page)
    await expect(page.locator('.seq__canvas')).toHaveCount(0)
    await expect(page.locator('.seq__poster')).toBeVisible()
    const h = await page.locator('.home-hero').evaluate((el) => el.getBoundingClientRect().height)
    expect(Math.abs(h - (await page.evaluate(() => innerHeight)))).toBeLessThan(2)
    for (const sel of ['.hero__title', '.hero__body', '.hero__contact', '.hero__fork']) expect(await visible(page, sel)).toBe(true)
    await expect(page.locator('#hero-static')).toHaveCount(0)
  })
})
