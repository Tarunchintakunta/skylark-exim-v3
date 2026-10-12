import gsap from 'gsap'
import { useEffect } from 'react'
import { env } from '../engine/env'
import { storyReady } from '../engine/boot'
import { MAX_MS, gate } from '../engine/preload'
import { store } from '../engine/store'
import { lockScroll, unlockScroll } from '../engine/ticker'

/** sessionStorage key: set at the first reveal; index.html skips the intro on later loads in the same tab session */
const SEEN = 'skylark-intro'

/**
 * Intro loader (STORY §0, #218). Its markup and CSS are static in index.html so it paints before any JS; the intro
 * (mark, name, wave line) is CSS. This component drives the rest: the wave line fills with real progress (preload.ts), scroll
 * is locked until the reveal, then the mark grows and a hole opens onto the looping hero.
 * - min 1.2 s so the intro finishes drawing; 0.8 s on a deep link (#ocean / #pond) or with reduced motion
 * - max 3.0 s from navigation start, whatever is still loading; a CSS fade in index.html covers the case where this
 *   script itself arrives later than that
 * - a return visit in the same session never shows it (index.html adds .intro-skip before first paint)
 */
export function Loader() {
  useEffect(() => {
    const html = document.documentElement
    const root = document.getElementById('boot')
    // the site is shown once the story has mounted; the static hero copy stays until then (#207)
    const ready = () =>
      storyReady.then(() => {
        if (!store.getState().ready) {
          store.setState({ ready: true })
          html.dataset.ready = '1'
        }
      })
    const remember = () => {
      try {
        sessionStorage.setItem(SEEN, '1')
      } catch {
        // storage blocked: the intro shows again next time
      }
    }
    const handOff = () => {
      root?.remove()
      ready().then(() => document.getElementById('hero-static')?.remove())
    }
    if (!root || html.classList.contains('intro-skip') || performance.now() >= MAX_MS) {
      remember()
      handOff()
      return
    }
    // from here on this script owns the timing: stop the CSS failsafe fade
    root.style.animation = 'none'
    const bar = root.querySelector<SVGPathElement>('.loader__bar')!
    const mark = root.querySelector<HTMLElement>('.loader__mark')!
    lockScroll()
    let shown = 0
    const set = (f: number) => {
      if (f <= shown) return // never move backwards
      shown = f
      bar.style.strokeDashoffset = String(1 - f)
      root.setAttribute('aria-valuenow', String(Math.round(f * 100)))
    }
    let cancelled = false
    gate(set, html.classList.contains('intro-short') || env.reduced ? 800 : 1200).then(() => {
      if (cancelled) return
      set(1)
      remember()
      ready()
      const done = () => {
        unlockScroll()
        handOff()
      }
      if (env.reduced) {
        gsap.to(root, { autoAlpha: 0, duration: 0.3, onComplete: done })
        return
      }
      // the mark grows and dissolves while a circular hole opens from the centre onto the looping hero
      mark.style.animation = 'none' // the CSS pulse animates opacity, which would win over the fade below
      const tl = gsap.timeline({ onComplete: done })
      tl.to(root.querySelector('.loader__side'), { autoAlpha: 0, duration: 0.25 }, 0)
      tl.to(mark, { scale: 7, autoAlpha: 0, duration: 1.0, ease: 'power3.in' }, 0)
      tl.to(root, { '--r': `${Math.hypot(innerWidth, innerHeight) / 2 + 2}px`, duration: 1.0, ease: 'power3.inOut' }, 0.15)
    })
    return () => {
      cancelled = true
    }
  }, [])
  return null
}
