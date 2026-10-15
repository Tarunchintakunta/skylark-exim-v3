import { chaptersFor } from '../config/chapters'
import { env } from '../engine/env'
import { frame, store, type Path } from '../engine/store'
import { GLOBE_TEXTURE, warmGlobePlaceholder } from '../three/globeState'
import { CLIPS, type Clip } from './manifest'
import { downloading, fullyLoaded } from './scrub'
import { W, avifReady, clipUrl, codec, codecReady, endPosterUrl, posterFor, served } from './segments'

/**
 * Warm cache (#251): once the first screen is up, one loader fetches every clip of the active path into Blobs, so the
 * stage's <video>s play from blob: URLs and a seek never touches the network. Only the active path, at the page's own
 * tier and in one codec (#hd: it waits for segments.ts to settle the codec). Coarse first: the first and the middle clip
 * of each chapter in story order, then the rest, so a fast scroll meets something cached everywhere early. Save-Data
 * and 2g/3g keep the distance prefetch only (scrub.ts), which stays the fallback for clips not cached yet.
 */
/** clips fetched at once (#264, Terminal's concurrency): 6 desktop, 3 phone */
const PARALLEL = env.mobile ? 3 : 6
/** ms since the last scroll that still counts as scrolling */
const QUIET = 400
/** chapters ahead of the one on screen that the scrub loads itself while the visitor scrolls */
const NEAR = 2
let lastMove = 0
addEventListener(
  'scroll',
  () => {
    const starts = performance.now() - lastMove >= QUIET
    lastMove = performance.now()
    // a scroll starts: cancel every fetch in flight so the scrub's progressive loads get the whole link. Those clips are
    // left to the scrub (fetching them again would download them twice); the cache goes on with the rest in the next pause
    if (starts) for (const stop of loading.values()) stop.abort()
  },
  { passive: true },
)

const urls = new Map<string, string>()
let path: Path | null = null
let abort: AbortController | null = null
let total = 0
let done = 0
const listeners = new Set<() => void>()
/** decoded posters, held so the document's list of available images serves them to the stage without a request */
const images: HTMLImageElement[] = []
const emit = () => listeners.forEach((f) => f())

// what the cache holds, for tests (navigator.webdriver) and ?debug only
if (navigator.webdriver || new URLSearchParams(location.search).has('debug'))
  Object.defineProperty(globalThis, '__warmCache', { get: () => ({ path, ids: [...urls.keys()], progress: progress() }) })

/** fetches in flight, by clip: a scroll cancels them (see below) */
const loading = new Map<string, AbortController>()

/** blob: URL for a cached clip of the active path, else null */
export const cachedUrl = (id: string) => urls.get(id) ?? null
/** 0..1 of the active path's clip bytes in the cache */
export const progress = () => (total ? done / total : 0)
export function onCache(f: () => void) {
  listeners.add(f)
  return () => void listeners.delete(f)
}

/** story order, coarse first: each chapter's first and middle clip, then everything else */
export function order(clips: Clip[]) {
  const coarse = clips.filter((c) => c.seg === 0 || c.seg === Math.floor((c.of - 1) / 2))
  return [...coarse, ...clips.filter((c) => !coarse.includes(c))]
}

/** bytes of a clip in the codec and tier this page plays */
const size = (c: Clip) => c.files[codec][served(W, codec)]?.bytes ?? 0

async function run(p: Path) {
  abort?.abort()
  const ctl = (abort = new AbortController())
  await Promise.all([codecReady, avifReady])
  if (ctl.signal.aborted) return
  const clips = CLIPS[p]
  const keep = new Set(clips.map((c) => c.id))
  // the other path's clips go; the chapters both paths share stay cached
  for (const [id, u] of urls) if (!keep.has(id)) (URL.revokeObjectURL(u), urls.delete(id))
  path = p
  total = clips.reduce((a, c) => a + size(c), 0)
  done = clips.reduce((a, c) => a + (urls.has(c.id) ? size(c) : 0), 0)
  emit()
  const queue = order(clips).filter((c) => !urls.has(c.id))
  // nothing new starts while the visitor scrolls, so the scrub's progressive loads get the bandwidth; at idle coarse
  // first, with the near window last (the scrub is already loading those)
  const scrolling = () => performance.now() - lastMove < QUIET
  const near = (c: Clip) => c.chapter >= frame.index && c.chapter <= frame.index + NEAR
  const next = () => {
    if (scrolling()) return null
    // not a clip a decoder is downloading right now (that would be a second download); the near window last
    const free = (c: Clip) => !downloading(c.id)
    const k = queue.findIndex((c) => free(c) && !near(c))
    const j = k >= 0 ? k : queue.findIndex(free)
    return j < 0 ? null : queue.splice(j, 1)[0]
  }
  const fetchOne = async (c: Clip) => {
    // a decoder already has the whole clip from the network: count it, don't download it twice
    if (fullyLoaded(c.id)) {
      done += size(c)
      return emit()
    }
    const stop = new AbortController()
    ctl.signal.addEventListener('abort', () => stop.abort())
    loading.set(c.id, stop)
    try {
      const res = await fetch(clipUrl(c.id), { signal: stop.signal })
      if (!res.ok) return
      const blob = await res.blob()
      if (ctl.signal.aborted) return
      urls.set(c.id, URL.createObjectURL(blob))
      done += size(c)
      emit()
    } finally {
      loading.delete(c.id)
    }
  }
  await Promise.all(
    Array.from({ length: PARALLEL }, async () => {
      while (queue.length && !ctl.signal.aborted) {
        const c = next()
        if (c) {
          await fetchOne(c).catch(() => {})
          continue
        }
        await new Promise((r) => setTimeout(r, QUIET))
        // a clip a decoder finished downloading counts as cached
        for (const q of [...queue])
          if (fullyLoaded(q.id)) {
            queue.splice(queue.indexOf(q), 1)
            done += size(q)
            emit()
          }
      }
    }),
  )
  // then the stage's posters (first frames, and the end frames desktop shows when scrolling back into a clip), held as
  // decoded images, and the page's lazy images (products), so nothing below is fetched during the scroll either
  const media = chaptersFor(p).flatMap((ch) => ch.media)
  const posters = [
    ...new Set([
      ...media.map((m) => posterFor(m)).filter((u): u is string => !!u),
      ...(env.mobile ? [] : media.flatMap((m) => (m.kind === 'video' ? [endPosterUrl(m.id)] : []))),
    ]),
  ]
  const warmImage = (src: string) =>
    new Promise<void>((done) => {
      const img = new Image()
      img.onload = img.onerror = () => done()
      img.src = src
      images.push(img)
    })
  await Promise.all(
    Array.from({ length: PARALLEL }, async () => {
      while (posters.length && !ctl.signal.aborted) await warmImage(posters.shift()!)
    }),
  )
  if (!ctl.signal.aborted) document.querySelectorAll<HTMLImageElement>('main img[loading="lazy"]').forEach((img) => (img.loading = 'eager'))
  // last, the globe the film ends on: its code, its placeholder frame and its texture
  if (!ctl.signal.aborted) {
    void import('../three/Globe').catch(() => {})
    images.push(warmGlobePlaceholder(await avifReady))
    void fetch(GLOBE_TEXTURE).then((r) => r.arrayBuffer()).catch(() => {})
  }
}

/** Starts after the loader's reveal (LCP is long past by then) in idle time, and follows path switches. */
export function startWarmCache() {
  if (env.saveData || env.slow) return () => {}
  let started = false
  const idle = (f: () => void) => ('requestIdleCallback' in window ? requestIdleCallback(f, { timeout: 2000 }) : setTimeout(f, 300))
  // after the reveal and once the clip on screen can play through (or 4 s after the reveal at the latest), in idle time
  let settled = false
  let revealed = store.getState().revealed
  let late = 0
  const go = () => {
    if (started || !revealed || !settled) return
    started = true
    clearTimeout(late)
    idle(() => void run(store.getState().path))
  }
  const onSettled = () => ((settled = true), go())
  addEventListener('scrub:settled', onSettled, { once: true })
  const reveal = () => {
    revealed = true
    late = window.setTimeout(onSettled, 4000)
    go()
  }
  if (revealed) reveal()
  const stop = store.subscribe((s, was) => {
    if (s.revealed && !was.revealed) reveal()
    if (path && s.path !== path) void run(s.path)
  })
  return () => (stop(), clearTimeout(late), removeEventListener('scrub:settled', onSettled))
}
