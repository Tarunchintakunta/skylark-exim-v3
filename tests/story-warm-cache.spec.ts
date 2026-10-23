import { expect, test, type Page } from '@playwright/test'
import { CLIPS, SEQ } from '../src/film/manifest'
import { scrollThrough } from './helpers'

// #251: after the first screen, the active path's clips are fetched into Blobs. Desktop and phones stream: the cache
// holds the chapter on screen and the next one and follows the scroll down, so the first load is the first chapters
// only, and a reader who stops there downloads nothing more.
// Frame times only mean something with GPU=1.

/**
 * video clips the cache wants with chapter `at` on screen (src/film/warmcache.ts: that chapter and the next); the port
 * film's frame sequences (#hd2) are the stage canvas's, fetched by its worker, not the cache's
 */
const windowAt = (path: 'ocean' | 'pond', at: number) => CLIPS[path].filter((c) => c.chapter >= at && c.chapter <= at + 1 && !(c.id in SEQ)).map((c) => c.id)

const ready = (page: Page) => page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 30_000 })

async function lcp(page: Page) {
  return page.evaluate(
    () =>
      new Promise<number>((done) => {
        new PerformanceObserver((l) => {
          const e = l.getEntries()
          done(Math.round(e[e.length - 1].startTime))
        }).observe({ type: 'largest-contentful-paint', buffered: true })
      }),
  )
}

const DEVICES = {
  desktop: { viewport: { width: 1440, height: 900 }, mobile: false, budgetMB: 25 },
  phone: { viewport: { width: 390, height: 844 }, mobile: true, budgetMB: 12 },
}

for (const [device, d] of Object.entries(DEVICES))
for (const path of ['ocean', 'pond'] as const) {
  const title = 'only the first chapters are cached, and a full scroll streams this path\'s clips, nothing else'
  test(`${device} /story#${path}: after 8 s idle, ${title}`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: d.viewport, isMobile: d.mobile, hasTouch: d.mobile })
    const page = await ctx.newPage()
    const cdp = await ctx.newCDPSession(page)
    await cdp.send('Network.enable')
    const net = new Map<string, string>()
    let phase: 'load' | 'scroll' = 'load'
    const bytes = { load: 0, scroll: 0 }
    const during: string[] = []
    cdp.on('Network.responseReceived', (e) => {
      if (!e.response.fromDiskCache && !e.response.fromServiceWorker && !e.response.fromPrefetchCache) net.set(e.requestId, e.response.url)
    })
    cdp.on('Network.loadingFinished', (e) => {
      bytes[phase] += e.encodedDataLength
      const url = net.get(e.requestId)
      if (phase === 'scroll' && url && /\/media\//.test(url) && e.encodedDataLength > 0) during.push(new URL(url).pathname)
    })
    await page.goto(`/story#${path}`)
    await ready(page)
    const l = await lcp(page)
    await page.waitForTimeout(8000)
    const cached = await page.evaluate(() => document.querySelector('.cache-bar')?.classList.contains('is-done') ?? false)
    const held = (await cache(page)).ids
    // /story#<path> lands on the path's first chapter (#210): the window is around that one
    const landed = await page.evaluate(() => (window as unknown as { __scrub: { chapter: number } }).__scrub.chapter)
    phase = 'scroll'
    await page.evaluate(() => {
      const w = window as unknown as { __f: number[]; __run: boolean }
      w.__f = []
      w.__run = true
      let last = performance.now()
      const f = (t: number) => (w.__f.push(t - last), (last = t), w.__run && requestAnimationFrame(f))
      requestAnimationFrame(f)
    })
    await scrollThrough(page, d.mobile, 1200)
    const p95 = await page.evaluate(() => {
      const w = window as unknown as { __f: number[]; __run: boolean }
      w.__run = false
      const f = w.__f.slice(5).sort((a, b) => a - b)
      return +f[Math.floor(f.length * 0.95)].toFixed(1)
    })
    const shown = await page.evaluate(() => (window as unknown as { __scrubSlots: { id: string }[] }).__scrubSlots.length)
    console.log(device, path, JSON.stringify({ lcpMs: l, cachedBeforeScroll: cached, held: held.length, loadMB: +(bytes.load / 1e6).toFixed(2), scrollKB: Math.round(bytes.scroll / 1024), mediaFromNetworkDuringScroll: during.length, frameP95Ms: p95, decoders: shown }))
    expect(cached).toBe(true)
    console.log(during.join(" "))
    // the first chapter and the next, no further; the scroll then streams clips of this path at the page's tier
    // (a window clip a decoder already holds whole is left to the decoder: the hairline counts it as in hand)
    const win = new Set(windowAt(path, landed))
    expect(held.filter((id) => !win.has(id))).toEqual([])
    // clips of this path, their posters (the scrub loads each segment's and the next two as it enters them), the
    // documentation backdrop, the port film's frames (#hd2: a frame sequence on desktop) and the products below the
    // film, native lazy images that load as the section comes near
    const mine = new Set([...CLIPS[path].map((c) => c.id), 'ph-docs-blur'])
    const id = (u: string) => u.replace(/^\/media\/(.+?)(?:-f_1920_\d+\.(?:avif|webp)|_(?:m|\d+)(?:\.(?:av1|hevc))?\.mp4|_(?:m|\d+)\.(?:avif|webp))$/, '$1')
    expect(during.filter((u) => !mine.has(id(u)) && !u.startsWith('/media/prod-'))).toEqual([])
    if (process.env.GPU) expect(p95).toBeLessThanOrEqual(16.7)
    await ctx.close()
  })
}

type Cache = { path: string; ids: string[]; progress: number }
async function cache(page: Page) {
  return page.evaluate(() => (window as unknown as { __warmCache: Cache }).__warmCache)
}
const OCEAN_ONLY = ['hf-depart', 'hf-catch', 'hf-ice', 'hf-return', 'hf-unload-fish', 'hf-unload-crew', 'hf-fish-intake', 'hf-fish-wash', 'hf-fish-cut', 'hf-fish-freeze']
const POND_ONLY = ['hf-ponds', 'hf-sample', 'hf-harvest', 'hf-unload-shrimp', 'hf-intake', 'hf-wash', 'hf-peel', 'hf-lab', 'hf-iqf', 'hf-pack']

test('desktop follows the scroll: idle mid-film, the cache fills the window around the chapter on screen', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/story#ocean')
  await ready(page)
  await expect.poll(async () => (await cache(page)).progress, { timeout: 20_000 }).toBe(1)
  // wheel into the port chapter (6 clips), then idle
  const port = CLIPS.ocean.find((c) => c.id === 'hf-port-3')!.chapter
  await page.mouse.move(700, 450)
  const chapter = () => page.evaluate(() => (window as unknown as { __scrub: { chapter: number } }).__scrub.chapter)
  for (let k = 0; k < 400 && (await chapter()) < port; k++) await page.mouse.wheel(0, 400)
  await page.waitForTimeout(1500)
  expect(await chapter()).toBe(port)
  await expect.poll(async () => (await cache(page)).progress, { timeout: 60_000 }).toBe(1)
  const ids = (await cache(page)).ids
  // every clip of the window is in hand: a Blob, or a decoder holding it whole
  const whole = await page.$$eval('.stage video[src]', (vs) => (vs as HTMLVideoElement[]).filter((v) => v.buffered.length === 1 && v.buffered.end(0) > v.duration - 0.05).map((v) => v.dataset.clip!))
  expect(windowAt('ocean', port).filter((id) => !ids.includes(id) && !whole.includes(id))).toEqual([])
  // and the port film's frame sets came in whole (sequence.ts prefetch, started by the window)
  await expect.poll(() => page.evaluate(() => ((window as unknown as { __sequences?: { id: string; complete: boolean }[] }).__sequences ?? []).filter((q) => q.id.startsWith('stage-hf-port') && q.complete).length), { timeout: 60_000 }).toBe(5)
  // nothing from the chapters in between that the scroll passed straight through (o3, on ice)
  expect(ids).not.toContain('hf-ice')
})

test('only the active path is fetched; decoders play from blob: URLs or hold their clip whole; a path switch drops the other path’s clips', async ({ page }) => {
  const clips = new Set<string>()
  page.on('request', (r) => {
    const m = new URL(r.url()).pathname.match(/^\/media\/(.+?)_(?:m|\d+)(?:\.(?:av1|hevc))?\.mp4$/)
    if (m) clips.add(m[1])
  })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/story#ocean')
  await ready(page)
  await expect.poll(async () => (await cache(page)).progress, { timeout: 20_000 }).toBe(1)
  expect([...clips].filter((c) => POND_ONLY.includes(c))).toEqual([])
  // every decoder plays from the cache or holds its clip whole: a seek never waits on the network
  const waiting = () =>
    page.$$eval('.stage video[src]', (vs) =>
      (vs as HTMLVideoElement[]).filter((v) => {
        if (v.src.startsWith('blob:')) return false
        const b = v.buffered
        return !(b.length === 1 && b.start(0) < 0.05 && b.end(0) > v.duration - 0.05)
      }).length,
    )
  await page.mouse.move(700, 450)
  for (let i = 0; i < 40; i++) await page.mouse.wheel(0, 120)
  await expect.poll(waiting, { timeout: 10_000 }).toBe(0)
  // (desktop streams by chapter now, #hd2: a decoder may hold its clip whole from the network rather than a blob:)

  await page.locator('.path-toggle a', { hasText: 'Farmed shrimp' }).click()
  await expect.poll(async () => (await cache(page)).path).toBe('pond')
  await expect.poll(async () => (await cache(page)).progress, { timeout: 20_000 }).toBe(1)
  const ids = (await cache(page)).ids
  expect(ids.filter((id) => OCEAN_ONLY.includes(id))).toEqual([])
  // every clip held belongs to the farmed path (shared chapters cached on the wild path stay cached across the switch)
  const pond = new Set(CLIPS.pond.map((c) => c.id))
  expect(ids.filter((id) => !pond.has(id))).toEqual([])
})

test('Save-Data keeps the distance prefetch only: nothing is fetched ahead in idle time', async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  await ctx.addInitScript(() => Object.defineProperty(navigator, 'connection', { value: { saveData: true, effectiveType: '4g' } }))
  const page = await ctx.newPage()
  const clips = new Set<string>()
  page.on('request', (r) => /\/media\/.+\.mp4/.test(r.url()) && clips.add(new URL(r.url()).pathname))
  await page.goto('/story#ocean')
  await ready(page)
  await page.waitForTimeout(6000)
  expect(clips.size).toBeLessThanOrEqual(3)
  await expect(page.locator('.cache-bar')).not.toHaveClass(/is-done/)
  await ctx.close()
})
