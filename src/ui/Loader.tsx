import gsap from 'gsap'
import { useEffect, useRef, useState } from 'react'
import { env } from '../engine/env'
import { preloadCritical } from '../engine/preload'
import { store } from '../engine/store'
import { lockScroll, unlockScroll } from '../engine/ticker'
import { Mark } from './Mark'
import './loader.css'

const MIN_MS = 300

/** Intro loader (STORY §0): real byte progress, scroll locked until ready, then the mark flies to the header. */
export function Loader() {
  const [gone, setGone] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const bar = useRef<HTMLDivElement>(null)
  const pct = useRef<HTMLSpanElement>(null)
  const mark = useRef<HTMLDivElement>(null)

  useEffect(() => {
    lockScroll()
    let shown = 0
    const t0 = performance.now()
    const set = (f: number) => {
      if (f <= shown) return // never move backwards
      shown = f
      bar.current!.style.transform = `scaleX(${f})`
      pct.current!.textContent = `${Math.round(f * 100)}%`
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
        setGone(true)
      }
      if (env.reduced) {
        gsap.to(root.current, { autoAlpha: 0, duration: 0.2, onComplete: done })
        return
      }
      const tl = gsap.timeline({ onComplete: done })
      const target = document.querySelector('[data-brand-mark]')?.getBoundingClientRect()
      const from = mark.current!.getBoundingClientRect()
      if (target && target.width) {
        tl.to(mark.current, {
          x: target.left + target.width / 2 - (from.left + from.width / 2),
          y: target.top + target.height / 2 - (from.top + from.height / 2),
          scale: target.width / from.width,
          duration: 0.6,
          ease: 'power3.inOut',
        })
      }
      tl.to(root.current, { autoAlpha: 0, duration: 0.6, ease: 'power2.out' }, target ? 0.15 : 0)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (gone) return null
  return (
    <div className="loader" ref={root} role="progressbar" aria-label="Loading Skylark Exim" aria-valuemin={0} aria-valuemax={100}>
      <div className="loader__mark" ref={mark}>
        <Mark className="loader__svg" />
      </div>
      <p className="loader__word mono">Skylark Exim</p>
      <div className="loader__track">
        <div className="loader__bar" ref={bar} />
      </div>
      <span className="loader__pct mono" ref={pct}>0%</span>
    </div>
  )
}
