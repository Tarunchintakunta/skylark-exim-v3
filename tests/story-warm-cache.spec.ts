import { expect, test, type Page } from '@playwright/test'
import { scrollThrough } from './helpers'

// #251: after the first screen, the active path's clips are fetched into Blobs (and its posters into the HTTP cache), so
// a scroll through the film fetches no media from the network. Frame times only mean something with GPU=1.

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
  test(`${device} /story#${path}: after 8 s idle, a full scroll fetches no media from the network`, async ({ browser }) => {
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
    console.log(device, path, JSON.stringify({ lcpMs: l, cachedBeforeScroll: cached, loadMB: +(bytes.load / 1e6).toFixed(2), scrollKB: Math.round(bytes.scroll / 1024), mediaFromNetworkDuringScroll: during.length, frameP95Ms: p95, decoders: shown }))
    expect(cached).toBe(true)
    console.log(during.join(" "))
    expect(during).toEqual([])
    if (process.env.GPU) expect(p95).toBeLessThanOrEqual(16.7)
    await ctx.close()
  })
}

type Cache = { path: string; ids: string[]; progress: number }
const cache = (page: Page) => page.evaluate(() => (window as unknown as { __warmCache: Cache }).__warmCache)
const OCEAN_ONLY = ['hf-depart', 'hf-catch', 'hf-ice', 'hf-return', 'hf-unload-fish', 'hf-fish-intake', 'hf-fish-wash', 'hf-fish-cut', 'hf-fish-freeze']
const POND_ONLY = ['hf-ponds', 'hf-sample', 'hf-harvest', 'hf-unload-shrimp', 'hf-intake', 'hf-wash', 'hf-peel', 'hf-lab', 'hf-iqf', 'hf-pack']

test('only the active path is fetched; decoders play from blob: URLs or hold their clip whole; a path switch drops the other path’s clips', async ({ page }) => {
  const clips = new Set<string>()
  page.on('request', (r) => {
    const m = new URL(r.url()).pathname.match(/^\/media\/(.+)_\d+\.mp4$/)
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
  expect(await page.$$eval('.stage video[src^="blob:"]', (vs) => vs.length)).toBeGreaterThan(0)

  await page.locator('.path-toggle a', { hasText: 'Farmed shrimp' }).click()
  await expect.poll(async () => (await cache(page)).path).toBe('pond')
  await expect.poll(async () => (await cache(page)).progress, { timeout: 20_000 }).toBe(1)
  const ids = (await cache(page)).ids
  expect(ids.filter((id) => OCEAN_ONLY.includes(id))).toEqual([])
  // shared chapters stay cached across the switch; a clip a decoder already holds whole isn't downloaded again
  expect(ids).toEqual(expect.arrayContaining(['hf-intake', 'hf-ship']))
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
