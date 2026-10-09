import { lazy, Suspense, useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { CATEGORIES, SHRIMP_FORMS, SPECIES_OFFERED, STATES, type Category } from '../config/products'
import { goTo } from '../engine/path'
import { store, useApp } from '../engine/store'
import { Fallback } from '../ui/Fallback'
import { ProductCard } from './ProductCard'
import { bindReveals } from './reveal'
import './sections.css'

const ProductStage = lazy(() => import('../three/ProductStage'))
const TABS: Category[] = ['marine', 'shrimps']

/** Products (STORY §12): tabs follow the chosen path, models (or DOM cards), species, shrimp forms, states. */
export function Products() {
  const path = useApp((s) => s.path)
  const [tab, setTab] = useState<Category>(path === 'pond' ? 'shrimps' : 'marine')
  const root = useRef<HTMLElement>(null)
  const tabs = useRef<(HTMLButtonElement | null)[]>([])

  useEffect(() => setTab(path === 'pond' ? 'shrimps' : 'marine'), [path])
  useEffect(() => store.setState({ prefill: { category: tab } }), [tab])
  useEffect(() => bindReveals(root.current!), [])

  const onKey = (e: KeyboardEvent) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
    const next = TABS[(TABS.indexOf(tab) + (e.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length]
    setTab(next)
    tabs.current[TABS.indexOf(next)]?.focus()
  }
  const cat = CATEGORIES[tab]
  const hasModels = cat.models.some((m) => m.glb)
  const cards = cat.models.map((m, i) => <ProductCard key={m.name} model={m} index={i} />)

  return (
    <section id="products" className="section theme-light" ref={root} aria-labelledby="products-title">
      <header className="section__head">
        <p className="eyebrow mono" data-reveal>Products</p>
        <h2 id="products-title" className="section__title" data-reveal>Our Products</h2>
      </header>

      <div className="tabs" role="tablist" aria-label="Product category" onKeyDown={onKey} data-reveal>
        {TABS.map((t, i) => (
          <button
            key={t}
            ref={(el) => void (tabs.current[i] = el)}
            role="tab"
            id={`tab-${t}`}
            aria-selected={tab === t}
            aria-controls={`panel-${t}`}
            tabIndex={tab === t ? 0 : -1}
            className="tab mono"
            onClick={() => setTab(t)}
          >
            {CATEGORIES[t].label}
          </button>
        ))}
      </div>

      <div className="products" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        <div className={`products__stage products__stage--${cat.models.length}`}>
          {hasModels ? (
            <Fallback fallback={cards}>
              <Suspense fallback={cards}>
                <ProductStage models={cat.models} />
              </Suspense>
            </Fallback>
          ) : (
            cards
          )}
        </div>
        <div className="products__info">
          <h3 className="products__sub mono" data-reveal>{cat.label}</h3>
          <ul className="species" data-reveal>
            {cat.species.map((s) => (
              <li key={s} className="species__item">{s}</li>
            ))}
          </ul>
          {tab === 'shrimps' && (
            <p className="products__note" data-reveal>
              <span className="mono">Species offered</span> {SPECIES_OFFERED}
            </p>
          )}
          <button className="btn products__cta" onClick={() => goTo('quote')} data-reveal>
            Request specifications
          </button>
        </div>
      </div>

      {tab === 'shrimps' && (
        <div className="forms">
          <h3 className="products__sub mono" data-reveal>Shrimp forms</h3>
          <ul className="forms__grid">
            {SHRIMP_FORMS.map((f) => (
              <li key={f.name} className="form-card" data-reveal>
                <span className="form-card__name">{f.name}</span>
                <span className="form-card__opt mono">{f.options}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <ul className="states" aria-label="Product states" data-reveal>
        {STATES.map((s) => (
          <li key={s} className="states__item display">{s}</li>
        ))}
      </ul>
    </section>
  )
}
