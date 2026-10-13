import type { MouseEvent } from 'react'
import { start } from '../config/content'
import { NAV, type Route } from '../config/nav'

/** The link list shared by every header: the current route is marked, "Our Story" opens its two paths. */
export function SiteNav({ open, current, onNavigate }: { open: boolean; current: Route; onNavigate: (e: MouseEvent<HTMLAnchorElement>) => void }) {
  return (
    <nav id="site-nav" className={`nav${open ? ' is-open' : ''}`} aria-label="Site">
      <ul>
        {NAV.map((item) => (
          <li key={item.id} className={item.sub ? 'nav__group' : undefined}>
            <a className="nav__link" data-nav={item.id} href={item.href} aria-current={item.id === current ? 'page' : undefined} onClick={onNavigate}>
              {item.label}
            </a>
            {item.sub && (
              <ul className="nav__sub" aria-label={item.label}>
                {item.sub.map((s) => (
                  <li key={s.href}>
                    <a className="nav__link" href={s.href} onClick={onNavigate}>
                      {s.label}
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
        <li className="nav__quote">
          <a className="nav__link" href="/quote" aria-current={current === 'quote' ? 'page' : undefined} onClick={onNavigate}>
            {start.cta} →
          </a>
        </li>
      </ul>
    </nav>
  )
}
