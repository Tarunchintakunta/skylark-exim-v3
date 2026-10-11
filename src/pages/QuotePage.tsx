import { CONTACT } from '../config/content'
import RfqForm from '../sections/RfqForm'

/**
 * Office and email are the contact lines on skylarkexim.com.
 * That page does not state a response time, so this panel does not invent one.
 */
export function QuotePage() {
  return (
    <>
      <a className="skip-link mono" href="#quote-form">Skip to form</a>
      <main id="main" className="doc-main" tabIndex={-1}>
        <header className="section__head">
          <p className="eyebrow">Quote</p>
          <h1 id="quote-title" className="section__title">Request an export quote</h1>
        </header>
        <div className="quote-layout">
          <RfqForm />
          <aside className="quote-aside" aria-label="Office">
            <h2>Office</h2>
            <p>{CONTACT.office}</p>
            <h2>Email</h2>
            <p>
              <a href={`mailto:${CONTACT.email}`}>{CONTACT.email}</a>
            </p>
          </aside>
        </div>
      </main>
    </>
  )
}
