import gsap from 'gsap'
import { useEffect } from 'react'
import { env } from '../engine/env'
import { store } from '../engine/store'
import { resizeScroll } from '../engine/ticker'

/** sessionStorage key: set at the first reveal; index.html and story.html skip the intro on later loads in the same tab session */
const SEEN = 'skylark-intro'
/** the intro holds its wordmark and filling hairline until INTRO_MS, then wipes away in WIPE_S: about 1.0 s in all (#270; the hard cap is 1.2 s) */
const INTRO_MS = 700
const WIPE_S = 0.3
/** the cap the CSS failsafe in each page's own HTML uses too */
const MAX_MS = 3000

/**
 * What must be ready when the intro opens (#274): `fn` runs once the page's own load has settled (the LCP poster is
 * in), in the first idle slice, in parallel with the hero frames; so it never competes with the first screen.
 */
export function duringIntro(fn: () => void) {
  const idle = () => ('requestIdleCallback' in window ? requestIdleCallback(() => fn(), { timeout: 400 }) : setTimeout(fn, 100))
  if (document.readyState === 'complete') idle()
  else addEventListener('load', idle, { once: true })
}

/**
 * Intro (STORY §0, #218, #270). Its markup and CSS are static in the page's HTML, so it paints before any JS; the intro
 * itself (the "Skylark Exim" wordmark, a hairline that fills, the first hero frame resolving behind it) is CSS. This component only ends it: the mark grows and a hole opens onto the page.
 *
 * Nothing is gated on it any more (#264, Terminal's pattern): no fonts, no clips, no scroll lock. The hero's first
 * frame and its headline paint under the overlay, the page scrolls from the first frame, and the real load progress is
 * the hairline in the story bar (Header.tsx, fed by the warm cache). A wheel, a touch, a key or a scroll opens the
 * intro at once, so it can never hold a visitor who wants to move. The static hero copy stays above the overlay until
 * it opens: Chrome ignores occluded text for LCP (#207).
 */
export function Loader({ mounted }: { mounted: Promise<void> }) {
  useEffect(() => {
    const html = document.documentElement
    const root = document.getElementById('boot')
    const remember = () => {
      try {
        sessionStorage.setItem(SEEN, '1')
      } catch {
        // storage blocked: the intro shows again next time
      }
    }
    /** the page's content has mounted; the intro's clock runs on its own and waits for nothing */
    const ready = () => {
      if (store.getState().ready) return
      store.setState({ ready: true })
      html.dataset.ready = '1'
      // the page just grew by its lazy content: Lenis would clamp the first wheel to the old height
      resizeScroll()
    }
    const whenMounted = mounted.then(ready)
    const handOff = () => {
      root?.remove()
      // the static copy only gives way once the page it hands over to is mounted
      void whenMounted.then(() => {
        document.getElementById('hero-static')?.remove()
        store.setState({ revealed: true })
      })
    }
    if (!root || html.classList.contains('intro-skip') || env.reduced || performance.now() >= MAX_MS) {
      remember()
      handOff()
      return
    }
    // from here on this script owns the timing: drop the CSS failsafe fade, keep the thinning overlay running
    root.style.animationName = 'loader-thin'
    let tl: gsap.core.Timeline | null = null
    let cancelled = false

    /** the first move of any kind opens the intro at once: the page below it is already live */
    const MOVES = ['wheel', 'touchstart', 'keydown', 'scroll', 'pointerdown'] as const
    const off = () => {
      clearTimeout(timer)
      for (const e of MOVES) removeEventListener(e, open)
    }
    function open() {
      if (cancelled || tl) return
      off()
      remember()
      // the wordmark lifts away while a circular hole opens from the centre onto the hero
      tl = gsap.timeline({ onComplete: handOff })
      tl.to(root!.querySelector('.loader__name'), { autoAlpha: 0, y: -6, duration: 0.2, ease: 'power2.in' }, 0)
      tl.to(root!.querySelector('.loader__line'), { autoAlpha: 0, duration: 0.2 }, 0)
      tl.to(root, { '--r': `${Math.hypot(innerWidth, innerHeight) / 2 + 2}px`, duration: WIPE_S, ease: 'power3.inOut' }, 0)
    }
    for (const e of MOVES) addEventListener(e, open, { passive: true })
    const timer = window.setTimeout(open, Math.max(0, INTRO_MS - performance.now()))
    return () => {
      cancelled = true
      off()
      tl?.kill()
    }
  }, [])
  return null
}
