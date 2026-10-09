import { expect, test } from '@playwright/test'
import { open } from './helpers'

/** Count captions a person could see: visible, not transparent, and with at least one line inside its mask. */
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

for (const path of ['', '#pond']) {
  test(`at most one caption on screen across every chapter boundary ${path || '#ocean'}`, async ({ browser }) => {
    const { ctx, page } = await open(browser, 'desktop', path)
    const tops = await page.evaluate(() => [...document.querySelectorAll<HTMLElement>('[data-chapter]')].map((el) => el.offsetTop))
    await page.mouse.move(700, 450)
    let worst = 0
    for (const top of tops.slice(1)) {
      // approach the boundary, then cross it with real wheel notches
      await page.evaluate((y) => window.scrollTo(0, y), top - 300)
      await page.waitForTimeout(400)
      for (let n = 0; n < 6; n++) {
        await page.mouse.wheel(0, 100)
        await page.waitForTimeout(90)
      }
      for (const ms of [0, 250, 500, 1000]) {
        if (ms) await page.waitForTimeout(ms === 250 ? 250 : 250 * (ms / 500))
        worst = Math.max(worst, await page.evaluate(visibleCaptions))
      }
    }
    expect(worst).toBeLessThanOrEqual(1)
    await ctx.close()
  })
}
