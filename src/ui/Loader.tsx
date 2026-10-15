import gsap from 'gsap'
import { useEffect } from 'react'
import { env } from '../engine/env'
import { store } from '../engine/store'
import { resizeScroll } from '../engine/ticker'

/** sessionStorage key: set at the first reveal; index.html and story.html skip the intro on later loads in the same tab session */
const SEEN = 'skylark-intro'
/** how long the intro plays, from navigation start (reduced motion and deep links: SHORT_MS) */
const INTRO_MS = 1200
const SHORT_MS = 800
/** the cap the CSS failsafe in each page's own HTML uses too */
const MAX_MS = 3000

/**
 * Intro (STORY §0, #218). Its markup and CSS are static in the page's HTML, so it paints before any JS; the intro
 * itself (mark, name, wave line) is CSS. This component only ends it: the mark grows and a hole opens onto the page.
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
    if (!root || html.classList.contains('intro-skip') || performance.now() >= MAX_MS) {
      remember()
      handOff()
      return
    }
    // from here on this script owns the timing: stop the CSS failsafe fade
    root.style.animation = 'none'
    const mark = root.querySelector<HTMLElement>('.loader__mark')!
    const short = html.classList.contains('intro-short') || env.reduced
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
      if (env.reduced) {
        tl = gsap.timeline({ onComplete: handOff }).to(root, { autoAlpha: 0, duration: 0.3 })
        return
      }
      // the mark grows and dissolves while a circular hole opens from the centre onto the page
      mark.style.animation = 'none' // the CSS pulse animates opacity, which would win over the fade below
      tl = gsap.timeline({ onComplete: handOff })
      tl.to(root!.querySelector('.loader__side'), { autoAlpha: 0, duration: 0.25 }, 0)
      tl.to(mark, { scale: 7, autoAlpha: 0, duration: 0.8, ease: 'power3.in' }, 0)
      tl.to(root, { '--r': `${Math.hypot(innerWidth, innerHeight) / 2 + 2}px`, duration: 0.8, ease: 'power3.inOut' }, 0.1)
    }
    for (const e of MOVES) addEventListener(e, open, { passive: true })
    const timer = window.setTimeout(open, Math.max(0, (short ? SHORT_MS : INTRO_MS) - performance.now()))
    return () => {
      cancelled = true
      off()
      tl?.kill()
    }
  }, [])
  return null
}
