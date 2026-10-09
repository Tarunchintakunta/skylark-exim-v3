import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useRef, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { CONTACT } from '../config/content'
import { CATEGORIES, SHRIMP_FORMS, STATES } from '../config/products'
import { RFQ_TO, rfqSchema, rfqSubject, rfqSummary, type Rfq, type RfqInput } from '../config/rfq'
import { store } from '../engine/store'
import { bindReveals } from './reveal'

type Status = { kind: 'idle' } | { kind: 'sending' } | { kind: 'sent' } | { kind: 'mailto'; href: string } | { kind: 'error'; msg: string }

/** Request an export quote (STORY §15, TRD §12): validated form → api/rfq (Resend) or a pre-filled mailto. */
export function Quote() {
  const root = useRef<HTMLElement>(null)
  const [status, setStatus] = useState<Status>({ kind: 'idle' })
  const { register, handleSubmit, control, setValue, formState: { errors } } = useForm<RfqInput, unknown, Rfq>({
    resolver: zodResolver(rfqSchema),
    defaultValues: { category: store.getState().prefill.category ?? 'marine', species: [], forms: [], states: [] },
  })
  const category = useWatch({ control, name: 'category' })

  useEffect(() => bindReveals(root.current!), [])
  // pre-fill the category from what the visitor last looked at in Products
  useEffect(() => store.subscribe((s) => s.prefill.category && setValue('category', s.prefill.category)), [setValue])

  const onSubmit = async (r: Rfq) => {
    setStatus({ kind: 'sending' })
    const mailto = `mailto:${RFQ_TO}?subject=${encodeURIComponent(rfqSubject(r))}&body=${encodeURIComponent(rfqSummary(r))}`
    try {
      const res = await fetch('/api/rfq', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(r) })
      const body = await res.json().catch(() => ({}))
      if (body.ok) return setStatus({ kind: 'sent' })
      if (res.status === 429) return setStatus({ kind: 'error', msg: 'Too many requests. Please try again in a few minutes, or email us directly.' })
      if (!body.fallback) throw new Error('rfq failed')
    } catch {
      // API unreachable: still let the buyer send it from their own email app
    }
    setStatus({ kind: 'mailto', href: mailto })
    window.location.href = mailto
  }

  const field = (name: 'name' | 'company' | 'country' | 'email' | 'phone' | 'quantity' | 'destination', label: string, type = 'text', auto?: string) => (
    <label className={`field${errors[name] ? ' is-invalid' : ''}`}>
      <input type={type} placeholder=" " autoComplete={auto} aria-invalid={!!errors[name]} {...register(name)} />
      <span className="field__label">{label}</span>
      {errors[name] && <span className="field__error" role="alert">{errors[name]?.message}</span>}
    </label>
  )
  const checks = (name: 'species' | 'forms' | 'states', options: string[], legend: string) => (
    <fieldset className="checks">
      <legend className="mono">{legend}</legend>
      {options.map((o) => (
        <label key={o} className="check">
          <input type="checkbox" value={o} {...register(name)} />
          <span>{o}</span>
        </label>
      ))}
    </fieldset>
  )

  return (
    <section id="quote" className="section theme-light quote" ref={root} aria-labelledby="quote-title" tabIndex={-1}>
      <header className="section__head">
        <p className="eyebrow mono" data-reveal>Quote</p>
        <h2 id="quote-title" className="section__title" data-reveal>Request an export quote</h2>
      </header>
      <div className="quote__grid">
        {status.kind === 'sent' || status.kind === 'mailto' ? (
          <div className="rfq-done" role="status">
            <svg className="rfq-done__check" viewBox="0 0 52 52" aria-hidden="true"><circle cx="26" cy="26" r="24" /><path d="M15 27l7 7 15-16" /></svg>
            <h3 className="tile__title">{status.kind === 'sent' ? 'Thank you. Your request is with our team.' : 'Your email app should open with the request.'}</h3>
            {status.kind === 'mailto' && (
              <p>
                If it didn’t, <a href={status.href}>open the pre-filled email</a> or write to <a href={`mailto:${RFQ_TO}`}>{RFQ_TO}</a>.
              </p>
            )}
          </div>
        ) : (
          <form className="rfq" onSubmit={handleSubmit(onSubmit)} noValidate data-reveal>
            <div className="rfq__row">
              {field('name', 'Name', 'text', 'name')}
              {field('company', 'Company', 'text', 'organization')}
            </div>
            <div className="rfq__row">
              {field('country', 'Country', 'text', 'country-name')}
              {field('email', 'Email', 'email', 'email')}
            </div>
            <div className="rfq__row">
              {field('phone', 'Phone (optional)', 'tel', 'tel')}
              <label className="field field--select">
                <select {...register('category')}>
                  <option value="marine">{CATEGORIES.marine.label}</option>
                  <option value="shrimps">{CATEGORIES.shrimps.label}</option>
                </select>
                <span className="field__label">Product category</span>
              </label>
            </div>
            {checks('species', CATEGORIES[category === 'shrimps' ? 'shrimps' : 'marine'].species, 'Species')}
            {category === 'shrimps' && checks('forms', SHRIMP_FORMS.map((f) => f.name), 'Form')}
            {checks('states', STATES, 'Fresh / chilled / frozen')}
            <div className="rfq__row">
              {field('quantity', 'Quantity')}
              {field('destination', 'Destination market')}
            </div>
            <label className={`field field--area${errors.message ? ' is-invalid' : ''}`}>
              <textarea rows={4} placeholder=" " {...register('message')} />
              <span className="field__label">Message</span>
              {errors.message && <span className="field__error" role="alert">{errors.message.message}</span>}
            </label>
            <label className="hp" aria-hidden="true">
              Website <input tabIndex={-1} autoComplete="off" {...register('website')} />
            </label>
            {status.kind === 'error' && <p className="field__error" role="alert">{status.msg}</p>}
            <button className="btn btn--solid rfq__submit" type="submit" disabled={status.kind === 'sending'}>
              {status.kind === 'sending' ? 'Sending…' : 'Send request'}
            </button>
          </form>
        )}
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
