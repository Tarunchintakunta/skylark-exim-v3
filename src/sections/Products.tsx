import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'
import { useEffect, useRef, useState } from 'react'
import { CATEGORIES, HERO, SHRIMP_FORMS, SPECIES_OFFERED, STATES, type Category } from '../config/products'
import { env } from '../engine/env'
import { goTo } from '../engine/path'
import { store, useApp } from '../engine/store'
import { clipUrl, posterUrl } from '../film/segments'
import { ProductCard } from './ProductCard'
import { bindReveals } from './reveal'
import './sections.css'
import './products.css'

gsap.registerPlugin(SplitText)

const TABS: Category[] = ['marine', 'shrimps']
const LATIN = /(Litopenaeus vannamei|Penaeus monodon)/

/** [data-lines] headings rise out of a line mask once, as they enter. */
function bindLines(root: HTMLElement) {
  if (env.reduced) return () => {}
  const splits = [...root.querySelectorAll<HTMLElement>('[data-lines]')].map((el) =>
    SplitText.create(el, {
      type: 'lines', mask: 'lines', autoSplit: true,
      onSplit: (s) => gsap.from(s.lines, { yPercent: 105, duration: 0.9, stagger: 0.08, ease: 'power3.out', scrollTrigger: { trigger: el, start: 'top 88%', once: true } }),
    }),
  )
  return () => splits.forEach((s) => s.revert())
}

/** Photoreal turntable clip, playing (muted, looped) only while on screen; reduced motion keeps the poster. */
function Turntable({ id, name }: { id: string; name: string }) {
  const ref = useRef<HTMLVideoElement>(null)
  // poster and clip attach only when the section is about a screen away: a poster attribute downloads at boot even with
  // preload="none", which competed with the hero's LCP resources (#131)
  const [near, setNear] = useState(false)
  useEffect(() => {
    const v = ref.current!
    const nearIo = new IntersectionObserver(([e]) => e.isIntersecting && (setNear(true), nearIo.disconnect()), { rootMargin: '100% 0px' })
    nearIo.observe(v)
    if (env.reduced) return () => nearIo.disconnect()
    const io = new IntersectionObserver(([e]) => (e.isIntersecting ? v.play().catch(() => {}) : v.pause()))
    io.observe(v)
    return () => (nearIo.disconnect(), io.disconnect())
  }, [])
  return (
    <figure className="pr-hero__media">
      <video ref={ref} src={near && !env.reduced ? clipUrl(id) : undefined} poster={near ? posterUrl(id) : undefined} muted loop playsInline preload="none" aria-label={name} />
      <figcaption className="display">{name}</figcaption>
    </figure>
  )
}

/** Hero slot: turntables once the clips exist (HERO[].available), else a typographic composition of the same names. */
function ProductHero() {
  const live = HERO.filter((h) => h.available)
  if (live.length) return <div className="pr-hero pr-hero--media">{live.map((h) => <Turntable key={h.id} {...h} />)}</div>
  return (
    <div className="pr-hero" aria-hidden="true">
      {HERO.map((h, i) => (
        <p key={h.id} className={`pr-hero__word pr-hero__word--${i}`}>
          <span className="pr-hero__label">{CATEGORIES[h.category].label}</span>
          <span className="display" data-lines>{i ? <em>{h.name}</em> : h.name}</span>
        </p>
      ))}
    </div>
  )
}

/** Products (STORY §12): category follows the chosen path; every product card enquires straight into the RFQ. */
export function Products() {
  const path = useApp((s) => s.path)
  const [tab, setTab] = useState<Category>(path === 'pond' ? 'shrimps' : 'marine')
  const head = useRef<HTMLElement>(null)
  const body = useRef<HTMLDivElement>(null)

  useEffect(() => setTab(path === 'pond' ? 'shrimps' : 'marine'), [path])
  useEffect(() => store.setState({ prefill: { category: tab } }), [tab])
  useEffect(() => {
    const a = bindReveals(head.current!)
    const b = bindLines(head.current!)
    return () => (a(), b())
  }, [])
  useEffect(() => bindReveals(body.current!), [tab])

  const enquire = (category: Category, species: string) => {
    store.setState({ prefill: { category, species } })
    goTo('quote')
  }
  const cat = CATEGORIES[tab]

  return (
    <section id="products" className="section theme-light pr" aria-labelledby="products-title">
      <header className="pr-head" ref={head}>
        <div className="pr-head__copy">
          <p className="eyebrow mono" data-reveal>Products</p>
          <h2 id="products-title" className="pr-title" data-lines>
            Our <em>Products</em>
          </h2>
          <ul className="pr-states display" aria-label="Product states" data-reveal>
            {STATES.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
        <ProductHero />
      </header>

      <div className="pr-switch" role="group" aria-label="Product category">
        {TABS.map((t) => (
          <button key={t} type="button" className="pr-switch__btn" aria-pressed={tab === t} aria-controls="pr-panel" onClick={() => setTab(t)}>
            {CATEGORIES[t].label}
            <span className="pr-switch__count" aria-hidden="true">{String(CATEGORIES[t].products.length).padStart(2, '0')}</span>
          </button>
        ))}
      </div>

      <div id="pr-panel" className="pr-panel" ref={body}>
        <ul className={`pr-grid pr-grid--${cat.products.length}`} aria-label={cat.label}>
          {cat.products.map((p, i) => (
            <ProductCard key={p.name} product={p} label={cat.label} index={i} onEnquire={() => enquire(tab, p.name)} />
          ))}
        </ul>

        {tab === 'shrimps' && (
          <div className="pr-forms">
            <div className="pr-forms__lede" data-reveal>
              <h3 className="pr-forms__title display">Shrimp forms</h3>
              <p className="pr-forms__species">
                <span className="pr-label">Species offered</span>
                {SPECIES_OFFERED.split(LATIN).map((t, i) => (i % 2 ? <i key={i}>{t}</i> : t))}
              </p>
            </div>
            <dl className="pr-forms__index">
              {SHRIMP_FORMS.map((f, i) => (
                <div key={f.name} className="pr-forms__row" data-reveal>
                  <dt>
                    <span className="pr-forms__no">{String(i + 1).padStart(2, '0')}</span>
                    {f.name}
                  </dt>
                  <dd>{f.options}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </section>
  )
}
