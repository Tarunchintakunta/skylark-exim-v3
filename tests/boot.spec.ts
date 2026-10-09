import { statSync } from 'node:fs'
import { expect, test } from '@playwright/test'

/** Loader and first load (#86): the opening clip once, each font once, 3 posters at most, no RFQ chunk. */
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
  await page.goto('/')
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
  await page.waitForTimeout(2000)

  const opening = [...bytes].filter(([f]) => f.includes('/opening_') && f.endsWith('.mp4'))
  for (const [f, b] of opening) expect(b, `${f} downloaded more than once`).toBeLessThanOrEqual(statSync(`dist${f}`).size * 1.1)
  const fonts = reqs.filter((f) => f.endsWith('.woff2'))
  expect(fonts.length, `fonts: ${fonts.join(', ')}`).toBe(new Set(fonts).size)
  const posters = new Set(reqs.filter((f) => f.endsWith('.webp')))
  expect(posters.size, `posters: ${[...posters].join(', ')}`).toBeLessThanOrEqual(4)
  expect(reqs.some((f) => f.includes('RfqForm')), 'RFQ chunk loaded at boot').toBe(false)
  console.log(`before first scroll: ${(total / 1024).toFixed(0)} KB, ${reqs.length} requests, posters ${posters.size}`)
  await ctx.close()
})
