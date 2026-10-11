import { statSync } from 'node:fs'
import { expect, test } from '@playwright/test'
import { open } from './helpers'

/**
 * Clip prefetch (#85): every clip after the first is requested before its chapter starts,
 * one pass down downloads no clip twice, and coming back from the business sections to the port
 * re-uses the two clips still held by the decoders (no re-download).
 */
import { OCEAN } from '../src/config/chapters'

/** the clip each chapter opens with on the Ocean path (later clips in a chapter are prefetched during the one before, so the chapter's start is no bound for them) */
const clipChapter: Record<string, string> = {}
for (const ch of OCEAN) if (ch.media[0]?.kind === 'video') clipChapter[ch.media[0].id] ??= ch.id

test('clips prefetch ahead of their chapter, one download per pass, no re-download on the way back', async ({ browser }) => {
  const { ctx, page } = await open(browser, 'desktop')
  const cdp = await ctx.newCDPSession(page)
  await cdp.send('Network.enable')
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
  const urls = new Map<string, string>()
  const firstAt = new Map<string, number>()
  const bytes = new Map<string, number>()
  cdp.on('Network.requestWillBeSent', (e) => {
    if (!e.request.url.endsWith('.mp4')) return
    const f = new URL(e.request.url).pathname
    urls.set(e.requestId, f)
    if (!firstAt.has(f)) firstAt.set(f, Date.now())
  })
  cdp.on('Network.dataReceived', (e) => {
    const f = urls.get(e.requestId)
    if (f) bytes.set(f, (bytes.get(f) ?? 0) + e.dataLength)
  })

  // chapter id → first clip it plays
  const chapters = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>('[data-chapter]')].map((el) => ({ id: el.dataset.chapter!, top: el.offsetTop })),
  )
  const enteredAt = new Map<string, number>()
  await page.mouse.move(700, 450)
  // real wheel notches at a normal reading pace: 100 px, ~10 notches/s
  const max = await page.evaluate(() => document.getElementById('story')!.offsetTop + document.getElementById('story')!.offsetHeight)
  for (let y = 0; y < max; ) {
    await page.mouse.wheel(0, 100)
    await page.waitForTimeout(100)
    y = await page.evaluate(() => scrollY)
    for (const c of chapters) if (y >= c.top && !enteredAt.has(c.id)) enteredAt.set(c.id, Date.now())
  }
  await page.waitForTimeout(1500)
  const afterPass = new Map(bytes)
  // past the film into Products, then back up to the port chapter
  await page.evaluate(() => document.getElementById('contact')!.scrollIntoView())
  await page.waitForTimeout(1200)
  const port = chapters.find((c) => c.id === 'port')!.top
  await page.evaluate((y) => window.scrollTo(0, y + 200), port)
  await page.waitForTimeout(1500)
  const refetched = ['hf-ship', 'x-ship'].filter((id) => {
    const f = [...bytes.keys()].find((k) => k.includes(`/${id}_`))
    return f && (bytes.get(f) ?? 0) > (afterPass.get(f) ?? 0) * 1.1
  })

  const late: string[] = []
  for (const [f, t] of firstAt) {
    const id = f.replace(/^\/media\/|_\d+\.mp4$/g, '')
    const ch = clipChapter[id]
    if (!ch || id === 'opening') continue
    const entered = enteredAt.get(ch)
    if (entered && t > entered) late.push(`${id} requested ${t - entered} ms after ${ch} began`)
  }
  const twice: string[] = []
  for (const [f, b] of afterPass) {
    const size = statSync(`dist${f}`).size
    if (b > size * 1.25) twice.push(`${f}: ${(b / 1024).toFixed(0)} KB for a ${(size / 1024).toFixed(0)} KB file`)
  }
  console.log('clips:', [...bytes].map(([f, b]) => `${f} ${(b / 1024).toFixed(0)} KB`).join(', '))
  expect(late, 'clips requested only after their chapter began').toEqual([])
  expect(twice, 'clips downloaded more than once in one pass').toEqual([])
  expect(refetched, 'clips re-downloaded on the way back to the port').toEqual([])
  await ctx.close()
})

test('the opening clip plays on the first screen (no neighbour behind it)', async ({ browser }) => {
  const { ctx, page } = await open(browser, 'desktop')
  await page.mouse.move(700, 450)
  for (let n = 0; n < 5; n++) {
    await page.mouse.wheel(0, 100)
    await page.waitForTimeout(100)
  }
  await page.waitForTimeout(800)
  const shown = await page.evaluate(() => [...document.querySelectorAll('video')].filter((v) => v.style.opacity === '1').map((v) => v.currentSrc))
  expect(shown.length).toBe(1)
  expect(shown[0]).toContain('/opening_')
  await ctx.close()
})
