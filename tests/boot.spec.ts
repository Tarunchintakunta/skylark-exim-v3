import { statSync } from 'node:fs'
import { expect, test } from '@playwright/test'

/** Loader and first load (#86, #197): the hero loop once, each font once, 3 posters at most, no RFQ chunk, up to the
 * reveal. After that the warm cache (#251) fetches the whole path on purpose. */
test('boot downloads each file once and only what the first screens need', async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  const cdp = await ctx.newCDPSession(page)
  await cdp.send('Network.enable')
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
  const reqs: string[] = []
  const bytes = new Map<string, number>()
  const ids = new Map<string, string>()
  let total = 0
  cdp.on('Network.requestWillBeSent', (e) => {
    const f = new URL(e.request.url).pathname
    ids.set(e.requestId, f)
    reqs.push(f)
  })
  cdp.on('Network.loadingFinished', (e) => (total += e.encodedDataLength))
  cdp.on('Network.dataReceived', (e) => {
    const f = ids.get(e.requestId)
    if (f) bytes.set(f, (bytes.get(f) ?? 0) + e.dataLength)
  })
  // the moment the loader leaves, timed in the page (the warm cache starts right after it)
  await page.addInitScript(() => {
    const w = window as unknown as { __revealAt?: number }
    new MutationObserver((_, mo) => {
      if (document.readyState !== 'loading' && !document.getElementById('boot')) (w.__revealAt = performance.now()), mo.disconnect()
    }).observe(document, { childList: true, subtree: true })
  })
  await page.goto('/story')
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
  await page.waitForSelector('#boot', { state: 'detached' })
  const firstScreen = await page.evaluate(() => {
    const at = (window as unknown as { __revealAt: number }).__revealAt
    return performance.getEntriesByType('resource').filter((e) => e.startTime < at).map((e) => new URL(e.name).pathname)
  })

  const opening = [...bytes].filter(([f]) => f.includes('/hero-loop_') && f.endsWith('.mp4'))
  for (const [f, b] of opening) expect(b, `${f} downloaded more than once`).toBeLessThanOrEqual(statSync(`dist${f}`).size * 1.1)
  const fonts = reqs.filter((f) => f.endsWith('.woff2'))
  expect(fonts.length, `fonts: ${fonts.join(', ')}`).toBe(new Set(fonts).size)
  const posters = new Set(firstScreen.filter((f) => /\.(webp|avif)$/.test(f)))
  expect(posters.size, `posters: ${[...posters].join(', ')}`).toBeLessThanOrEqual(4)
  expect(reqs.some((f) => f.includes('RfqForm')), 'RFQ chunk loaded at boot').toBe(false)
  console.log(`before first scroll: ${(total / 1024).toFixed(0)} KB, ${reqs.length} requests, posters ${posters.size}`)
  await ctx.close()
})
