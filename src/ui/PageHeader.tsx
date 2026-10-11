import { useState } from 'react'
import { start } from '../config/content'
import { NAV } from '../config/nav'
import { Mark } from './Mark'

const PATHS = ['ocean', 'pond'] as const

/** Header for /quote and /news. Same bar as the film, always on sand, with no film engine. */
export function PageHeader({ current }: { current: 'quote' | 'news' }) {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)

  return (
    <header className="topbar is-light is-page">
      <a className="brand" href="/#story" aria-label="Skylark Exim, back to the story">
        <span className="brand__mark">
          <Mark />
        </span>
        <span className="brand__word">Skylark Exim</span>
      </a>
      <p className="path-toggle" role="group" aria-label="Story path">
        {PATHS.map((path, i) => (
          <span key={path}>
            {i > 0 && <span aria-hidden="true"> · </span>}
            <a href={`/#${path}`}>{start[path].sub}</a>
          </span>
        ))}
      </p>
      <button className="menu-btn" aria-expanded={open} aria-controls="site-nav" onClick={() => setOpen((value) => !value)}>
        {open ? 'Close' : 'Menu'}
      </button>
      <nav id="site-nav" className={`nav${open ? ' is-open' : ''}`} aria-label="Sections">
        <ul>
          {NAV.map((item) => (
            <li key={item.id}>
              <a
                className="nav__link"
                href={item.href}
                aria-current={item.id === current ? 'page' : undefined}
                onClick={close}
              >
                {item.label}
              </a>
            </li>
          ))}
          <li className="nav__quote">
            <a className="nav__link" href="/quote" aria-current={current === 'quote' ? 'page' : undefined} onClick={close}>
              {start.cta} →
            </a>
          </li>
        </ul>
      </nav>
      <a className="quote-cta" href="/quote" aria-current={current === 'quote' ? 'page' : undefined}>
        {start.cta} →
      </a>
    </header>
  )
}
