import { useEffect, useRef } from 'react'
import { CONTACT } from '../config/content'
import { goTo } from '../engine/path'
import { bindReveals } from './reveal'

/** Final call to action (redesign §6, #132): deep-sea band with the email set large, phones, both addresses, the profile PDF. */
export function Contact() {
  const root = useRef<HTMLElement>(null)
  useEffect(() => bindReveals(root.current!), [])
  return (
    <section id="contact" className="contact-band" ref={root} aria-labelledby="contact-title">
      <p className="eyebrow mono" data-reveal>Contact</p>
      <h2 id="contact-title" className="contact-band__title" data-reveal>
        Let’s talk <em>seafood</em>.
      </h2>
      <a className="contact-band__email" href={`mailto:${CONTACT.email}`} data-reveal>
        {CONTACT.email}
      </a>
      <div className="contact-band__grid">
        <div data-reveal>
          <h3 className="mono">Phone</h3>
          <ul>
            {CONTACT.phones.map((p) => (
              <li key={p.tel}>
                <a href={`tel:${p.tel}`}>{p.label}</a>
              </li>
            ))}
          </ul>
        </div>
        <div data-reveal>
          <h3 className="mono">Office</h3>
          <p>{CONTACT.office}</p>
        </div>
        <div data-reveal>
          <h3 className="mono">Processing unit</h3>
          <p>{CONTACT.unit}</p>
        </div>
        <div className="contact-band__actions" data-reveal>
          <a
            className="contact-band__cta"
            href="#quote"
            onClick={(e) => {
              e.preventDefault()
              goTo('quote')
            }}
          >
            Request export quote →
          </a>
          <a className="contact-band__pdf" href="/docs/skylark-exim-company-profile.pdf" download>
            Company profile (PDF)
          </a>
        </div>
      </div>
      <footer className="contact-band__foot mono">
        <span>© {new Date().getFullYear()} Skylark Exim</span>
        <span>Visakhapatnam, Andhra Pradesh</span>
      </footer>
    </section>
  )
}
