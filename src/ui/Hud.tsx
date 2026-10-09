import gsap from 'gsap'
import { useEffect, useRef } from 'react'
import type { HudState } from '../config/hud'
import { film } from '../film/controller'
import { frame, useApp } from '../engine/store'
import { onTick } from '../engine/ticker'
import './hud.css'

/**
 * Cold-chain HUD (PRD F5): workflow step 01–09 + name + state; temperature only at cold storage.
 * Desktop: glass panel on the right edge. < 768 px: slim top bar. All updates are direct DOM writes on change.
 */
export function Hud() {
  const ready = useApp((s) => s.ready)
  const root = useRef<HTMLElement>(null)
  const num = useRef<HTMLSpanElement>(null)
  const name = useRef<HTMLSpanElement>(null)
  const state = useRef<HTMLSpanElement>(null)
  const temp = useRef<HTMLSpanElement>(null)
  const line = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ready) return
    let last: HudState | null = null
    let op = -1
    let shownStep = 0
    const counter = { v: 0 }
    return onTick(() => {
      const ch = film.chapters[frame.index]
      if (!ch) return
      // fades out at the end of the globe chapter
      const isLast = frame.index === film.chapters.length - 1
      const o = frame.past ? 0 : isLast ? 1 - Math.min(1, Math.max(0, (frame.local - 0.85) / 0.15)) : 1
      if (o !== op) {
        op = o
        root.current!.style.opacity = String(o)
        root.current!.style.visibility = o > 0 ? 'visible' : 'hidden'
      }
      line.current!.style.setProperty('--p', String(Math.min(1, frame.scroll / Math.max(1, film.end - innerHeight))))

      let h = ch.hud[0]
      for (const s of ch.hud) if (frame.local >= s.at) h = s
      if (h === last) return
      last = h
      const step = Number(h.step)
      if (step !== shownStep) {
        gsap.to(counter, {
          v: step, duration: 0.45, ease: 'power2.out', overwrite: true,
          onUpdate: () => (num.current!.textContent = String(Math.round(counter.v)).padStart(2, '0')),
        })
        shownStep = step
      }
      name.current!.textContent = h.name
      state.current!.textContent = h.state ?? ''
      state.current!.hidden = !h.state
      temp.current!.textContent = h.temp ?? ''
      temp.current!.hidden = !h.temp
    })
  }, [ready])

  return (
    <aside className="hud mono" ref={root} aria-label="Cold chain">
      <div className="hud__panel">
        <span className="hud__label">Cold chain · step</span>
        <p className="hud__step" aria-live="polite">
          <span className="hud__num" ref={num}>01</span>
          <span className="hud__of">/ 09</span>
          <span className="hud__name" ref={name} />
        </p>
        <span className="hud__state" ref={state} />
        <span className="hud__temp" ref={temp} hidden />
      </div>
      <div className="hud__track" aria-hidden="true">
        <div className="hud__line" ref={line} />
      </div>
    </aside>
  )
}
