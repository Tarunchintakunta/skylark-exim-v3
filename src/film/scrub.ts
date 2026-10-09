import gsap from 'gsap'
import { env } from '../engine/env'
import { frame } from '../engine/store'
import { onTick } from '../engine/ticker'
import { clipUrl, endPosterUrl, posterFor, type Segment } from './segments'

/**
 * Video engine (TRD §6). Two <video> decoders: the current clip and the next one (prefetched at 50%).
 * Each tick: target = p * (duration - 1/24); seek only if the decoder is idle and the target moved > 1/48 s,
 * otherwise remember the newest target and apply it on `seeked`. The poster stays visible until a frame has painted.
 */
interface Slot {
  v: HTMLVideoElement
  id: string | null
  painted: boolean
  pending: number | null
  dead: boolean
}

const FRAME = 1 / 24
const EPS = 1 / 48

let segs: Segment[] = []
let posters: (HTMLElement | null)[] = []
let tags: (HTMLElement | null)[] = []
let slots: Slot[] = []
let veil: HTMLElement | null = null
let stage: HTMLElement | null = null
let cur = -1
let shown: Slot | null = null
let over = -1
let hidden = false
let stopTick: (() => void) | null = null

export function bindStage(el: HTMLElement, segments: Segment[]) {
  stage = el
  segs = segments
  posters = segments.map((_, i) => el.querySelector<HTMLElement>(`[data-seg="${i}"]`))
  tags = segments.map((_, i) => el.querySelector<HTMLElement>(`[data-ph="${i}"]`))
  veil = el.querySelector('.stage__veil')
  slots = [...el.querySelectorAll('video')].map((v) => makeSlot(v))
  cur = -1
  shown = null
  over = -1
  stopTick?.()
  stopTick = onTick(tick, -5)
  return () => {
    stopTick?.()
    stopTick = null
    for (const s of slots) release(s)
  }
}

function makeSlot(v: HTMLVideoElement): Slot {
  const s: Slot = { v, id: null, painted: false, pending: null, dead: false }
  v.muted = true // React doesn't reflect the muted attribute reliably
  const markPainted = () => {
    if (v.requestVideoFrameCallback) {
      let done = false
      v.requestVideoFrameCallback(() => (done = s.painted = true))
      // rVFC may not fire for a paused element in every browser; don't leave the poster up forever
      setTimeout(() => !done && v.readyState >= 2 && (s.painted = true), 120)
    } else s.painted = true
  }
  v.addEventListener('loadeddata', markPainted)
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
  s.v.src = clipUrl(id)
  s.v.load()
  // iOS Low Power Mode and friends: no decode → stay on posters for this clip
  setTimeout(() => {
    if (s.id === id && s.v.readyState < 2) s.dead = true
  }, 1500)
}

function release(s: Slot) {
  if (!s.id) return
  s.id = null
  s.painted = false
  s.v.removeAttribute('src')
  s.v.load()
  s.v.style.opacity = '0'
}

const videoId = (i: number) => {
  const m = segs[i]?.media
  return m?.kind === 'video' ? m.id : null
}

function slotFor(id: string, keep: string | null) {
  return (
    slots.find((s) => s.id === id) ??
    (() => {
      const free = (x: Slot) => x.id === null || x.id !== keep
      const s = slots.find((x) => x.id === null) ?? slots.find((x) => free(x) && x !== shown) ?? slots.find(free)!
      load(s, id)
      return s
    })()
  )
}

function setShown(s: Slot | null) {
  if (shown === s) return
  if (shown) shown.v.style.opacity = '0'
  if (s) s.v.style.opacity = '1'
  shown = s
}

function tick() {
  if (!segs.length) return
  // the whole film is off screen: stop all work and free decoders
  if (frame.past !== hidden) {
    hidden = frame.past
    if (stage) stage.style.visibility = hidden ? 'hidden' : 'visible'
    if (hidden) {
      setShown(null)
      for (const s of slots) release(s)
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

  // decoders: current + next (from 50%)
  const want = videoId(i)
  const next = p > 0.5 ? videoId(i + 1) : null
  let active: Slot | null = null
  if (want) {
    active = slotFor(want, next)
    seek(active, p)
  }
  if (next && next !== want) slotFor(next, want)
  setShown(active && active.painted && !active.dead ? active : null)

  // placeholders (stills and the port/sea gradients): slow push-in
  const m = seg.media
  if (m.kind === 'still' || m.kind === 'gradient') posters[i]!.style.transform = `scale(${1 + 0.04 * p})`

  // cross-fade join: next segment's poster fades in over the last 3% of scroll (x-ship → globe: 15%)
  const fadeLen = seg.join === 'crossfade' ? (segs[i + 1]?.media.kind === 'globe' ? 0.15 : 0.03) : 0
  const a = fadeLen ? Math.max(0, (p - (1 - fadeLen)) / fadeLen) : 0
  const o = a > 0 ? i + 1 : -1
  if (o !== over && over >= 0 && posters[over]) {
    posters[over]!.classList.remove('is-over')
    if (over !== cur) posters[over]!.style.opacity = '0'
  }
  over = o
  if (o >= 0 && posters[o]) {
    posters[o]!.classList.add('is-over')
    posters[o]!.style.opacity = String(a)
  }
}

function seek(s: Slot, p: number) {
  const v = s.v
  if (v.readyState < 1 || !Number.isFinite(v.duration)) return
  const t = p * Math.max(0, v.duration - FRAME)
  if (v.seeking) {
    s.pending = t
    return
  }
  if (Math.abs(v.currentTime - t) > EPS) v.currentTime = t
}

function enter(i: number, prev: number) {
  const fromBelow = prev > i
  if (prev >= 0 && tags[prev]) tags[prev]!.style.opacity = '0'
  if (tags[i]) tags[i]!.style.opacity = '1'
  if (prev >= 0 && posters[prev]) {
    posters[prev]!.style.opacity = '0'
    posters[prev]!.classList.remove('is-over')
  }
  const el = posters[i]
  if (el) {
    el.style.opacity = '1'
    // entering a clip from below: show its last frame until the decoder catches up
    const m = segs[i].media
    if (el instanceof HTMLImageElement && m.kind === 'video' && !env.mobile) {
      const want = fromBelow ? endPosterUrl(m.id) : posterFor(m)!
      if (!el.src.endsWith(want)) el.src = want
    }
  }
  // intentional cut (documentation → port): 250 ms fade through the page colour
  const crossedCut = prev >= 0 && (segs[Math.min(i, prev)].join === 'cut')
  if (crossedCut && veil) gsap.fromTo(veil, { opacity: 1 }, { opacity: 0, duration: 0.25, ease: 'none' })
  cur = i
}

/** Preload the remaining first-frame posters (after the loader) and the end posters (desktop). */
export function preloadPosters() {
  for (const s of segs) {
    const m = s.media
    if (m.kind === 'video' && !env.mobile) new Image().src = endPosterUrl(m.id)
  }
}
