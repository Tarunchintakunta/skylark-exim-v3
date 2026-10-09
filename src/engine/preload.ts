import { clipUrl, posterUrl } from '../film/segments'

/**
 * Critical set for the loader (STORY §0): fonts, the opening poster and the first ~600 KB of the opening clip.
 * Progress is real transferred bytes; estimates are replaced by Content-Length as soon as headers arrive.
 */
const FONTS = ['/fonts/sora-latin-600-normal.woff2', '/fonts/inter-latin-400-normal.woff2', '/fonts/inter-latin-500-normal.woff2', '/fonts/jetbrains-mono-latin-400-normal.woff2']
const CLIP_HEAD = 600 * 1024

export async function preloadCritical(onProgress: (f: number) => void) {
  const items = [
    ...FONTS.map((url) => ({ url, est: 24_000, range: 0 })),
    { url: posterUrl('opening'), est: 6_000, range: 0 },
    { url: clipUrl('opening'), est: CLIP_HEAD, range: CLIP_HEAD },
  ]
  const total = items.map((i) => i.est)
  const loaded = items.map(() => 0)
  const sum = (a: number[]) => a.reduce((x, y) => x + y, 0)
  const report = () => onProgress(Math.min(1, sum(loaded) / sum(total)))

  await Promise.all(
    items.map(async (it, k) => {
      try {
        const res = await fetch(it.url, it.range ? { headers: { Range: `bytes=0-${it.range - 1}` } } : undefined)
        const len = Number(res.headers.get('content-length'))
        if (len) total[k] = len
        const reader = res.body!.getReader()
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          loaded[k] = Math.min(total[k], loaded[k] + value.length)
          report()
        }
      } catch {
        // a failed request must never block the site; count it as done
      }
      loaded[k] = total[k]
      report()
    }),
  )
  await document.fonts.ready
}
