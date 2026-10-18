import { chaptersFor } from '../config/chapters'
import { env } from '../engine/env'
import { frame, store, type Path } from '../engine/store'
import { GLOBE_TEXTURE, warmGlobePlaceholder } from '../three/globeState'
import { CLIPS, type Clip } from './manifest'
import { downloading, fullyLoaded, prefetchSeq } from './scrub'
import { W, avifReady, clipUrl, codec, codecReady, endPosterUrl, isSeq, posterFor, served } from './segments'

/**
 * Warm cache (#251): once the first screen is up, one loader fetches the active path's clips into Blobs, so the
 * stage's <video>s play from blob: URLs and a seek never touches the network. Desktop (#hd2, 2560 clips up to 60 MB a
 * path) keeps to a window around the chapter on screen, WINDOW chapters behind and ahead, and follows the scroll: the
 * first load stays the first chapters' worth, and a reader who stops halfway never downloads the rest. Phones (12 MB
 * a path) still take the whole path. Only the active path, at the page's own
 * tier and in one codec (#hd: it waits for segments.ts to settle the codec). Every clip gets its own Blob, including
 * one a decoder has already downloaded in full: without a Blob that clip is fetched again the next time a decoder takes
 * it, which was the one request a warm scroll still made (#264; /media is immutable, so the refetch is a cache hit).
 * Those clips are fetched last, so a slow link spends its bandwidth on clips nothing holds yet.
 * Coarse first: the first and the middle clip
 * of each chapter in story order, then the rest, so a fast scroll meets something cached everywhere early. Save-Data
 * and 2g/3g keep the distance prefetch only (scrub.ts), which stays the fallback for clips not cached yet.
 */
/** clips fetched at once (#264, Terminal's concurrency): 6 desktop, 3 phone */
const PARALLEL = env.mobile ? 3 : 6
/** ms since the last scroll that still counts as scrolling */
const QUIET = 400
/** chapters ahead of the one on screen that the scrub loads itself while the visitor scrolls */
const NEAR = 2
/** desktop: chapters behind and ahead of the one on screen whose clips the cache fetches (#hd2); phones: the whole path */
const WINDOW = 1
const windowed = !env.mobile
/** the clips the cache holds as Blobs: a desktop frame-sequence clip (#hd2) is the stage canvas's, not a video */
const videos = (p: Path) => CLIPS[p].filter((c) => !isSeq(c.id))
/** a clip the cache fetches now: on desktop within WINDOW chapters of the one on screen, on phones every clip */
const inWindow = (c: Clip) => !windowed || Math.abs(c.chapter - frame.index) <= WINDOW
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
/** the whole routine is through: clips (desktop: the first window), posters, the page's lazy images and the globe. Tests wait for this (#264). */
let warm = false
const listeners = new Set<() => void>()
/** decoded posters, held so the document's list of available images serves them to the stage without a request */
const images: HTMLImageElement[] = []
const emit = () => listeners.forEach((f) => f())

// what the cache holds, for tests (navigator.webdriver) and ?debug only
if (navigator.webdriver || new URLSearchParams(location.search).has('debug'))
  Object.defineProperty(globalThis, '__warmCache', { get: () => ({ path, ids: [...urls.keys()], progress: progress(), warm }) })

/** fetches in flight, by clip: a scroll cancels them (see below) */
const loading = new Map<string, AbortController>()

/** blob: URL for a cached clip of the active path, else null */
export const cachedUrl = (id: string) => urls.get(id) ?? null
/** 0..1 of the clip bytes the cache wants now in hand: the window around the chapter on screen (desktop), the path (phones) */
export function progress() {
  const want = path ? videos(path).filter(inWindow) : []
  const total = want.reduce((a, c) => a + size(c), 0)
  // (desktop: a clip a decoder holds whole is as good as cached; the cache leaves it to the decoder)
  return total ? want.reduce((a, c) => a + (urls.has(c.id) || (windowed && fullyLoaded(c.id)) ? size(c) : 0), 0) / total : 0
}
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
  warm = false
  abort?.abort()
  const ctl = (abort = new AbortController())
  await Promise.all([codecReady, avifReady])
  if (ctl.signal.aborted) return
  const clips = videos(p)
  const keep = new Set(clips.map((c) => c.id))
  // the other path's clips go; the chapters both paths share stay cached
  for (const [id, u] of urls) if (!keep.has(id)) (URL.revokeObjectURL(u), urls.delete(id))
  path = p
  emit()
  const queue = order(clips).filter((c) => !urls.has(c.id))
  // nothing new starts while the visitor scrolls, so the scrub's progressive loads get the bandwidth; at idle coarse
  // first, with the near window last (the scrub is already loading those)
  const scrolling = () => performance.now() - lastMove < QUIET
  const near = (c: Clip) => c.chapter >= frame.index && c.chapter <= frame.index + NEAR
  const next = () => {
    if (scrolling()) return null
    // not a clip a decoder is downloading right now (that would be a second download), and on desktop only inside the
    // window; then, in order: phones a clip no decoder holds and that is not in the near window, desktop one in the
    // chapter on screen, then one ahead; then any clip no decoder holds, and last (phones only) a clip a decoder already
    // has in full — that one only needs its Blob, and on a slow link the progressive loads want the bandwidth more
    // (#264). Desktop leaves those to the decoder: streaming, a second fetch of a clip already held is bytes for nothing
    // when the HTTP cache is cold (it measured 62.5 MB a path against 58.7 MB of files, #hd2)
    const free = (c: Clip) => !downloading(c.id) && inWindow(c)
    const first = (test: (c: Clip) => boolean) => queue.findIndex((c) => free(c) && test(c))
    const open = (c: Clip) => !fullyLoaded(c.id)
    const tests = windowed
      ? [(c: Clip) => open(c) && c.chapter === frame.index, (c: Clip) => open(c) && c.chapter > frame.index, open]
      : [(c: Clip) => !near(c) && open(c), open, () => true]
    const j = tests.map(first).find((k) => k >= 0) ?? -1
    return j < 0 ? null : queue.splice(j, 1)[0]
  }
  const fetchOne = async (c: Clip) => {
    const stop = new AbortController()
    ctl.signal.addEventListener('abort', () => stop.abort())
    loading.set(c.id, stop)
    try {
      const res = await fetch(clipUrl(c.id), { signal: stop.signal })
      if (!res.ok) return
      const blob = await res.blob()
      if (ctl.signal.aborted) return
      urls.set(c.id, URL.createObjectURL(blob))
      emit()
    } finally {
      loading.delete(c.id)
    }
  }
  let shown = -1
  const workers = Promise.all(
    Array.from({ length: PARALLEL }, async () => {
      while (queue.length && !ctl.signal.aborted) {
        const c = next()
        if (c) {
          const cut = await fetchOne(c).then(() => false, (e: unknown) => (e as Error)?.name === 'AbortError')
          // desktop: a fetch a scroll cancelled goes back in the queue, for when the window comes round to it again
          if (windowed && cut && !urls.has(c.id) && !ctl.signal.aborted) queue.push(c)
          continue
        }
        // the hairline follows what is in hand: on desktop the window moves with the scroll, and a decoder finishing a
        // window clip completes it without a fetch here; frame sequences in the window start fetching (frame 0 first,
        // then coarse first: sequence.ts)
        if (progress() !== shown) ((shown = progress()), emit())
        if (!scrolling()) for (const c of CLIPS[p]) if (isSeq(c.id) && inWindow(c)) prefetchSeq(c.id)
        await new Promise((r) => setTimeout(r, QUIET))
      }
    }),
  )
  // desktop: the first window, then the rest of the routine; the workers go on following the scroll (phones: the path)
  // (a window clip a decoder is downloading or holds whole counts as handled)
  if (windowed) while (!ctl.signal.aborted && (loading.size || queue.some((c) => inWindow(c) && !downloading(c.id) && !fullyLoaded(c.id)))) await new Promise((r) => setTimeout(r, QUIET))
  else await workers
  // then the stage's posters (first frames, and the end frames desktop shows when scrolling back into a clip), held as
  // decoded images, and the page's lazy images (products), so nothing below is fetched during the scroll either
  // (every poster of the path, desktop too: they are what a fast scroll shows ahead of the streamed clips; windowed,
  // a Fast 4G step scroll met segments with neither a clip nor a poster, tests/terminal-mode.spec.ts, #hd2)
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
    await fetch(await GLOBE_TEXTURE.film).then((r) => r.arrayBuffer()).catch(() => {})
  }
  if (!ctl.signal.aborted) {
    warm = true
    emit()
  }
  await workers
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
