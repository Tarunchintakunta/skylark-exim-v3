import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { expect, test } from '@playwright/test'

// Node-only: every media URL the chapter config can request, on every tier, must exist in public/ (#144).
// Tiers (segments.ts): phones / Save-Data 960 (stills 720), desktop 1280 and 1920 (stills 1280).
test('every chapter media URL exists in public/ for every tier', async () => {
  // segments.ts reads the window size at import; stub it for Node
  Object.assign(globalThis, { devicePixelRatio: 1, innerWidth: 1440 })
  const { OCEAN, POND } = await import('../src/config/chapters')
  const { clipUrl, endPosterUrl, posterFor } = await import('../src/film/segments')

  const urls = new Set<string>()
  for (const w of [960, 1280, 1920])
    for (const ch of [...OCEAN, ...POND])
      for (const m of ch.media) {
        const poster = posterFor(m, w)
        if (poster) urls.add(poster)
        if (m.kind === 'video') urls.add(clipUrl(m.id, w)).add(endPosterUrl(m.id))
      }

  const missing = [...urls].filter((u) => !existsSync(join('public', u)))
  expect(urls.size).toBeGreaterThan(30)
  expect(missing).toEqual([])
})
