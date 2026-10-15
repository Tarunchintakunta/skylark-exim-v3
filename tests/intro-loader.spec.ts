import { expect, test, type BrowserContext, type Page } from '@playwright/test'

/**
 * Intro (#218, non-blocking since #264): it paints before any JS, opens within 3 s of navigation even on throttled 4G,
 * never locks the scroll, opens at once on the first wheel, is skipped on a return visit in the same session, is short
 * on a deep link, static with reduced motion, and never traps the visitor.
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
    await page.goto('/story', { waitUntil: 'commit' })
    // static markup: on screen as soon as the document parses, with the intro and an empty progress line
    await page.waitForSelector('#boot .loader__name', { state: 'attached' })
    await expect(page.locator('#boot')).toBeVisible()
    await expect(page.locator('#boot .loader__name')).toHaveText('Skylark Exim · Visakhapatnam')
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

test('on fast 4G the intro opens on its own clock, and the real progress is the story bar hairline', async ({ browser }) => {
  const ctx = await browser.newContext()
  const page = await ctx.newPage()
  await page.addInitScript(TIMES)
  await throttle4g(ctx, page, 'fast')
  await page.goto('/story')
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 15_000 })
  const t = await times(page)
  console.log(`fast 4G ready at ${Math.round(t.ready)} ms`)
  expect(t.ready).toBeLessThan(2500)
  // the intro claims no progress of its own any more (#264)
  await expect(page.locator('#boot')).toHaveCount(0)
  // the hairline under the story bar grows with the warm cache and reaches the end
  const bar = page.locator('.cache-bar')
  const scale = () => bar.evaluate((el) => new DOMMatrixReadOnly(getComputedStyle(el).transform).a)
  await expect.poll(scale, { timeout: 60_000 }).toBeGreaterThan(0.05)
  await expect.poll(scale, { timeout: 180_000 }).toBeGreaterThan(0.99)
  await ctx.close()
})

test('the intro opens at once on the first wheel, and the page scrolls while it plays', async ({ browser }) => {
  const ctx = await browser.newContext()
  const page = await ctx.newPage()
  await page.addInitScript(TIMES)
  await page.goto('/story')
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

test('a return visit in the same session skips the loader', async ({ page }) => {
  await page.goto('/story')
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

test('a deep link gets the short intro and lands on its path', async ({ page }) => {
  await page.addInitScript(TIMES)
  await page.goto('/story#pond')
  await expect(page.locator('html')).toHaveClass(/intro-short/)
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
  await page.waitForSelector('#boot', { state: 'detached', timeout: 5_000 })
  const t = await times(page)
  console.log(`deep link ready at ${Math.round(t.ready)} ms, intro gone at ${Math.round(t.gone)} ms`)
  // the short intro: it opens 800 ms after navigation, or as soon as the script arrives if that is later
  expect(t.gone).toBeGreaterThanOrEqual(800)
  expect(t.gone).toBeLessThanOrEqual(t.ready + 1500)
  await expect.poll(() => page.evaluate(() => (window as unknown as { __scrub?: { id: string | null } }).__scrub?.id), { timeout: 10_000 }).toBe('hf-ponds')
})

test('reduced motion: a static mark and name, then a plain fade', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  await page.goto('/story', { waitUntil: 'commit' })
  await page.waitForSelector('#boot .loader__name', { state: 'attached' })
  const still = await page.evaluate(() => ({
    path: getComputedStyle(document.querySelector('#boot .loader__svg path')!).strokeDashoffset,
    name: getComputedStyle(document.querySelector('#boot .loader__name')!).opacity,
    anim: getComputedStyle(document.querySelector('#boot .loader__svg path')!).animationName,
  }))
  expect(still).toEqual({ path: '0px', name: '1', anim: 'none' })
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
  // the fade leaves the mark at its size (no grow-and-dissolve)
  expect(await page.evaluate(() => document.querySelector<HTMLElement>('#boot .loader__mark')?.style.transform ?? '')).toBe('')
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
