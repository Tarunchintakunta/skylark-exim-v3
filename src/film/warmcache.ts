import { env } from '../engine/env'
import { store, type Path } from '../engine/store'
import { CLIPS, SEQ, type Clip } from './manifest'
import { prefetchSeq, seqProgress } from './scrub'
import { W, avifReady, clipUrl, codec, codecReady, isSeq, served } from './segments'

/**
 * Warm cache, all up front (Terminal Industries' pattern): at mount the whole active path goes into memory before the
 * story opens. Every video clip becomes a Blob (the stage's <video>s play from blob: URLs, so a seek never touches the
 * network) and every desktop frame sequence lands in the decode worker's byte store (sequence.ts), in story order. The
 * intro (Loader.tsx) shows the percentage and opens once the path is in hand; a path switch loads the other path's
 * clips the same way, keeping the chapters both share. Only the active path, at the page's own tier, in one codec
 * (it waits for segments.ts to settle the codec). Save-Data and 2g/3g skip it: the scrub's distance prefetch (scrub.ts)
 * streams those.
 */
/** clips fetched at once (Terminal's concurrency): 6 desktop, 3 phone */
const PARALLEL = env.mobile ? 3 : 6
/** the clips the cache holds as Blobs: a desktop frame-sequence clip (#hd2) is the stage canvas's, not a video */
const videos = (p: Path) => CLIPS[p].filter((c) => !isSeq(c.id))
const frameSets = (p: Path) => CLIPS[p].filter((c) => isSeq(c.id))
export const enabled = !(env.saveData || env.slow)

const urls = new Map<string, string>()
let path: Path | null = null
let abort: AbortController | null = null
/** the whole active path is in hand. Tests wait for this. */
let warm = false
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((f) => f())

// what the cache holds, for tests (navigator.webdriver) and ?debug only
if (navigator.webdriver || new URLSearchParams(location.search).has('debug'))
  Object.defineProperty(globalThis, '__warmCache', { get: () => ({ path, ids: [...urls.keys()], progress: progress(), warm }) })

/** blob: URL for a cached clip of the active path, else null */
export const cachedUrl = (id: string) => urls.get(id) ?? null

/** bytes of a clip in the codec and tier this page plays (a frame set: its frames, AVIF or WebP) */
const size = (c: Clip) => (isSeq(c.id) ? SEQ[c.id][avif ? 'avif' : 'webp'] : (c.files[codec][served(W, codec)]?.bytes ?? 0))
let avif = false
void avifReady.then((a) => (avif = a))

/** 0..1 of the active path's bytes in memory: its clips' Blobs and its frame sets' bytes */
export function progress() {
  if (!path) return 0
  const all = [...videos(path), ...frameSets(path)]
  const total = all.reduce((a, c) => a + size(c), 0)
  const have = all.reduce((a, c) => a + size(c) * (isSeq(c.id) ? seqProgress(c.id) : urls.has(c.id) ? 1 : 0), 0)
  return total ? have / total : 0
}
export function onCache(f: () => void) {
  listeners.add(f)
  return () => void listeners.delete(f)
}

/** resolves once the active path is in memory (at once where the cache is off) */
export const pathReady = () =>
  new Promise<void>((done) => {
    if (!enabled || warm) return done()
    const off = onCache(() => warm && (off(), done()))
  })

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
  // story order: the first chapter first, so a visitor who opens the intro early still finds the start in hand
  const queue = clips.filter((c) => !urls.has(c.id))
  const fetchOne = async (c: Clip) => {
    const res = await fetch(clipUrl(c.id), { signal: ctl.signal })
    if (!res.ok) return
    const blob = await res.blob()
    if (ctl.signal.aborted) return
    urls.set(c.id, URL.createObjectURL(blob))
    emit()
  }
  // the frame sets start with the videos: the worker fetches them PARALLEL at a time, frame 0 first, then coarse first
  for (const c of frameSets(p)) prefetchSeq(c.id)
  await Promise.all(
    Array.from({ length: PARALLEL }, async () => {
      while (queue.length && !ctl.signal.aborted) await fetchOne(queue.shift()!).catch(() => {})
    }),
  )
  // the frame sets report through scrub.ts; follow them until every byte is here
  while (!ctl.signal.aborted && progress() < 1) {
    emit()
    await new Promise((r) => setTimeout(r, 250))
  }
  if (!ctl.signal.aborted) {
    warm = true
    emit()
  }
}

/** Starts at mount, before the intro opens, and follows path switches. */
export function startWarmCache() {
  if (!enabled) return () => {}
  void run(store.getState().path)
  return store.subscribe((s) => {
    if (path && s.path !== path) void run(s.path)
  })
}
