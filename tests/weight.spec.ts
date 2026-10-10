import { expect, test } from '@playwright/test'
import { statSync, readdirSync } from 'node:fs'
import { PROFILES, scrollThrough, type ProfileName } from './helpers'

// TRD §13 / ASSETS_SPEC budgets. Transferred bytes from CDP, initial (loader done) and after a full scroll.
const BUDGET = { desktop: { initial: 3e6, full: 25e6 }, mobile: { initial: 1.5e6, full: 12e6 } }
const MB = (b: number) => +(b / 1e6).toFixed(2)

/**
 * Per-file caps for everything under public/ (KB). First match wins; an unknown file type fails, so new
 * kinds of assets need a deliberate cap. Clip tiers: 1920 ≤ 2,250, 1280 ≤ 2,300, 960 ≤ 1,400.
 */
const CAPS: [RegExp, number][] = [
  [/_1920\.mp4$/, 2250],
  [/_1280\.mp4$/, 2300],
  [/_960\.mp4$/, 1400],
  [/_720\.mp4$/, 1230],
  [/_720\.webp$/, 40],
  [/\.webp$/, 120],
  [/\.glb$/, 1536],
  [/\.woff2$/, 40],
  [/\.(svg|txt)$/, 20],
  [/\.pdf$/, 2300],
  [/\.(ktx2|jpg|png)$/, 1024],
]

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(`${dir}/${e.name}`) : [`${dir}/${e.name}`]))
}

test('every file under public/ is within its per-file cap', () => {
  const over: string[] = []
  for (const f of walk('public')) {
    if (f.endsWith('.DS_Store')) continue
    const cap = CAPS.find(([re]) => re.test(f))?.[1]
    const kb = statSync(f).size / 1024
    if (cap === undefined) over.push(`${f}: no cap for this file type`)
    else if (kb > cap) over.push(`${f} ${kb.toFixed(0)} KB > ${cap} KB`)
  }
  expect(over).toEqual([])
})

for (const profile of Object.keys(PROFILES) as ProfileName[]) {
  for (const path of ['ocean', 'pond']) {
    test(`weight ${profile} ${path}`, async ({ browser }) => {
      const p = PROFILES[profile]
      const ctx = await browser.newContext({ viewport: p.viewport, isMobile: p.mobile, hasTouch: p.mobile })
      const page = await ctx.newPage()
      const cdp = await ctx.newCDPSession(page)
      await cdp.send('Network.enable')
      await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
      let bytes = 0
      cdp.on('Network.loadingFinished', (e) => (bytes += e.encodedDataLength))
      cdp.on('Network.loadingFailed', () => {})
      await page.goto(`/#${path}`)
      await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 30_000 })
      await page.waitForTimeout(500)
      const initial = bytes
      await scrollThrough(page, p.mobile, 900)
      const full = bytes
      await ctx.close()
      console.log(profile, path, `initial ${MB(initial)} MB · full scroll ${MB(full)} MB`)
      expect(initial).toBeLessThanOrEqual(BUDGET[profile].initial)
      expect(full).toBeLessThanOrEqual(BUDGET[profile].full)
    })
  }
}
