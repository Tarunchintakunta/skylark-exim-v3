import { useEffect, useRef } from 'react'
import { TRUST } from '../config/content'
import { bindReveals } from './reveal'

/** Why choose us (STORY §13): six tiles, the compliance line exactly as the site states it, a facts row. No badges. */
export function Trust() {
  const root = useRef<HTMLElement>(null)
  useEffect(() => bindReveals(root.current!), [])
  return (
    <section id="why" className="section theme-light" ref={root} aria-labelledby="why-title">
      <header className="section__head">
        <p className="eyebrow mono" data-reveal>Why us</p>
        <h2 id="why-title" className="section__title" data-reveal>{TRUST.title}</h2>
      </header>
      <ul className="facts" aria-label="Facts">
        {TRUST.facts.map((f) => (
          <li key={f.label} className="fact" data-reveal>
            <span className="fact__value display">{f.value}</span>
            <span className="fact__label mono">{f.label}</span>
          </li>
        ))}
      </ul>
      <ul className="tiles">
        {TRUST.tiles.map((t, i) => (
          <li key={t.title} className="tile" data-reveal>
            <span className="tile__no mono">{String(i + 1).padStart(2, '0')}</span>
            <h3 className="tile__title">{t.title}</h3>
            <p className="tile__line">{t.line}</p>
          </li>
        ))}
      </ul>
      <p className="compliance" data-reveal>
        <span className="mono">Certificates</span>
        {TRUST.compliance}
      </p>
    </section>
  )
}
