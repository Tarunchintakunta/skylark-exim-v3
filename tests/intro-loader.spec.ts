import { expect, test, type BrowserContext, type Page } from '@playwright/test'

/**
 * Intro (#218, #264): it paints before any JS. On the homepage it opens within 3 s of navigation even on throttled 4G,
 * never locks the scroll, opens at once on the first wheel and is skipped on a return visit in the same session. On
 * /story (#preload) it holds, with a percentage, until the active path is in memory. Static with reduced motion, and it
 * never traps the visitor.
 */

/** records when the loader handed over (data-ready on <html>) and when #boot left the DOM, in ms from navigation start */
const TIMES = () => {
  const t: Record<string, number> = ((window as unknown as { __intro: Record<string, number> }).__intro = {})
  new MutationObserver(() => {
    if (!t.ready && document.documentElement.dataset.ready === '1') t.ready = performance.now()
    if (t.ready && !t.gone && !document.getElementById('boot')) t.gone = performance.now()
  }).observe(document, { subtree: true, childList: true, attributes: true, attributeFilter: ['data-ready'] })
}
const times = (page: Page) => page.evaluate(() => (window as unknown as { __intro: Record<string, number> }).__intro)

/**
 * 'slow': Lighthouse's mobile 4G (1.6 Mbps down, 750 kbps up, 150 ms RTT) with a 4× slower CPU. JS and fonts alone take
 * ~2 s there, so the clips can't buffer in time and the 3 s cap reveals the site.
 * 'fast': DevTools' Fast 4G (9 Mbps down, 1.5 Mbps up, 60 ms RTT): the gate itself completes.
 */
async function throttle4g(ctx: BrowserContext, page: Page, speed: 'slow' | 'fast') {
  const cdp = await ctx.newCDPSession(page)
  await cdp.send('Network.enable')
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
  const [down, up, latency] = speed === 'slow' ? [1.6e6, 750e3, 150] : [9e6, 1.5e6, 60]
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency, downloadThroughput: down / 8, uploadThroughput: up / 8 })
  if (speed === 'slow') await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 })
}

for (const [name, viewport, mobile] of [
  ['390', { width: 390, height: 844 }, true],
  ['1440', { width: 1440, height: 900 }, false],
] as const) {
  test(`loader shows before JS and reveals within 3 s on throttled 4G (${name})`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport, isMobile: mobile, hasTouch: mobile })
    const page = await ctx.newPage()
    await page.addInitScript(TIMES)
    await throttle4g(ctx, page, 'slow')
    await page.goto('/', { waitUntil: 'commit' })
    // static markup: on screen as soon as the document parses, with the intro and an empty progress line
    await page.waitForSelector('#boot .loader__name', { state: 'attached' })
    await expect(page.locator('#boot')).toBeVisible()
    await expect(page.locator('#boot .loader__name')).toHaveText('Skylark Exim')
    // the page is live under the overlay: the scroll is never locked, not even while the intro plays (#264)
    await expect(page.locator('html')).not.toHaveClass(/is-locked/)
    await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 15_000 })
    await page.waitForSelector('#boot', { state: 'detached', timeout: 5_000 })
    const t = await times(page)
    console.log(name, `ready at ${Math.round(t.ready)} ms, loader gone at ${Math.round(t.gone)} ms`)
    // nothing is gated on the intro: the site is live as soon as its script mounts, and the intro opens on its own clock
    expect(t.ready).toBeLessThanOrEqual(3000 + 100)
    expect(t.gone).toBeLessThanOrEqual(t.ready + 2000)
    // hand-off: scroll is unlocked and the static hero copy has given way to React's (same place, no shift)
    await expect(page.locator('html')).not.toHaveClass(/is-locked/)
    await expect(page.locator('#hero-static')).toHaveCount(0)
    await expect(page.locator('.hero h1')).toBeVisible()
    await ctx.close()
  })
}

test('/story: the intro counts up to 100 % and opens once the whole path is in memory; the page holds still meanwhile', async ({ page }) => {
  test.setTimeout(180_000)
  await page.goto('/story')
  await page.waitForSelector('#boot.is-gated', { timeout: 15_000 })
  await expect(page.locator('html')).toHaveClass(/is-locked/)
  const seen = new Set<string>()
  while (await page.locator('#boot').count()) {
    const t = await page.locator('#boot .loader__pct').textContent().catch(() => null)
    if (t) seen.add(t)
    await page.waitForTimeout(100)
  }
  console.log('percentages', [...seen].join(' '))
  expect(await page.evaluate(() => (window as unknown as { __warmCache: { warm: boolean } }).__warmCache.warm)).toBe(true)
  await expect(page.locator('html')).not.toHaveClass(/is-locked/)
})

test('the intro opens at once on the first wheel, and the page scrolls while it plays', async ({ browser }) => {
  const ctx = await browser.newContext()
  const page = await ctx.newPage()
  await page.addInitScript(TIMES)
  await page.goto('/')
  // the page is mounted and the intro is still on screen: a wheel now both scrolls the page and opens the intro
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
  await expect(page.locator('#boot')).toBeVisible()
  await page.mouse.move(700, 450)
  await page.mouse.wheel(0, 600)
  await page.waitForSelector('#boot', { state: 'detached', timeout: 5_000 })
  const t = await times(page)
  console.log(`wheel: intro gone at ${Math.round(t.gone)} ms`)
  await expect.poll(() => page.evaluate(() => scrollY), { timeout: 5_000 }).toBeGreaterThan(0)
  await ctx.close()
})

test('a return visit in the same session skips the homepage loader', async ({ page }) => {
  await page.goto('/')
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
  await page.waitForSelector('#boot', { state: 'detached' })
  await page.addInitScript(TIMES)
  await page.reload()
  await expect(page.locator('html')).toHaveClass(/intro-skip/)
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
  const t = await times(page)
  console.log(`revisit ready at ${Math.round(t.ready)} ms`)
  expect(t.ready).toBeLessThan(1200)
  await expect(page.locator('#boot')).toHaveCount(0)
  await expect(page.locator('html')).not.toHaveClass(/is-locked/)
})

test('a deep link loads its own path behind the intro and lands on it', async ({ page }) => {
  await page.goto('/story#pond')
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
  await page.waitForSelector('#boot', { state: 'detached', timeout: 120_000 })
  expect(await page.evaluate(() => (window as unknown as { __warmCache: { path: string; warm: boolean } }).__warmCache)).toMatchObject({ path: 'pond', warm: true })
  await expect.poll(() => page.evaluate(() => (window as unknown as { __scrub?: { id: string | null } }).__scrub?.id), { timeout: 10_000 }).toBe('hf-ponds')
})

test('the intro is about 1 s: wordmark and hairline, gone by 1.2 s, no layout shift, dark from the first paint (#270)', async ({ page }) => {
  await page.addInitScript(() => {
    ;(window as unknown as { __cls: number }).__cls = 0
    new PerformanceObserver((l) => {
      for (const e of l.getEntries() as unknown as { value: number; hadRecentInput: boolean }[]) if (!e.hadRecentInput) (window as unknown as { __cls: number }).__cls += e.value
    }).observe({ type: 'layout-shift', buffered: true })
  })
  await page.addInitScript(TIMES)
  await page.goto('/', { waitUntil: 'commit' })
  await page.waitForSelector('#boot .loader__name', { state: 'attached' })
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(7, 31, 38)')
  await expect(page.locator('#boot .loader__line')).toHaveCount(1)
  await expect(page.locator('#boot svg, #boot img')).toHaveCount(0) // a text wordmark, no logo
  await page.waitForSelector('#boot', { state: 'detached', timeout: 5_000 })
  const t = await times(page)
  console.log(`intro gone at ${Math.round(t.gone)} ms`)
  expect(t.gone).toBeGreaterThanOrEqual(700)
  expect(t.gone).toBeLessThanOrEqual(1200 + 400) // 1.2 s cap; the 400 ms is the headless CI machine's script arrival
  expect(await page.evaluate(() => (window as unknown as { __cls: number }).__cls)).toBe(0)
})

test('reduced motion: no intro at all', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  await page.goto('/', { waitUntil: 'commit' })
  await page.waitForSelector('#boot .loader__name', { state: 'attached' })
  await expect(page.locator('#boot')).toBeHidden() // display: none from the first paint
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
  await page.waitForSelector('#boot', { state: 'detached' })
  await ctx.close()
})

test('never traps: with no script, the loader fades away on its own at 3 s', async ({ page }) => {
  await page.route(/\/assets\/story-.*\.js$/, (r) => r.abort())
  await page.goto('/story')
  await expect(page.locator('#boot')).toBeVisible()
  await page.waitForTimeout(3600)
  await expect(page.locator('#boot')).toBeHidden()
  // the static hero copy and its links are there to use
  await expect(page.locator('#hero-static h1')).toBeVisible()
  await expect(page.locator('#hero-static .hero__contact')).toBeVisible()
})
