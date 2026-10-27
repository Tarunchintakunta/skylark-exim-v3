import { firstClip } from '../config/chapters'
import { env } from '../engine/env'
import { store, type Path } from '../engine/store'
import { CLIPS } from '../film/manifest'
import { avifReady, clipUrl, codecReady, isSeq, posterUrl, seqFrames, seqUrl } from '../film/segments'

const hinted = new Set<string>()
function hint(rel: 'modulepreload' | 'prefetch', href: string, as?: string) {
  if (hinted.has(href)) return
  hinted.add(href)
  const link = document.createElement('link')
  link.rel = rel
  link.href = href
  if (as) link.as = as
  document.head.append(link)
}

let scripts: Promise<void> | null = null
/** /story's scripts: its entry and preloads (named in its HTML), then the lazy story chunk and its CSS (named in the entry). */
const storyScripts = () =>
  (scripts ??= fetch('/story')
    .then((r) => r.text())
    .then(async (html) => {
      const entry = html.match(/<script type="module"[^>]*src="([^"]+)"/)?.[1]
      if (!entry) return
      for (const [, href] of html.matchAll(/<link rel="modulepreload"[^>]*href="([^"]+)"/g)) hint('modulepreload', href)
      const js = await fetch(entry).then((r) => r.text())
      hint('modulepreload', entry)
      for (const [file] of js.matchAll(/assets\/Story-[\w-]+\.(?:js|css)/g)) {
        if (file.endsWith('.css')) hint('prefetch', `/${file}`, 'style')
        else hint('modulepreload', `/${file}`)
      }
    })
    .catch(() => void (scripts = null)))

/** The /story chunk and that path's first chapter (o1 / p1): its poster and clip, at the tier /story will ask for. */
export function prefetchStory(path: Path) {
  void storyScripts()
  const clip = firstClip(path)
  if (!clip) return
  hint('prefetch', posterUrl(clip.id), 'image')
  hint('prefetch', clipUrl(clip.id), 'video')
}

/** Hover or keyboard focus on any story link (nav, hero fork, story cards) warms /story; nothing loads before that. */
export function bindStoryPrefetch() {
  const on = (e: Event) => {
    const a = (e.target as Element | null)?.closest?.<HTMLAnchorElement>('a[href^="/story"]')
    if (a) prefetchStory(a.hash === '#pond' ? 'pond' : 'ocean')
  }
  document.addEventListener('pointerover', on, { passive: true })
  document.addEventListener('focusin', on)
  return () => {
    document.removeEventListener('pointerover', on)
    document.removeEventListener('focusin', on)
  }
}

/**
 * The homepage's own images, warmed once the intro has opened and the browser is idle (#264): every lazy image below the
 * fold is switched to eager, so a scroll through the page fetches nothing. The hero's frame set loads on the same
 * signal (home/HomeHero.tsx); this is everything under it: the story cards, the products, the plant and the globe still.
 */
export function warmHomeImages() {
  const go = () => {
    const warm = () => document.querySelectorAll<HTMLImageElement>('main img[loading="lazy"]').forEach((img) => (img.loading = 'eager'))
    if ('requestIdleCallback' in window) requestIdleCallback(() => warm(), { timeout: 3000 })
    else setTimeout(warm, 500)
  }
  if (store.getState().revealed) {
    go()
    return () => {}
  }
  const off = store.subscribe((s) => {
    if (!s.revealed) return
    off()
    go()
  })
  return off
}

/**
 * The story, warmed from the homepage (#preload): once the intro has opened and the browser is idle, every clip and
 * frame of the wild-catch path and then the farmed path is fetched at low priority, at the tier and codec /story will
 * ask for. /media is immutable, so /story's warm cache then reads them from the HTTP cache and its intro opens almost
 * at once. Save-Data and 2g/3g skip it.
 */
export function warmStory() {
  if (env.saveData || env.slow) return () => {}
  const ctl = new AbortController()
  const go = async () => {
    await Promise.all([codecReady, avifReady])
    const seen = new Set<string>()
    const urls = (['ocean', 'pond'] as const).flatMap((p) =>
      CLIPS[p].flatMap((c) => (isSeq(c.id) ? Array.from({ length: seqFrames(c.id) }, (_, i) => seqUrl(c.id, i)) : [clipUrl(c.id)])),
    ).filter((u) => !seen.has(u) && seen.add(u))
    const one = (u: string) => fetch(u, { signal: ctl.signal, priority: 'low' } as RequestInit).then((r) => r.blob()).catch(() => null)
    await Promise.all(Array.from({ length: 3 }, async () => {
      while (urls.length && !ctl.signal.aborted) await one(urls.shift()!)
    }))
  }
  const start = () => ('requestIdleCallback' in window ? requestIdleCallback(() => void go(), { timeout: 3000 }) : setTimeout(go, 500))
  if (store.getState().revealed) start()
  const off = store.subscribe((s, was) => s.revealed && !was.revealed && start())
  return () => (off(), ctl.abort())
}
