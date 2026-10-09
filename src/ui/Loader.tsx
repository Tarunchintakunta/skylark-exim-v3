import gsap from 'gsap'
import { useEffect } from 'react'
import { env } from '../engine/env'
import { preloadCritical } from '../engine/preload'
import { store } from '../engine/store'
import { lockScroll, unlockScroll } from '../engine/ticker'

/** the mark needs ~0.8 s to draw; preload.ts caps the wait at 2.5 s */
const MIN_MS = 800

/**
 * Intro loader (STORY §0). Its markup and CSS are static in index.html so it paints before any JS;
 * this component drives it: the mark draws, a hairline shows real progress of the opening clip, scroll is locked until
 * ready, then the mark grows and dissolves into the first frame.
 */
export function Loader() {
  useEffect(() => {
    const root = document.getElementById('boot')
    if (!root) return
    const bar = root.querySelector<HTMLElement>('.loader__bar')!
    const mark = root.querySelector<HTMLElement>('.loader__mark')!
    lockScroll()
    let shown = 0
    const t0 = performance.now()
    const set = (f: number) => {
      if (f <= shown) return // never move backwards
      shown = f
      bar.style.transform = `scaleX(${f})`
      root.setAttribute('aria-valuenow', String(Math.round(f * 100)))
    }
    let cancelled = false
    preloadCritical(set).then(async () => {
      await new Promise((r) => setTimeout(r, Math.max(0, MIN_MS - (performance.now() - t0))))
      if (cancelled) return
      set(1)
      store.setState({ ready: true })
      document.documentElement.dataset.ready = '1'
      const done = () => {
        unlockScroll()
        root.remove()
      }
      if (env.reduced) {
        gsap.to(root, { autoAlpha: 0, duration: 0.2, onComplete: done })
        return
      }
      // logo reveal: the mark grows and dissolves while a circular hole opens from the centre onto the moving first frame
      const tl = gsap.timeline({ onComplete: done })
      tl.to(root.querySelector('.loader__track'), { autoAlpha: 0, duration: 0.25 }, 0)
      tl.to(mark, { scale: 7, autoAlpha: 0, duration: 1.0, ease: 'power3.in' }, 0)
      tl.to(root, { '--r': `${Math.hypot(innerWidth, innerHeight) / 2 + 2}px`, duration: 1.0, ease: 'power3.inOut' }, 0.15)
    })
    return () => {
      cancelled = true
    }
  }, [])
  return null
}
