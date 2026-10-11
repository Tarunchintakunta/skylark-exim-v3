import gsap from 'gsap'
import { useEffect, useRef } from 'react'
import { exportsLine, start } from '../config/content'
import { env } from '../engine/env'
import { setPath } from '../engine/path'
import { frame, useApp } from '../engine/store'
import { onTick } from '../engine/ticker'
import { FILM_W, clipUrl, posterUrl } from '../film/segments'
import './hero.css'

/**
 * Hero frame (redesign §3): a full-bleed looping coastal video (#197) that dissolves into the scrubbed story, one editorial headline, one line of body,
 * a slim scroll cue and one text link to the other path. Fixed while the start chapter is on screen; fades over its last 15%.
 */
export function Hero() {
  const ready = useApp((s) => s.ready)
  const path = useApp((s) => s.path)
  const root = useRef<HTMLDivElement>(null)
  const video = useRef<HTMLVideoElement>(null)
  const media = useRef<HTMLDivElement>(null)

  // the loop plays only while it can be seen: off-screen (hero faded out) or a hidden tab pauses it
  useEffect(() => {
    const v = video.current
    const m = media.current!
    if (!v || env.reduced) return
    let inView = true
    const sync = () => (inView && !document.hidden && m.style.opacity !== '0' ? v.play().catch(() => {}) : v.pause())
    const io = new IntersectionObserver(([e]) => {
      inView = e.isIntersecting
      sync()
    })
    io.observe(v)
    document.addEventListener('visibilitychange', sync)
    const stop = onTick(() => {
      // hand-off: the loop dissolves into the scrubbed opening shot over the first third of the start chapter
      const o = frame.index <= 0 ? 1 - Math.min(1, Math.max(0, (frame.local - 0.05) / 0.3)) : 0
      const s = String(o)
      if (m.style.opacity === s) return
      const was = m.style.opacity
      m.style.opacity = s
      if ((was === '0') !== (s === '0')) sync()
    })
    return () => {
      io.disconnect()
      document.removeEventListener('visibilitychange', sync)
      stop()
    }
  }, [])

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
      {/* looping coastal shot (not scrubbed); reduced motion gets the poster only */}
      <div className="hero__media" ref={media}>
      <video
        ref={video}
        className="hero__video"
        src={env.reduced ? undefined : clipUrl('hero-loop', FILM_W)}
        poster={posterUrl('hero-loop')}
        autoPlay={!env.reduced}
        muted
        loop
        playsInline
        preload={env.reduced ? 'none' : 'auto'}
        disablePictureInPicture
        tabIndex={-1}
        aria-hidden="true"
      />
      </div>
      <div className="hero__copy">
        <h1 className="hero__title">
          {lead} <em>{last}</em>.
        </h1>
        <p className="hero__body">{start.body}</p>
        <div className="hero__exports">
          <h2 className="hero__exports-title mono">{exportsLine.title}</h2>
          <ul>
            {exportsLine.items.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <a className="hero__contact" href="/quote">
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
