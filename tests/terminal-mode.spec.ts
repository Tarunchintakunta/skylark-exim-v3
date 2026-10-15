import { mkdirSync, writeFileSync } from 'node:fs'
import { expect, test, type Page } from '@playwright/test'

/**
 * Terminal mode (#264): once a page is warm, scrolling it fetches nothing and always has a picture to show.
 *
 * Per viewport, with no throttling and again on Fast 4G with a 4× slower CPU:
 * - the homepage hero's canvas sequence: on a step scroll the frame drawn is within one index of the target, on a fast
 *   fling it keeps painting, and it is never blank or stuck
 * - /story, warm: a step scroll and a fast fling always have a clip on screen (no frozen frame, no blank stage)
 * - no request to /media once the page is warm, on either page
 * - the frame-time p95 table, written to review/terminal-mode.json
 */
const VIEWPORTS = {
  '1920x1080@1': { viewport: { width: 1920, height: 1080 }, dpr: 1, mobile: false },
  '1440x900@2': { viewport: { width: 1440, height: 900 }, dpr: 2, mobile: false },
  '390x844@3': { viewport: { width: 390, height: 844 }, dpr: 3, mobile: true },
} as const
/** DevTools' Fast 4G */
const FAST_4G = { offline: false, latency: 150, downloadThroughput: (9 * 1024 * 1024) / 8, uploadThroughput: (1.5 * 1024 * 1024) / 8 }
/** one 60 Hz vsync, plus the jitter a run with no dropped frame still shows */
const FRAME_P95_MS = 16.7 + 0.3
/** the frame drawn may sit this far from the target index */
const OFF_BY = 1

interface Seq {
  id: string
  frames: number
  progress: number
  complete: boolean
}
const seqs = (page: Page) => page.evaluate(() => (globalThis as unknown as { __sequences?: Seq[] }).__sequences ?? [])

/** A cheap hash of the canvas, to tell a frame that changed from one that is stuck, and either from a blank one. */
const canvasHash = (page: Page) =>
  page.evaluate(() => {
    const c = document.querySelector<HTMLCanvasElement>('.seq__canvas')
    if (!c || !c.width) return { hash: 0, flat: true }
    const d = c.getContext('2d')!.getImageData(0, 0, c.width, c.height).data
    let h = 0
    let min = 255
    let max = 0
    for (let i = 0; i < d.length; i += 4093) {
      h = (h * 31 + d[i]) | 0
      min = Math.min(min, d[i])
      max = Math.max(max, d[i])
    }
    // a blank canvas is one flat colour
    return { hash: h, flat: max - min < 4 }
  })

const p95 = (a: number[]) => +[...a].sort((x, y) => x - y)[Math.max(0, Math.floor(a.length * 0.95) - 1)].toFixed(1)

/** Scrolls with rAF and returns every frame delta, so the table is the browser's own frame times. */
const timedScroll = (page: Page, step: number) =>
  page.evaluate(
    (step) =>
      new Promise<number[]>((done) => {
        const max = document.documentElement.scrollHeight - innerHeight
        const dt: number[] = []
        let last = performance.now()
        const f = (t: number) => {
          dt.push(t - last)
          last = t
          scrollBy(0, step)
          if (scrollY >= max - 2) done(dt.slice(5))
          else requestAnimationFrame(f)
        }
        requestAnimationFrame(f)
      }),
    step,
  )

for (const [name, v] of Object.entries(VIEWPORTS)) {
  for (const throttled of [false, true]) {
    test(`terminal mode ${name}${throttled ? ' fast 4G + 4× CPU' : ''}`, async ({ browser }) => {
      test.setTimeout(900_000)
      const report: Record<string, unknown> = { viewport: name, throttled }
      const ctx = await browser.newContext({ viewport: v.viewport, deviceScaleFactor: v.dpr, isMobile: v.mobile, hasTouch: v.mobile })
      const page = await ctx.newPage()
      const cdp = await ctx.newCDPSession(page)
      await cdp.send('Network.enable')
      await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
      if (throttled) {
        await cdp.send('Network.emulateNetworkConditions', FAST_4G)
        await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 })
      }
      let media: string[] = []
      let counting = false
      page.on('request', (r) => counting && /\/media\//.test(r.url()) && media.push(new URL(r.url()).pathname))

      // ── the homepage hero sequence
      await page.goto('/')
      await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 60_000 })
      await page.mouse.move(v.viewport.width / 2, v.viewport.height / 2)
      await page.mouse.wheel(0, 20)
      await expect.poll(async () => (await seqs(page))[0]?.complete ?? false, { timeout: 300_000 }).toBe(true)
      const seq = (await seqs(page))[0]
      report.heroSet = seq
      await page.evaluate(() => scrollTo(0, 0))
      await page.waitForTimeout(600)

      // step scroll: the frame drawn stays with the target, the picture is never blank and never stuck
      counting = true
      const off: number[] = []
      let prev = await canvasHash(page)
      for (const f of [0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1]) {
        const want = await page.evaluate((f) => {
          const s = document.querySelector<HTMLElement>('.home-hero')!
          scrollTo(0, (s.offsetHeight - innerHeight) * f)
          return f
        }, f)
        await page.waitForTimeout(500)
        const drawn = +(await page.locator('.home-hero').getAttribute('data-frame'))!
        off.push(Math.abs(drawn - Math.round(want * (seq.frames - 1))))
        const now = await canvasHash(page)
        expect.soft(now.flat, `${name} hero at ${f}: blank canvas`).toBe(false)
        expect.soft(now.hash, `${name} hero at ${f}: the frame did not change`).not.toBe(prev.hash)
        prev = now
      }
      report.heroOffBy = off

      // fast fling back to the top and down again: it keeps painting
      await page.evaluate(() => scrollTo(0, 0))
      await page.waitForTimeout(400)
      const flung: boolean[] = []
      for (let i = 0; i < 6; i++) {
        await page.mouse.wheel(0, 1200)
        await page.waitForTimeout(120)
        const h = await canvasHash(page)
        flung.push(!h.flat)
      }
      report.heroFlingPainted = flung
      report.heroFrameP95 = p95(await timedScroll(page, v.mobile ? 18 : 24))
      counting = false
      report.heroMediaDuringScroll = [...new Set(media)]

      // ── /story, warm
      media = []
      await page.goto('/story#ocean')
      await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 60_000 })
      // the whole warm routine, not just the clips: the posters, the page's lazy images and the globe come after them
      await page.waitForFunction(() => (globalThis as unknown as { __warmCache?: { warm: boolean } }).__warmCache?.warm === true, null, { timeout: 600_000 })
      await page.waitForTimeout(1500)
      await page.evaluate(() => scrollTo(0, 0))
      await page.waitForTimeout(800)
      counting = true
      const stuck: string[] = []
      // the film's own stops only: past it the business sections cover the stage and no clip is meant to be on screen
      const onFilm = () =>
        page.evaluate(() => {
          const s = (globalThis as unknown as { __scrub?: { id: string | null; shown: boolean } }).__scrub
          // before the story chunk mounts there is no film: nothing to check
          const film = document.querySelector('.film')?.getBoundingClientRect()
          return { ...s, film: !!film && film.bottom > innerHeight * 0.5 }
        })
      for (const f of [0.05, 0.12, 0.2, 0.3, 0.4, 0.5, 0.6]) {
        await page.evaluate((f) => scrollTo(0, (document.documentElement.scrollHeight - innerHeight) * f), f)
        await page.waitForTimeout(700)
        const s = await onFilm()
        if (s.film && !s.shown) stuck.push(`step ${f}: ${s.id ?? 'no clip'} not on screen`)
      }
      // a fast fling through the film: it still has a clip painted at the end of it
      await page.evaluate(() => scrollTo(0, 0))
      await page.waitForTimeout(500)
      for (let i = 0; i < 8; i++) {
        await page.mouse.wheel(0, 1600)
        await page.waitForTimeout(150)
      }
      await page.waitForTimeout(800)
      const after = await onFilm()
      if (after.film && !after.shown) stuck.push('after the fling: no clip on screen')
      report.storyStuck = stuck
      await page.evaluate(() => scrollTo(0, 0))
      await page.waitForTimeout(600)
      report.storyFrameP95 = p95(await timedScroll(page, v.mobile ? 18 : 24))
      counting = false
      report.storyMediaDuringScroll = [...new Set(media)]
      await ctx.close()

      mkdirSync('review', { recursive: true })
      writeFileSync(`review/terminal-mode-${name}${throttled ? '-4g' : ''}.json`, JSON.stringify(report, null, 2))
      console.log(`\n${name}${throttled ? ' fast 4G + 4× CPU' : ''}`, JSON.stringify(report))

      expect.soft(Math.max(...off), `${name} hero frame off by`).toBeLessThanOrEqual(OFF_BY)
      expect.soft(flung.filter((p) => !p), `${name} hero blank frames during a fling`).toEqual([])
      expect.soft(report.heroMediaDuringScroll, `${name} hero media requests once warm`).toEqual([])
      expect.soft(stuck, `${name} story stuck or blank`).toEqual([])
      expect.soft(report.storyMediaDuringScroll, `${name} story media requests once warm`).toEqual([])
      expect.soft(report.heroFrameP95 as number, `${name} hero frame p95`).toBeLessThanOrEqual(FRAME_P95_MS)
      expect.soft(report.storyFrameP95 as number, `${name} story frame p95`).toBeLessThanOrEqual(FRAME_P95_MS)
    })
  }
}
