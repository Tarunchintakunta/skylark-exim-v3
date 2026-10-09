import { useEffect, useRef, useState } from 'react'
import { start } from '../config/content'
import { NAV } from '../config/nav'
import { goTo } from '../engine/path'
import { frame } from '../engine/store'
import { onTick } from '../engine/ticker'
import { film } from '../film/controller'
import { Mark } from './Mark'
import './chrome.css'

/** Top bar: wordmark and section nav. Switches to dark-on-light over the globe and business sections. */
export function Header() {
  const root = useRef<HTMLElement>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let light = false
    return onTick(() => {
      const l = frame.past || film.chapters[frame.index]?.id === 'world'
      if (l !== light) {
        light = l
        root.current!.classList.toggle('is-light', l)
      }
    })
  }, [])

  const go = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    setOpen(false)
    goTo(id)
  }

  return (
    <header className="topbar" ref={root}>
      <a className="brand" href="#story" onClick={go('story')} aria-label="Skylark Exim, back to the start">
        <span className="brand__mark" data-brand-mark>
          <Mark />
        </span>
        <span className="brand__word mono">Skylark Exim</span>
      </a>
      <button className="menu-btn mono" aria-expanded={open} aria-controls="site-nav" onClick={() => setOpen((o) => !o)}>
        {open ? 'Close' : 'Menu'}
      </button>
      <nav id="site-nav" className={`nav${open ? ' is-open' : ''}`} aria-label="Sections">
        <ul>
          {NAV.map((n) => (
            <li key={n.id}>
              <a className="nav__link mono" href={`#${n.id}`} onClick={go(n.id)}>
                {n.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <span className="sr-only">{start.eyebrow}</span>
    </header>
  )
}
