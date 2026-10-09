import gsap from 'gsap'
import { useEffect } from 'react'
import { env } from '../engine/env'
import { preloadCritical } from '../engine/preload'
import { store } from '../engine/store'
import { lockScroll, unlockScroll } from '../engine/ticker'

const MIN_MS = 300

/**
 * Intro loader (STORY §0). Its markup and CSS are static in index.html so it paints before any JS;
 * this component drives it: real byte progress, scroll locked until ready, then the mark flies to the header.
 */
export function Loader() {
  useEffect(() => {
    const root = document.getElementById('boot')
    if (!root) return
    const bar = root.querySelector<HTMLElement>('.loader__bar')!
    const pct = root.querySelector<HTMLElement>('.loader__pct')!
    const mark = root.querySelector<HTMLElement>('.loader__mark')!
    lockScroll()
    let shown = 0
    const t0 = performance.now()
    const set = (f: number) => {
      if (f <= shown) return // never move backwards
      shown = f
      bar.style.transform = `scaleX(${f})`
      const n = Math.round(f * 100)
      pct.textContent = `${n}%`
      root.setAttribute('aria-valuenow', String(n))
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
      const tl = gsap.timeline({ onComplete: done })
      const target = document.querySelector('[data-brand-mark]')?.getBoundingClientRect()
      const from = mark.getBoundingClientRect()
      if (target && target.width) {
        tl.to(mark, {
          x: target.left + target.width / 2 - (from.left + from.width / 2),
          y: target.top + target.height / 2 - (from.top + from.height / 2),
          scale: target.width / from.width,
          duration: 0.6,
          ease: 'power3.inOut',
        })
      }
      tl.to(root, { autoAlpha: 0, duration: 0.6, ease: 'power2.out' }, target ? 0.15 : 0)
    })
    return () => {
      cancelled = true
    }
  }, [])
  return null
}
