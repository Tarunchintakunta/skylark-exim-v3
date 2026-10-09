import { useEffect, useRef } from 'react'
import { ABOUT } from '../config/content'
import { bindReveals } from './reveal'

/** About (STORY §14): company, vision, mission, managing partners (initials until photos are supplied, confirm-list #9). */
export function About() {
  const root = useRef<HTMLElement>(null)
  useEffect(() => bindReveals(root.current!), [])
  return (
    <section id="about" className="section theme-light about" ref={root} aria-labelledby="about-title">
      <header className="section__head">
        <p className="eyebrow mono" data-reveal>About</p>
        <h2 id="about-title" className="section__title" data-reveal>{ABOUT.title}</h2>
      </header>
      <div className="about__grid">
        <div className="about__company">
          {ABOUT.company.map((p, i) => (
            <p key={i} className={i === 0 ? 'about__lead' : undefined} data-reveal>
              {p}
            </p>
          ))}
        </div>
        <div className="about__vm">
          <article data-reveal>
            <h3 className="mono">Vision</h3>
            <p>{ABOUT.vision}</p>
          </article>
          <article data-reveal>
            <h3 className="mono">Mission</h3>
            <p>{ABOUT.mission}</p>
          </article>
        </div>
      </div>
      <div className="partners">
        <h3 className="products__sub mono" data-reveal>Managing partners</h3>
        <ul className="partners__list">
          {ABOUT.partners.map((p) => (
            <li key={p.name} className="partner" data-reveal>
              <span className="partner__mono display" aria-hidden="true">{p.initials}</span>
              <span className="partner__name">{p.name}</span>
              <span className="partner__role mono">Managing partner</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
