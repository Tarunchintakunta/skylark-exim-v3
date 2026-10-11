import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'
import { useEffect, useRef } from 'react'
import { exportsLine, start } from '../config/content'
import { env } from '../engine/env'
import { setPath } from '../engine/path'
import { frame, useApp } from '../engine/store'
import { onTick } from '../engine/ticker'
import './hero.css'

gsap.registerPlugin(SplitText)

/**
 * Hero frame (redesign §3): full-bleed moving footage behind (the stage), one editorial headline, one line of body,
 * a slim scroll cue and one text link to the other path. Fixed while the start chapter is on screen; fades over its last 15%.
 */
export function Hero() {
  const ready = useApp((s) => s.ready)
  const path = useApp((s) => s.path)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ready) return
    const el = root.current!
    gsap.set(el, { autoAlpha: 1 })
    if (!env.reduced) {
      SplitText.create(el.querySelector('h1'), {
        type: 'lines', mask: 'lines', autoSplit: true,
        onSplit: (s) => gsap.from(s.lines, { yPercent: 100, duration: 0.9, stagger: 0.08, delay: 0.35, ease: 'power3.out' }),
      })
      gsap.from(el.querySelectorAll('[data-fade]'), { y: 20, autoAlpha: 0, duration: 0.8, delay: 0.75, stagger: 0.08, ease: 'power3.out' })
    }
    let op = -1
    return onTick(() => {
      const o = frame.index <= 0 ? 1 - Math.min(1, Math.max(0, (frame.local - 0.85) / 0.15)) : 0
      if (o === op) return
      op = o
      el.style.opacity = String(o)
      el.style.visibility = o > 0 ? 'visible' : 'hidden'
    })
  }, [ready])

  const other = path === 'ocean' ? 'pond' : 'ocean'
  const [lead, last] = [start.title.replace(/ world\.$/, ''), 'world']
  return (
    <div className="hero" ref={root}>
      <div className="hero__copy">
        <h1 className="hero__title">
          {lead} <em>{last}</em>.
        </h1>
        {/* no fade: this paragraph is the LCP element on phones */}
        <p className="hero__body">{start.body}</p>
        <div className="hero__exports" data-fade>
          <h2 className="hero__exports-title mono">{exportsLine.title}</h2>
          <ul>
            {exportsLine.items.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <a className="hero__contact" href="/quote" data-fade>
          Contact us
        </a>
        <a
          className="hero__path"
          href={`#${other}`}
          data-fade
          onClick={(e) => {
            e.preventDefault()
            setPath(other, true)
          }}
        >
          Or follow the {start[other].sub.toLowerCase()} →
        </a>
      </div>
      <span className="hero__cue" data-fade aria-hidden="true">
        Scroll
      </span>
    </div>
  )
}
