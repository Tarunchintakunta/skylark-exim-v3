import { expect, test } from '@playwright/test'

// #147: globe market labels never overlap each other and stay inside the viewport, below the fixed header
const VIEWS = [
  { name: 'mobile', viewport: { width: 390, height: 844 }, isMobile: true },
  { name: 'desktop', viewport: { width: 1440, height: 900 }, isMobile: false },
]

for (const v of VIEWS) {
  test(`globe labels: no overlap, inside the viewport (${v.viewport.width}×${v.viewport.height})`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: v.viewport, isMobile: v.isMobile, hasTouch: v.isMobile })
    const page = await ctx.newPage()
    await page.goto('/')
    await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 30_000 })
    // walk into the world chapter, then hold at 90 % and 99 % of its progress (routes have landed)
    for (const p of [0.5, 0.9, 0.99]) {
      await page.evaluate((p) => {
        const el = document.querySelector<HTMLElement>('[data-chapter="world"]')!
        const top = el.getBoundingClientRect().top + scrollY
        window.scrollTo(0, top + p * (el.offsetHeight - innerHeight))
      }, p)
      await page.waitForTimeout(p === 0.5 ? 1500 : 1000)
      if (p === 0.5) continue
      const boxes = await page.evaluate(() =>
        [...document.querySelectorAll<HTMLElement>('.globe-label')]
          .filter((l) => Number(l.style.opacity) > 0)
          .map((l) => {
            const r = l.getBoundingClientRect()
            return { name: l.textContent, l: r.left, t: r.top, r: r.right, b: r.bottom }
          }),
      )
      expect(boxes.length).toBeGreaterThan(5)
      for (const a of boxes) {
        expect(a.l, `${a.name} left`).toBeGreaterThanOrEqual(0)
        expect(a.r, `${a.name} right`).toBeLessThanOrEqual(v.viewport.width)
        expect(a.t, `${a.name} top`).toBeGreaterThanOrEqual(68)
        expect(a.b, `${a.name} bottom`).toBeLessThanOrEqual(v.viewport.height)
        for (const b of boxes)
          if (a !== b) expect(a.l < b.r && a.r > b.l && a.t < b.b && a.b > b.t, `${a.name} overlaps ${b.name}`).toBe(false)
      }
    }
    await ctx.close()
  })
}
