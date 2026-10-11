import gsap from 'gsap'
import { useEffect, useRef } from 'react'
import { exportsLine, start } from '../config/content'
import { goTo, setPath } from '../engine/path'
import { frame, useApp } from '../engine/store'
import { onTick } from '../engine/ticker'
import './hero.css'

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
    // no intro animation: the same copy is already on screen from index.html (#207), above the loader
    gsap.set(el, { autoAlpha: 1 })
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
        <div className="hero__exports">
          <h2 className="hero__exports-title mono">{exportsLine.title}</h2>
          <ul>
            {exportsLine.items.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <a
          className="hero__contact"
          href="#quote"
          onClick={(e) => {
            e.preventDefault()
            goTo('quote')
          }}
        >
          Contact us
        </a>
        <a
          className="hero__path"
          href={`#${other}`}
          onClick={(e) => {
            e.preventDefault()
            setPath(other, true)
          }}
        >
          Or follow the {start[other].sub.toLowerCase()} →
        </a>
      </div>
      <span className="hero__cue" aria-hidden="true">
        Scroll
      </span>
    </div>
  )
}
