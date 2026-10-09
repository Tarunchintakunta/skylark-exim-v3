import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'
import { env } from './env'
import { frame } from './store'

gsap.registerPlugin(ScrollTrigger)

type TickFn = (time: number) => void
let subs: { fn: TickFn; order: number }[] = []
let lenis: Lenis | null = null
let started = false

/** One clock for everything (TRD §1): gsap.ticker drives Lenis, ScrollTrigger and every per-frame callback. */
export function startEngine() {
  if (started) return
  started = true
  history.scrollRestoration = 'manual'
  // Touch and reduced motion keep native scrolling.
  if (!env.coarse && !env.reduced) {
    lenis = new Lenis({ autoRaf: false, lerp: 0.1, wheelMultiplier: 1, smoothWheel: true, syncTouch: false })
    lenis.on('scroll', ScrollTrigger.update)
  }
  if (env.coarse) ScrollTrigger.config({ ignoreMobileResize: true })
  ScrollTrigger.normalizeScroll(false)
  gsap.ticker.lagSmoothing(0)
  gsap.ticker.add(tick)
}

function tick(time: number) {
  lenis?.raf(time * 1000)
  const y = lenis ? lenis.scroll : window.scrollY
  if (y !== frame.scroll) frame.dir = y > frame.scroll ? 1 : -1
  frame.scroll = y
  for (const s of subs) s.fn(time)
}

/**
 * Register a per-frame callback. Write only to refs, style.transform/opacity, video.currentTime or three uniforms.
 * Lower `order` runs first (the film controller uses -10 so everyone else reads this frame's chapter progress).
 */
export function onTick(fn: TickFn, order = 0) {
  subs = [...subs, { fn, order }].sort((a, b) => a.order - b.order)
  return () => void (subs = subs.filter((s) => s.fn !== fn))
}

const SCROLL_KEYS = new Set([' ', 'PageDown', 'PageUp', 'ArrowDown', 'ArrowUp', 'Home', 'End'])
const swallowKey = (e: KeyboardEvent) => {
  if (SCROLL_KEYS.has(e.key)) e.preventDefault()
}
const swallow = (e: Event) => e.preventDefault()

export function lockScroll() {
  lenis?.stop()
  document.documentElement.classList.add('is-locked')
  addEventListener('keydown', swallowKey, { capture: true })
  addEventListener('wheel', swallow, { passive: false })
  addEventListener('touchmove', swallow, { passive: false })
}

export function unlockScroll() {
  document.documentElement.classList.remove('is-locked')
  removeEventListener('keydown', swallowKey, { capture: true })
  removeEventListener('wheel', swallow)
  removeEventListener('touchmove', swallow)
  lenis?.start()
}

export function scrollToY(y: number, immediate = false) {
  if (lenis) lenis.scrollTo(y, { immediate, duration: 1.4, force: true })
  else window.scrollTo({ top: y, behavior: immediate || env.reduced ? 'instant' : 'smooth' })
}
