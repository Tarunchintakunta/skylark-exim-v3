import { useEffect, useRef, useState } from 'react'
import { start } from '../config/content'
import { NAV } from '../config/nav'
import { goTo, setPath } from '../engine/path'
import { frame, useApp, type Path } from '../engine/store'
import { onTick } from '../engine/ticker'
import { film } from '../film/controller'
import { Mark } from './Mark'
import './chrome.css'

const PATHS: Path[] = ['ocean', 'pond']
const STORY = NAV.find((item) => item.id === 'story')!

/**
 * Top bar (redesign §3): mark + wordmark left; the Wild catch · Farmed shrimp text toggle; four links right.
 * "Request export quote →" appears as a quiet text button from the plant chapters on, and as a bottom bar on
 * mobile only once the business sections are on screen. Dark-on-light over the globe and business sections.
 */
export function Header() {
  const root = useRef<HTMLElement>(null)
  const [open, setOpen] = useState(false)
  const path = useApp((s) => s.path)

  useEffect(() => {
    let light = false
    let cta = false
    let bar = false
    let section = ''
    return onTick(() => {
      const id = film.chapters[frame.index]?.id
      const l = frame.past || id === 'world'
      if (l !== light) root.current!.classList.toggle('is-light', (light = l))
      // the plant onward: intake is the first shared chapter after the fork
      const plant = frame.past || film.chapters.findIndex((c) => c.id === 'intake') <= frame.index
      if (plant !== cta) root.current!.classList.toggle('has-cta', (cta = plant))
      if (frame.past !== bar) root.current!.classList.toggle('has-bar', (bar = frame.past))
      let next = 'story'
      for (const name of ['products', 'about', 'contact']) {
        const el = document.getElementById(name)
        if (el && el.getBoundingClientRect().top <= 96) next = name
      }
      if (next !== section && root.current) {
        section = next
        root.current.querySelectorAll<HTMLAnchorElement>('[data-nav]').forEach((link) => {
          if (link.dataset.nav === next) link.setAttribute('aria-current', 'true')
          else link.removeAttribute('aria-current')
        })
      }
    })
  }, [])

  const go = (item: (typeof NAV)[number]) => (e: React.MouseEvent) => {
    setOpen(false)
    if (!item.href.startsWith('/#')) return
    e.preventDefault()
    history.replaceState(null, '', item.href)
    goTo(item.id)
  }

  return (
    <header className="topbar" ref={root}>
      <a className="brand" href="/#story" onClick={go(STORY)} aria-label="Skylark Exim, back to the start">
        <span className="brand__mark" data-brand-mark>
          <Mark />
        </span>
        <span className="brand__word">Skylark Exim</span>
      </a>
      <p className="path-toggle" role="group" aria-label="Story path">
        {PATHS.map((p, i) => (
          <span key={p}>
            {i > 0 && <span aria-hidden="true"> · </span>}
            <a
              href={`#${p}`}
              aria-current={path === p ? 'true' : undefined}
              onClick={(e) => {
                e.preventDefault()
                // inside the film: land on the other path's first chapter; on the hero: just switch
                setPath(p, frame.index > 0 && !frame.past)
              }}
            >
              {start[p].sub}
            </a>
          </span>
        ))}
      </p>
      <button className="menu-btn" aria-expanded={open} aria-controls="site-nav" onClick={() => setOpen((o) => !o)}>
        {open ? 'Close' : 'Menu'}
      </button>
      <nav id="site-nav" className={`nav${open ? ' is-open' : ''}`} aria-label="Sections">
        <ul>
          {NAV.map((n) => (
            <li key={n.id}>
              <a className="nav__link" data-nav={n.id} href={n.href} onClick={go(n)}>
                {n.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <a className="quote-cta" href="/quote">
        {start.cta} →
      </a>
    </header>
  )
}
