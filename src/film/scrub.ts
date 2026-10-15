import gsap from 'gsap'
import { env } from '../engine/env'
import { frame, store } from '../engine/store'
import { landing } from '../engine/path'
import { onTick } from '../engine/ticker'
import { clipUrl, endPosterUrl, posterFor, type Segment } from './segments'
import { cachedUrl } from './warmcache'

/**
 * Video engine (TRD §6, redesign §2.3-2.4). A pool of POOL <video> decoders.
 * - The current clip loads on entry; after the first scroll, once it has metadata, the next AHEAD clips in the scroll
 *   direction load in parallel (one more while the scroll is fast). A clip on screen for under a second can't wait for
 *   its neighbour to finish buffering first.
 * - A new clip takes the decoder whose clip is furthest from the current segment, never one inside that window.
 * - One seek in flight; the newest target is applied on `seeked`. Targets outside `buffered` are held for HOLD ms, so the
 *   last presented frame stays up instead of stalling or flashing back to the poster; after that the picture follows the
 *   buffered frame nearest the target, so it keeps moving with the page as the download arrives.
 * - `fastSeek()` while the scroll is fast,
 *   exact `currentTime` once it settles. Frames count as presented from `requestVideoFrameCallback`.
 */
interface Slot {
  v: HTMLVideoElement
  id: string | null
  painted: boolean
  pending: number | null
  /** when the current target was first found outside `buffered` (0: it wasn't) */
  holdSince: number
  dead: boolean
  /** fired loadeddata since the last load(): a slot that ever decoded a frame is never marked dead by the timer */
  loaded: boolean
  /** fired canplaythrough */
  ready: boolean
  /** last time this slot was the current clip (breaks eviction ties) */
  used: number
  /** playing from the warm cache's blob: URL (#251), so its seeks never touch the network */
  blob: boolean
}

const FRAME = 1 / 24
const EPS = 1 / 48
/** ms a target outside `buffered` is held before the picture moves to the nearest buffered frame */
const HOLD = 250
/** px per tick above which seeks use fastSeek (keyframe-accurate, cheaper) */
const FAST = 30
const light = env.mobile || env.saveData || env.slow
/** decoders on the stage (ScrubStage renders this many <video>s) */
export const POOL = env.mobile ? 4 : 5
/** clips prefetched ahead of the scroll: three on desktop, two on phones, Save-Data and 3G or slower; one more while fast */
const AHEAD = light ? 2 : 3

let segs: Segment[] = []
let posters: (HTMLElement | null)[] = []
let slots: Slot[] = []
/** one slot per <video> for the page's life: a path switch rebinds the stage but keeps what the decoders already hold */
const slotOf = new WeakMap<HTMLVideoElement, Slot>()
let veil: HTMLElement | null = null
let stage: HTMLElement | null = null
let cur = -1
let shown: Slot | null = null
let over = -1
let hidden = false
let isLight = false
let isSoft = false
let lastY = 0
/**
 * Read by tests/video-smoothness.spec.ts and tests/terminal-mode.spec.ts: the clip that should be on screen, the time
 * it should show, whether its decoder is the picture (`shown`) and whether the stage has a picture at all (`painted`:
 * the clip, or the poster, still, gradient or globe layer under it). Plain writes, no DOM.
 */
const probe = { id: null as string | null, target: 0, shown: false, chapter: -1, painted: false }
;(globalThis as { __scrub?: typeof probe }).__scrub = probe
// the decoder pool, for tests (navigator.webdriver) and ?debug only
if (navigator.webdriver || new URLSearchParams(location.search).has('debug'))
  Object.defineProperty(globalThis, '__scrubSlots', {
    get: () => slots.map((s) => ({ id: s.id, readyState: s.v.readyState, ready: s.ready, dead: s.dead, painted: s.painted })),
  })
let clock = 0
/** neighbours are only prefetched after the visitor first scrolls, so the first screen costs just the opening clip */
let scrolled = false
/**
 * The hero's looping video (#197) covers the start chapter: its clip loads in idle time after the loader's reveal (the
 * loader already buffered the path's first clip), so it's there on the first scroll without competing with the first screen.
 */
let primed = false
let stopTick: (() => void) | null = null
/** the clip on screen after the reveal can play through: the warm cache (#251) waits for this before it takes bandwidth */
let settled = false

export function bindStage(el: HTMLElement, segments: Segment[]) {
  stage = el
  segs = segments
  posters = segments.map((_, i) => el.querySelector<HTMLElement>(`[data-seg="${i}"]`))
  veil = el.querySelector('.stage__veil')
  slots = [...el.querySelectorAll('video')].map((v) => slotOf.get(v) ?? makeSlot(v))
  for (const s of slots) s.v.style.opacity = '0'
  cur = -1
  shown = null
  over = -1
  stopTick?.()
  stopTick = onTick(tick, -5)
  const stopReady = store.subscribe((st, was) => st.ready && !was.ready && cur >= 0 && loadPosters(cur))
  const prime = () => ('requestIdleCallback' in window ? requestIdleCallback(() => (primed = true), { timeout: 1000 }) : setTimeout(() => (primed = true), 200))
  const stopReveal = store.subscribe((st, was) => st.revealed && !was.revealed && prime())
  if (store.getState().revealed) prime()
  return () => {
    stopReady()
    stopReveal()
    stopTick?.()
    stopTick = null
  }
}

/**
 * Loader gate (#218): buffer these clips into free decoders before the reveal, so the chosen path's first chapter plays
 * on arrival. Returns their elements; the loader waits for `canplaythrough`.
 */
export function warm(ids: string[]) {
  return ids.flatMap((id) => slotFor(id, ids, 0)?.v ?? [])
}

function makeSlot(v: HTMLVideoElement): Slot {
  const s: Slot = { v, id: null, painted: false, pending: null, holdSince: 0, dead: false, loaded: false, ready: false, used: 0, blob: false }
  slotOf.set(v, s)
  v.muted = true // React doesn't reflect the muted attribute reliably
  const markPainted = () => {
    if (v.requestVideoFrameCallback) {
      let done = false
      v.requestVideoFrameCallback(() => (done = s.painted = true))
      // rVFC may not fire for a paused element in every browser; don't leave the poster up forever
      setTimeout(() => !done && v.readyState >= 2 && (s.painted = true), 120)
    } else s.painted = true
  }
  v.addEventListener('loadeddata', () => {
    s.loaded = true
    s.dead = false
    markPainted()
  })
  v.addEventListener('canplay', () => (s.dead = false))
  v.addEventListener('canplaythrough', () => (s.ready = true))
  v.addEventListener('error', () => (s.dead = true))
  v.addEventListener('seeked', () => {
    if (s.pending !== null && Math.abs(v.currentTime - s.pending) > EPS) {
      v.currentTime = s.pending
      s.pending = null
      return
    }
    s.pending = null
    s.dead = false
    markPainted()
  })
  return s
}

function load(s: Slot, id: string) {
  s.id = id
  s.painted = false
  s.pending = null
  s.dead = false
  s.loaded = false
  s.ready = false
  const cached = cachedUrl(id)
  s.blob = cached !== null
  // the clip id, readable whether the source is a file or a blob: URL
  s.v.dataset.clip = id
  s.v.src = cached ?? clipUrl(id)
  s.v.load()
  // iOS Low Power Mode and friends: no first frame after 4 s → posters until `loadeddata` arrives. Not readyState: it
  // drops below 2 during every seek, and a clip caught mid-seek would sit on its poster for the rest of the chapter.
  setTimeout(() => {
    if (s.id === id && !s.loaded) s.dead = true
  }, 4000)
}

const videoId = (i: number) => {
  const m = segs[i]?.media
  return m?.kind === 'video' ? m.id : null
}

/** A decoder is downloading `id` from the network right now: the warm cache leaves it alone until it's done. */
export const downloading = (id: string) => slots.some((s) => s.id === id && !s.blob && s.v.networkState === s.v.NETWORK_LOADING)

/** The next `n` distinct clips from segment i in direction d (skipping stills/globe). */
function clipsFrom(i: number, d: 1 | -1, n: number) {
  const out: string[] = []
  for (let k = i + d; k >= 0 && k < segs.length && out.length < n; k += d) {
    const id = videoId(k)
    if (id && !out.includes(id)) out.push(id)
  }
  return out
}

/** Segments between segment `at` and the nearest one playing `id` (Infinity: not on this path). */
function distance(id: string | null, at: number) {
  let best = Infinity
  segs.forEach((s, k) => s.media.kind === 'video' && s.media.id === id && (best = Math.min(best, Math.abs(k - at))))
  return best
}

/** Slot holding `id`, else load it into a free slot or the one whose clip is furthest from segment `at`, never one in `keep`. */
function slotFor(id: string, keep: (string | null)[], at: number) {
  const have = slots.find((s) => s.id === id)
  if (have) return have
  const free = slots.filter((x) => x !== shown && (x.id === null || !keep.includes(x.id)))
  const far = (x: Slot) => (x.id === null ? Infinity : distance(x.id, at))
  const s = free.sort((a, b) => far(b) - far(a) || a.used - b.used)[0]
  if (!s) return null
  load(s, id)
  return s
}

function setShown(s: Slot | null) {
  if (shown === s) return
  if (shown) shown.v.style.opacity = '0'
  if (s) s.v.style.opacity = '1'
  shown = s
}

function tick() {
  if (!segs.length) return
  clock++
  const vel = Math.abs(frame.scroll - lastY)
  lastY = frame.scroll
  // the whole film is off screen: stop all work, keep the decoders' sources so the way back doesn't re-download
  if (frame.past !== hidden) {
    hidden = frame.past
    if (stage) stage.style.visibility = hidden ? 'hidden' : 'visible'
    if (hidden) {
      setShown(null)
      clearLayers(-1)
      cur = -1
    }
  }
  if (hidden) return

  // current segment from (chapter, local)
  let i = segs.findIndex((s) => s.chapter === frame.index && frame.local < s.to)
  if (i < 0) i = segs.findLastIndex((s) => s.chapter === frame.index)
  if (i < 0) return
  const seg = segs[i]
  const p = Math.min(1, Math.max(0, (frame.local - seg.from) / (seg.to - seg.from)))

  if (i !== cur) enter(i, cur)

  // decoders: current now; the next AHEAD clips in the scroll direction once it has metadata (one more while fast)
  const want = videoId(i)
  const ahead = clipsFrom(i, frame.dir < 0 ? -1 : 1, Math.min(POOL - 1, AHEAD + (vel > FAST ? 1 : 0)))
  const keep = [want, ...ahead]
  let active: Slot | null = null
  // the start clip waits for the reveal: the hero loop covers it, and the loader's budget goes to the first chapter
  // of each path (#218); a deep link that is about to jump past the hero doesn't fetch it at all
  if (want && !(landing.pending && i === 0) && (scrolled || primed || i > 0)) {
    active = slotFor(want, keep, i)
    if (active) {
      active.used = clock
      seek(active, p, vel)
      probe.target = p * Math.max(0, (active.v.duration || 0) - FRAME)
    }
  }
  // a deep link (#ocean / #pond) lands mid-film: measure the first scroll from there, so it doesn't prefetch on arrival
  if (!scrolled && !landing.pending && Math.abs(frame.scroll - Math.max(0, landing.y)) > 2) {
    scrolled = true
    loadPosters(i)
  }
  if (scrolled && (!want || (active && (active.v.readyState >= 1 || active.dead)))) for (const id of ahead) slotFor(id, keep, i)
  setShown(active && active.painted && !active.dead ? active : null)
  // a decoder still on its network source moves to the warm cache's blob once that clip is cached: right away when it's
  // off screen, or while the hero still fully covers the start chapter, never under a clip the visitor is watching
  for (const s of slots) if (s.id && !s.blob && cachedUrl(s.id) && (s !== shown || (frame.index === 0 && frame.local < 0.05))) load(s, s.id)
  if (!settled && active?.ready && store.getState().revealed) {
    settled = true
    dispatchEvent(new Event('scrub:settled'))
  }
  probe.id = want
  probe.chapter = seg.chapter
  probe.shown = shown !== null && shown === active
  // something is on screen: the clip's decoder, or the layer under it (a poster, a still, a gradient or the globe)
  const layer = posters[i]
  probe.painted = probe.shown || (layer instanceof HTMLImageElement ? layer.complete && layer.naturalWidth > 0 : !!layer)

  // placeholders (stills and the port/sea gradients): slow push-in
  const m = seg.media
  if (m.kind === 'still' || m.kind === 'gradient') posters[i]!.style.transform = `scale(${1 + 0.04 * p})`

  // cross-fade join: next segment's poster fades in over the last 3% of scroll (the last sea shot → globe: 15%)
  const fadeLen = seg.join === 'crossfade' ? (segs[i + 1]?.media.kind === 'globe' ? 0.15 : 0.03) : 0
  const a = fadeLen ? Math.max(0, (p - (1 - fadeLen)) / fadeLen) : 0
  const o = a > 0 ? i + 1 : -1
  if (o !== over && over >= 0 && posters[over]) {
    posters[over]!.classList.remove('is-over')
    if (over !== cur) posters[over]!.style.opacity = '0'
  }
  over = o
  // the stage turns light (no dark scrim) once the globe owns the frame
  const light = seg.media.kind === 'globe' || (o >= 0 && segs[o].media.kind === 'globe' && a > 0.5)
  if (light !== isLight) {
    isLight = light
    stage?.classList.toggle('is-light', light)
  }
  const soft = seg.scrim === 'soft'
  if (soft !== isSoft) {
    isSoft = soft
    stage?.classList.toggle('is-soft', soft)
  }
  if (o >= 0 && posters[o]) {
    posters[o]!.classList.add('is-over')
    posters[o]!.style.opacity = String(a)
  }
}

function seek(s: Slot, p: number, vel: number, t0 = 0) {
  const v = s.v
  if (v.readyState < 1 || !Number.isFinite(v.duration)) return
  // no extra easing here: Lenis already smooths the scroll, a second lerp only adds lag behind the page
  let t = t0 + p * Math.max(0, v.duration - FRAME - t0)
  // hold the last presented frame while the range is still downloading; if the browser stopped preloading, the seek asks for it.
  // Held for more than HOLD ms: show the buffered frame nearest the target instead, so the picture doesn't sit still
  if (!buffered(v, t) && v.networkState === v.NETWORK_LOADING) {
    const now = performance.now()
    s.holdSince ||= now
    const near = now - s.holdSince > HOLD ? nearestBuffered(v, t) : null
    if (near === null) return
    t = near
  } else s.holdSince = 0
  if (v.seeking) {
    s.pending = t
    return
  }
  if (Math.abs(v.currentTime - t) <= EPS) return
  if (vel > FAST && v.fastSeek) v.fastSeek(t)
  else v.currentTime = t
}

function buffered(v: HTMLVideoElement, t: number) {
  const b = v.buffered
  for (let k = 0; k < b.length; k++) if (t >= b.start(k) - EPS && t <= b.end(k) + EPS) return true
  return false
}

/** The buffered time closest to `t` between the current frame and `t` (in the direction of travel), or null. */
function nearestBuffered(v: HTMLVideoElement, t: number) {
  const from = v.currentTime
  const lo = Math.min(from, t)
  const hi = Math.max(from, t)
  let best: number | null = null
  const b = v.buffered
  for (let k = 0; k < b.length; k++) {
    // a frame short of the range's end: the last buffered frame may not be complete yet
    const c = Math.min(Math.max(t, b.start(k)), Math.max(b.start(k), b.end(k) - FRAME))
    if (c >= lo && c <= hi && (best === null || Math.abs(c - t) < Math.abs(best - t))) best = c
  }
  return best
}

/** Every stage layer to opacity 0 except `keep`; clears the cross-fade overlay. */
function clearLayers(keep: number) {
  posters.forEach((el, k) => {
    if (!el || k === keep) return
    el.style.opacity = '0'
    el.classList.remove('is-over')
  })
  over = -1
}

/** Posters load lazily: this segment and the next two, but only this one until the loader is done (first screen = LCP). */
function loadPosters(i: number) {
  if (!scrolled) return
  const last = store.getState().ready ? i + 2 : i
  for (let k = i; k <= last; k++) {
    const p = posters[k]
    // the URL is taken here, not at render: by now the page knows whether AVIF decodes
    const src = segs[k] && posterFor(segs[k].media)
    if (p instanceof HTMLImageElement && !p.getAttribute('src') && src) p.src = src
  }
}

function enter(i: number, prev: number) {
  const fromBelow = prev > i
  // coming back from the business sections (or the first frame): nothing to fade from, start clean
  if (prev < 0) clearLayers(i)
  if (prev >= 0 && posters[prev]) {
    posters[prev]!.style.opacity = '0'
    posters[prev]!.classList.remove('is-over')
  }
  loadPosters(i)
  const el = posters[i]
  if (el) {
    el.style.opacity = '1'
    // entering a clip from below: show its last frame until the decoder catches up
    const m = segs[i].media
    if (el instanceof HTMLImageElement && m.kind === 'video' && !env.mobile) {
      const want = fromBelow ? endPosterUrl(m.id) : posterFor(m)!
      if (!el.src.endsWith(want)) el.src = want
      // the end frame is only needed for scrolling back into this clip from below (not on the first screen)
      else if (prev >= 0) new Image().src = endPosterUrl(m.id)
    }
  }
  // intentional cut (documentation → port): 250 ms fade through the page colour
  const crossedCut = prev >= 0 && (segs[Math.min(i, prev)].join === 'cut')
  if (crossedCut && veil) gsap.fromTo(veil, { opacity: 1 }, { opacity: 0, duration: 0.25, ease: 'none' })
  cur = i
}
