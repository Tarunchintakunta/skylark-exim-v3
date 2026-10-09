import { expect, test } from '@playwright/test'
import { statSync, readdirSync } from 'node:fs'
import { PROFILES, scrollThrough, type ProfileName } from './helpers'

// TRD §13 / ASSETS_SPEC budgets. Transferred bytes from CDP, initial (loader done) and after a full scroll.
const BUDGET = { desktop: { initial: 3e6, full: 25e6 }, mobile: { initial: 1.5e6, full: 12e6 } }
const MB = (b: number) => +(b / 1e6).toFixed(2)

test('every committed media/model file is within budget', () => {
  const over: string[] = []
  for (const dir of ['public/media', 'public/models', 'public/textures']) {
    let files: string[] = []
    try {
      files = readdirSync(dir)
    } catch {
      continue
    }
    for (const f of files) {
      const kb = statSync(`${dir}/${f}`).size / 1024
      // clip tiers (redesign §2.6): ≈ 2.5 MB / 8 s at 1920 and 0.9 MB / 8 s at 960, so 12 s clips get 1.5×; posters ≤ 120 KB
      const limit = f.endsWith('.glb') ? 1536
        : f.endsWith('_720.webp') ? 40 : f.endsWith('.webp') ? 120
        : f.endsWith('_1920.mp4') ? 3900 : f.endsWith('_960.mp4') ? 1400 : f.endsWith('_720.mp4') ? 1230 : f.endsWith('.mp4') ? 2300
        : 1024
      if (kb > limit) over.push(`${f} ${kb.toFixed(0)} KB > ${limit} KB`)
    }
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
