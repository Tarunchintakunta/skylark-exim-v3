import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'
import { useEffect, useRef, type KeyboardEvent } from 'react'
import { start } from '../config/content'
import { env } from '../engine/env'
import { goTo, setPath } from '../engine/path'
import { frame, store, useApp, type Path } from '../engine/store'
import { onTick } from '../engine/ticker'
import './start.css'

gsap.registerPlugin(SplitText)
const PATHS: Path[] = ['ocean', 'pond']

/** Fork screen over the `opening` clip (STORY §1). Fixed while the start chapter is on screen. */
export function StartScreen() {
  const path = useApp((s) => s.path)
  const ready = useApp((s) => s.ready)
  const root = useRef<HTMLDivElement>(null)
  const head = useRef<HTMLDivElement>(null)
  const btns = useRef<(HTMLButtonElement | null)[]>([])

  // headline reveals as the camera breaks the surface (≈60%); the whole screen fades over the last 15%
  useEffect(() => {
    if (!ready) return
    let revealed = false
    let op = -1
    const reveal = () => {
      revealed = true
      const h1 = head.current!.querySelector('h1')!
      gsap.set(head.current, { autoAlpha: 1 })
      if (env.reduced) return
      SplitText.create(h1, {
        type: 'lines', mask: 'lines', autoSplit: true,
        onSplit: (s) => gsap.from(s.lines, { yPercent: 100, duration: 0.9, stagger: 0.08, ease: 'power3.out' }),
      })
      gsap.from(head.current!.querySelectorAll('[data-fade]'), { y: 24, autoAlpha: 0, duration: 0.8, delay: 0.25, ease: 'power3.out' })
    }
    if (env.reduced) reveal()
    return onTick(() => {
      const atStart = frame.index <= 0
      if (!revealed && atStart && frame.local >= 0.55) reveal()
      const o = atStart ? 1 - Math.min(1, Math.max(0, (frame.local - 0.85) / 0.15)) : 0
      if (o !== op) {
        op = o
        root.current!.style.opacity = String(o)
        root.current!.style.visibility = o > 0 ? 'visible' : 'hidden'
      }
    })
  }, [ready])

  const begin = () => setPath(store.getState().path, true)
  const onKey = (e: KeyboardEvent) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
    e.preventDefault()
    const next = e.key === 'ArrowLeft' ? 'ocean' : 'pond'
    setPath(next)
    btns.current[PATHS.indexOf(next)]?.focus()
  }

  return (
    <div className="start" ref={root}>
      <p className="start__eyebrow mono">{start.eyebrow}</p>
      <a
        className="start__skip mono"
        href="#products"
        onClick={(e) => {
          e.preventDefault()
          goTo('products')
        }}
      >
        {start.skip} → Products
      </a>
      <div className="start__paths" role="group" aria-label="Choose a path" onKeyDown={onKey}>
        {PATHS.map((p, i) => {
          const c = start[p]
          const on = path === p
          return (
            <button
              key={p}
              ref={(el) => {
                btns.current[i] = el
              }}
              className={`path-btn path-btn--${p}`}
              aria-pressed={on}
              tabIndex={on ? 0 : -1}
              onClick={() => (on ? begin() : setPath(p))}
            >
              <span className="path-btn__label display">{c.label}</span>
              <span className="path-btn__sub mono">{on ? `${c.sub} · press to begin` : c.sub}</span>
            </button>
          )
        })}
      </div>
      <div className="start__head" ref={head}>
        <h1 className="start__title">{start.title}</h1>
        <p className="start__body" data-fade>{start.body}</p>
      </div>
      <p className="start__cue mono" aria-hidden="true">Scroll</p>
    </div>
  )
}
