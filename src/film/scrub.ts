import gsap from 'gsap'
import { env } from '../engine/env'
import { frame, store } from '../engine/store'
import { landing } from '../engine/path'
import { onTick } from '../engine/ticker'
import { FILM_W, clipUrl, endPosterUrl, posterFor, type Segment } from './segments'

/**
 * Video engine (TRD §6, redesign §2.3-2.4). A pool of three <video> decoders: previous, current and next clip.
 * - The current clip loads on entry; after the first scroll the next starts once the current fires `canplaythrough`, and the one after
 *   once the next can play through (direction-aware, so scrolling up prefetches upwards).
 * - One seek in flight; the newest target is applied on `seeked`. Targets outside `buffered` are held, so the last
 *   presented frame stays up instead of stalling or flashing back to the poster.
 * - `fastSeek()` while the scroll is fast,
 *   exact `currentTime` once it settles. Frames count as presented from `requestVideoFrameCallback`.
 */
interface Slot {
  v: HTMLVideoElement
  id: string | null
  painted: boolean
  pending: number | null
  dead: boolean
  /** fired canplaythrough: safe to start the neighbour */
  ready: boolean
  /** last time this slot was the current clip (pool eviction) */
  used: number
}

const FRAME = 1 / 24
const EPS = 1 / 48
/** px per tick above which seeks use fastSeek (keyframe-accurate, cheaper) */
const FAST = 30

let segs: Segment[] = []
let posters: (HTMLElement | null)[] = []
let slots: Slot[] = []
let veil: HTMLElement | null = null
let stage: HTMLElement | null = null
let cur = -1
let shown: Slot | null = null
let over = -1
let hidden = false
let isLight = false
let isSoft = false
let lastY = 0
/** Read by tests/video-smoothness.spec.ts: the clip that should be on screen and the time it should show. Plain writes, no DOM. */
const probe = { id: null as string | null, target: 0, shown: false, chapter: -1 }
;(globalThis as { __scrub?: typeof probe }).__scrub = probe
let clock = 0
/** neighbours are only prefetched after the visitor first scrolls, so the first screen costs just the opening clip */
let scrolled = false
/** The hero's looping video (#197) covers the start chapter: its clip loads after the loader, its posters after the first scroll. */
let stopTick: (() => void) | null = null

export function bindStage(el: HTMLElement, segments: Segment[]) {
  stage = el
  segs = segments
  posters = segments.map((_, i) => el.querySelector<HTMLElement>(`[data-seg="${i}"]`))
  veil = el.querySelector('.stage__veil')
  slots = [...el.querySelectorAll('video')].map((v) => makeSlot(v))
  cur = -1
  shown = null
  over = -1
  stopTick?.()
  stopTick = onTick(tick, -5)
  const stopReady = store.subscribe((st, was) => st.ready && !was.ready && cur >= 0 && loadPosters(cur))
  return () => {
    stopReady()
    stopTick?.()
    stopTick = null
    for (const s of slots) release(s)
  }
}

function makeSlot(v: HTMLVideoElement): Slot {
  const s: Slot = { v, id: null, painted: false, pending: null, dead: false, ready: false, used: 0 }
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
    s.dead = false
    markPainted()
  })
  v.addEventListener('canplaythrough', () => (s.ready = true))
  v.addEventListener('error', () => (s.dead = true))
  v.addEventListener('seeked', () => {
    if (s.pending !== null && Math.abs(v.currentTime - s.pending) > EPS) {
      v.currentTime = s.pending
      s.pending = null
      return
    }
    s.pending = null
    markPainted()
  })
  return s
}

function load(s: Slot, id: string) {
  s.id = id
  s.painted = false
  s.pending = null
  s.dead = false
  s.ready = false
  s.v.src = clipUrl(id, FILM_W)
  s.v.load()
  // iOS Low Power Mode and friends: no first frame after 4 s → posters until `loadeddata` arrives
  setTimeout(() => {
    if (s.id === id && s.v.readyState < 2) s.dead = true
  }, 4000)
}

function release(s: Slot) {
  if (!s.id) return
  s.id = null
  s.painted = false
  s.ready = false
  s.v.removeAttribute('src')
  s.v.load()
  s.v.style.opacity = '0'
}

const videoId = (i: number) => {
  const m = segs[i]?.media
  return m?.kind === 'video' ? m.id : null
}

/** Nearest video clip from segment i in direction d (skipping stills/globe), or null. */
function videoNear(i: number, d: 1 | -1) {
  for (let k = i + d; k >= 0 && k < segs.length; k += d) {
    const id = videoId(k)
    if (id) return id
  }
  return null
}

/** Nearest clip after the segment that plays `id`, in direction d. */
function videoNearId(id: string, d: 1 | -1) {
  const k = segs.findIndex((s) => s.media.kind === 'video' && s.media.id === id)
  return k < 0 ? null : videoNear(k, d)
}

/** Slot holding `id`, loading it into the least recently used slot not in `keep` if needed. */
function slotFor(id: string, keep: (string | null)[]) {
  const have = slots.find((s) => s.id === id)
  if (have) return have
  const free = slots.filter((x) => x !== shown && (x.id === null || !keep.includes(x.id)))
  const s = free.find((x) => x.id === null) ?? free.sort((a, b) => a.used - b.used)[0]
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

  // decoders: current now; the neighbour in the scroll direction once the current can play through
  const want = videoId(i)
  const ahead = videoNear(i, frame.dir < 0 ? -1 : 1)
  const behind = videoNear(i, frame.dir < 0 ? 1 : -1)
  let active: Slot | null = null
  // the start clip loads once the loader is done (behind the hero loop) so the hand-off has frames ready; a deep link
  // that is about to jump past the hero doesn't fetch it at all
  if (want && !(landing.pending && i === 0) && (scrolled || i > 0 || store.getState().ready)) {
    active = slotFor(want, [ahead, behind])
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
  if (ahead && scrolled && (!want || active?.ready)) {
    const a = slotFor(ahead, [want, behind])
    // the one after that once the next can play through too (short chapters pass in < 1 s); phones only ever prefetch the next
    const ahead2 = env.mobile ? null : videoNearId(ahead, frame.dir < 0 ? -1 : 1)
    if (a?.ready && ahead2) slotFor(ahead2, [want, ahead])
  }
  setShown(active && active.painted && !active.dead ? active : null)
  probe.id = want
  probe.chapter = seg.chapter
  probe.shown = shown !== null && shown === active

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
  const t = t0 + p * Math.max(0, v.duration - FRAME - t0)
  // hold the last presented frame while the range is still downloading; if the browser stopped preloading, the seek asks for it
  if (!buffered(v, t) && v.networkState === v.NETWORK_LOADING) return
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
    if (p instanceof HTMLImageElement && !p.getAttribute('src') && p.dataset.src) p.src = p.dataset.src
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
