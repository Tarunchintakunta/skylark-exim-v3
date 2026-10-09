import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { CONTACT } from '../config/content'
import { bindReveals } from './reveal'

const RfqForm = lazy(() => import('./RfqForm'))

/** Request an export quote. The form (zod + react-hook-form) loads once the section is within ~2 screens. */
export function Quote() {
  const root = useRef<HTMLElement>(null)
  const [near, setNear] = useState(false)

  useEffect(() => bindReveals(root.current!), [])
  useEffect(() => {
    const io = new IntersectionObserver((e) => e.some((x) => x.isIntersecting) && setNear(true), { rootMargin: '200% 0px' })
    io.observe(root.current!)
    return () => io.disconnect()
  }, [])

  return (
    <section id="quote" className="section theme-light quote" ref={root} aria-labelledby="quote-title" tabIndex={-1}>
      <header className="section__head">
        <p className="eyebrow mono" data-reveal>Quote</p>
        <h2 id="quote-title" className="section__title" data-reveal>Request an export quote</h2>
      </header>
      <div className="quote__grid">
        <Suspense fallback={<div className="rfq rfq--loading" />}>{near ? <RfqForm /> : <div className="rfq rfq--loading" />}</Suspense>
        <aside className="contact" aria-label="Contact" data-reveal>
          <h3 className="products__sub mono">Contact</h3>
          <ul className="contact__list">
            {CONTACT.phones.map((p) => (
              <li key={p.tel}><a href={`tel:${p.tel}`}>{p.label}</a></li>
            ))}
            <li><a href={`mailto:${CONTACT.email}`}>{CONTACT.email}</a></li>
          </ul>
          <h4 className="mono">Office</h4>
          <p>{CONTACT.office}</p>
          <h4 className="mono">Processing unit</h4>
          <p>{CONTACT.unit}</p>
          <a className="btn contact__pdf" href="/docs/skylark-exim-company-profile.pdf" download>
            Download company profile (PDF)
          </a>
        </aside>
      </div>
    </section>
  )
}
