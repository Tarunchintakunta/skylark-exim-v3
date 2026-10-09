import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { open, type ProfileName } from './helpers'

/**
 * #131: axe (WCAG 2.2 A/AA) across the film and the business sections, mobile layout checks at the common phone
 * widths, and the reduced-motion fallback.
 */
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']

async function axe(page: Page, where: string, seen: Map<string, string>) {
  // let scroll reveals and caption swaps settle: axe would read their mid-fade colours as contrast failures
  await page
    .waitForFunction(() => [...document.querySelectorAll<HTMLElement>('[data-reveal], .caption [data-fade]')].every((el) => {
      const r = el.getBoundingClientRect()
      if (r.bottom < 0 || r.top > innerHeight) return true
      const o = Number(getComputedStyle(el).opacity)
      return o === 0 || o === 1
    }), null, { timeout: 4000 })
    .catch(() => {})
  // the captions that are not on screen are visibility:hidden, axe skips them; the stage is aria-hidden
  const r = await new AxeBuilder({ page }).withTags(TAGS).analyze()
  for (const v of r.violations) for (const n of v.nodes) seen.set(`${v.id} ${n.target.join(' ')}`, `${where}: ${v.id} (${v.impact}) ${n.target.join(' ')} ${n.failureSummary?.split('\n')[1] ?? ''}`)
}

/** Midpoints of every chapter, then each business section. */
async function stops(page: Page) {
  return page.evaluate(() => [
    ...[...document.querySelectorAll<HTMLElement>('[data-chapter]')].map((el) => ({ at: el.id, y: el.offsetTop + el.offsetHeight / 2 })),
    ...['products', 'trust', 'about', 'quote', 'contact'].map((id) => ({ at: id, y: document.getElementById(id)?.offsetTop ?? 0 })),
  ])
}

for (const profile of ['desktop', 'mobile'] as ProfileName[])
  for (const path of ['', '#pond'])
    test(`axe: no WCAG A/AA violations ${profile} ${path || '#ocean'}`, async ({ browser }) => {
      const { ctx, page } = await open(browser, profile, path)
      await page.waitForSelector('#boot', { state: 'detached' })
      const seen = new Map<string, string>()
      await axe(page, 'top', seen)
      for (const s of await stops(page)) {
        await page.evaluate((y) => window.scrollTo(0, y), s.y)
        await page.waitForTimeout(700)
        await axe(page, s.at, seen)
      }
      // the lazy RFQ form is mounted by now
      await expect(page.locator('form.rfq')).toHaveCount(1)
      await axe(page, 'quote form', seen)
      expect([...seen.values()]).toEqual([])
      await ctx.close()
    })

test('axe: mobile menu open', async ({ browser }) => {
  const { ctx, page } = await open(browser, 'mobile')
  await page.waitForSelector('#boot', { state: 'detached' })
  const btn = page.locator('.menu-btn')
  await btn.click()
  await expect(btn).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByRole('navigation', { name: 'Sections' }).getByRole('link').first()).toBeVisible()
  const seen = new Map<string, string>()
  await axe(page, 'menu open', seen)
  expect([...seen.values()]).toEqual([])
  // Escape closes it and returns focus to the button
  await page.keyboard.press('Escape')
  await expect(btn).toHaveAttribute('aria-expanded', 'false')
  await expect(btn).toBeFocused()
  await ctx.close()
})

test('keyboard: skip link is the first tab stop and moves focus to main', async ({ page }) => {
  await page.goto('/')
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
  await page.waitForSelector('#boot', { state: 'detached' })
  await page.keyboard.press('Tab')
  const skip = page.getByRole('link', { name: 'Skip to content' })
  await expect(skip).toBeFocused()
  await expect.poll(() => skip.evaluate((el) => el.getBoundingClientRect().top)).toBeGreaterThanOrEqual(0)
  await page.keyboard.press('Enter')
  await expect(page.locator('#main')).toBeFocused()
})

/* ---------------- mobile layout ---------------- */

const PHONES = [
  { w: 390, h: 844 },
  { w: 360, h: 800 },
  { w: 412, h: 915 },
  { w: 768, h: 1024 },
]

const tapTargets = () => {
  const small: string[] = []
  const sel = '.path-toggle a, .menu-btn, .nav__link, .quote-cta, .btn, .rfq input:not([tabindex="-1"]), .rfq select, .rfq textarea, .check, .contact-band a, .products button'
  for (const el of document.querySelectorAll<HTMLElement>(sel)) {
    const cs = getComputedStyle(el)
    if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) === 0) continue
    // a checkbox counts with its label
    const r = (el.matches('input[type=checkbox]') ? el.closest('label')! : el).getBoundingClientRect()
    if (!r.width || !r.height) continue
    if (r.width < 44 - 0.5 || r.height < 44 - 0.5) small.push(`${el.className || el.tagName} "${el.textContent?.trim().slice(0, 24)}" ${Math.round(r.width)}×${Math.round(r.height)}`)
  }
  return [...new Set(small)]
}

for (const vp of PHONES)
  test(`mobile ${vp.w}×${vp.h}: no horizontal scroll, tap targets ≥ 44 px, 960 tier`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 })
    const page = await ctx.newPage()
    await page.goto('/')
    await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 30_000 })
    await page.waitForSelector('#boot', { state: 'detached' })
    expect(await page.locator('video[src*="/opening_"]').getAttribute('src')).toMatch(/_960\.mp4$/)
    const wide: string[] = []
    const small = new Set<string>()
    for (const s of await stops(page)) {
      await page.evaluate((y) => window.scrollTo(0, y), s.y)
      await page.waitForTimeout(400)
      const sw = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
      if (sw > 0) wide.push(`${s.at}: ${sw}px`)
      for (const t of await page.evaluate(tapTargets)) small.add(t)
    }
    if (vp.w < 900) await page.locator('.menu-btn').click()
    for (const t of await page.evaluate(tapTargets)) small.add(t)
    expect(wide, 'horizontal overflow').toEqual([])
    expect([...small], 'tap targets under 44×44').toEqual([])
    // the 16 market names are an inline list: WCAG 2.2 AA (2.5.8) 24 px minimum
    const markets = await page.locator('.markets__item').evaluateAll((els) => els.map((e) => e.getBoundingClientRect()).filter((r) => r.width && (r.width < 24 || r.height < 24)).length)
    expect(markets).toBe(0)
    await ctx.close()
  })

/** Same as captions.spec but with native touch scrolling at a phone size: never two headlines on screen. */
const visibleCaptions = () =>
  [...document.querySelectorAll<HTMLElement>('.caption')].filter((el) => {
    const cs = getComputedStyle(el)
    if (cs.visibility === 'hidden' || Number(cs.opacity) < 0.05) return false
    const lines = el.querySelectorAll<HTMLElement>('.line')
    if (!lines.length) return true
    return [...lines].some((l) => {
      const r = l.getBoundingClientRect()
      const m = (l.parentElement ?? l).getBoundingClientRect()
      return r.bottom > m.top + 2 && r.top < m.bottom - 2
    })
  }).length

for (const path of ['', '#pond'])
  test(`mobile: at most one caption on screen across every chapter boundary ${path || '#ocean'}`, async ({ browser }) => {
    const { ctx, page } = await open(browser, 'mobile', path)
    await page.waitForSelector('#boot', { state: 'detached' })
    const tops = await page.evaluate(() => [...document.querySelectorAll<HTMLElement>('[data-chapter]')].map((el) => el.offsetTop))
    let worst = 0
    for (const top of tops.slice(1)) {
      await page.evaluate((y) => window.scrollTo(0, y), top - 300)
      await page.waitForTimeout(400)
      for (let n = 0; n < 6; n++) {
        await page.evaluate(() => window.scrollBy(0, 100))
        await page.waitForTimeout(90)
        worst = Math.max(worst, await page.evaluate(visibleCaptions))
      }
      await page.waitForTimeout(500)
      worst = Math.max(worst, await page.evaluate(visibleCaptions))
    }
    expect(worst).toBeLessThanOrEqual(1)
    await ctx.close()
  })

/* ---------------- reduced motion ---------------- */

test('reduced motion: native scroll, no intro playback, no line animation, loader fades without the reveal', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce', viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  await page.goto('/')
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 30_000 })
  // the loader goes in a 0.2 s fade, not the 1.15 s mark reveal
  await page.waitForSelector('#boot', { state: 'detached', timeout: 600 })
  await expect(page.locator('html')).toHaveClass(/is-reduced/)
  await expect(page.locator('html')).not.toHaveClass(/lenis/)
  // the opening clip is held, not played
  const video = page.locator('video[src*="/opening_"]')
  const t1 = await video.evaluate((v: HTMLVideoElement) => v.currentTime)
  await page.waitForTimeout(800)
  expect(await video.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true)
  expect(await video.evaluate((v: HTMLVideoElement) => v.currentTime)).toBe(t1)
  // headlines are never split into animated lines
  const second = await page.evaluate(() => {
    const el = document.querySelectorAll<HTMLElement>('[data-chapter]')[1]
    return el.offsetTop + el.offsetHeight / 2
  })
  await page.evaluate((y) => window.scrollTo(0, y), second)
  await page.waitForTimeout(300)
  expect(await page.locator('.caption .line').count()).toBe(0)
  expect(await page.locator('.hero h1 .line, .hero h1 [style*="translate"]').count()).toBe(0)
  // no CSS animation is left running
  const running = await page.evaluate(() => document.getAnimations().filter((a) => a.playState === 'running' && (a.effect?.getTiming().iterations ?? 1) === Infinity).length)
  expect(running).toBe(0)
  await ctx.close()
})
