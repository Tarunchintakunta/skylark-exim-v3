import { film, MARINE_FISH, SHRIMPS, start, STATES } from '../config/content'
import './type.css'

/**
 * /type (#88): the three type pairings from the redesign prompt §4, each on the hero, one story chapter and the
 * Products header, plus the proposed palette. Only on dev and preview builds. Copy comes from config/content.ts.
 */
const PAIRS = {
  a: { name: 'A · Editorial', fonts: 'Instrument Serif + Inter Tight', licence: 'both SIL OFL (Google Fonts)' },
  b: { name: 'B · Warm, crafted', fonts: 'Fraunces (opsz 144, 300–400) + General Sans', licence: 'OFL + Fontshare ITF Free Font Licence' },
  c: { name: 'C · Modern grotesk', fonts: 'Satoshi 500 + Inter', licence: 'Fontshare ITF FFL + OFL' },
} as const
type Pair = keyof typeof PAIRS

const cold = film.coldchain[3]

export default function TypePreview() {
  const q = new URLSearchParams(location.search).get('p')
  const pair: Pair = q === 'b' || q === 'c' ? q : 'a'
  const [lead, last] = [start.title.replace(/ world\.$/, ''), 'world']
  return (
    <div className="tp" data-pair={pair}>
      <div className="tp-bar">
        <b>Type preview</b>
        {(Object.keys(PAIRS) as Pair[]).map((k) => (
          <a key={k} href={`/type?p=${k}`} aria-current={k === pair ? 'page' : undefined}>
            {PAIRS[k].name}
          </a>
        ))}
        <span>
          {PAIRS[pair].fonts} · {PAIRS[pair].licence}
        </span>
      </div>

      <section className="tp-frame" aria-label="Hero">
        <img src="/media/opening_1280.webp" alt="" />
        <header className="tp-head">
          <span>Skylark Exim</span>
          <span className="tp-head__toggle">
            <u>{start.ocean.sub}</u> · {start.pond.sub}
          </span>
          <nav>
            <span>Story</span>
            <span>Products</span>
            <span>About</span>
            <span>Quote</span>
          </nav>
        </header>
        <div className="tp-frame__copy">
          <h1 className="tp-hero">
            {lead} <em>{last}</em>.
          </h1>
          <p className="tp-lead">{start.body}</p>
          <a className="tp-path" href="#pond">
            Or follow the {start.pond.sub.toLowerCase()} →
          </a>
        </div>
        <span className="tp-scroll">Scroll</span>
      </section>

      <section className="tp-frame tp-chapter" aria-label="Story chapter">
        <img src="/media/ph-p-freeze_1280.webp" alt="" />
        <div className="tp-frame__copy">
          <p className="tp-small">
            <span className="num">07</span>Cold storage
          </p>
          <h2 className="tp-h1">{cold.title}</h2>
          <p className="tp-body">{cold.body}</p>
        </div>
      </section>

      <section className="tp-products" aria-label="Products header">
        <div className="tp-products__head">
          <div>
            <p className="tp-small">Products</p>
            <h2 className="tp-h1">
              Our <em>Products</em>
            </h2>
          </div>
          <p className="tp-lead" style={{ color: 'var(--ink-2)' }}>
            {start.body}
          </p>
        </div>
        <p className="tp-states">
          {STATES.map((s, i) => (
            <span key={s}>
              {i > 0 && <span className="tp-dot"> · </span>}
              {s}
            </span>
          ))}
        </p>
        <ul className="tp-index">
          {MARINE_FISH.slice(0, 4).map((f) => (
            <li key={f}>
              {f} <small>Marine fish</small>
            </li>
          ))}
          {SHRIMPS.slice(0, 4).map((f) => (
            <li key={f}>
              {f} <small>Shrimp</small>
            </li>
          ))}
        </ul>
        <div className="tp-numbers">
          <div>
            <strong>700</strong>
            <span>pallets of cold storage</span>
          </div>
          <div>
            <strong>16</strong>
            <span>markets</span>
          </div>
          <div>
            <strong>−18&nbsp;°C</strong>
            <span>to −20&nbsp;°C in cold storage</span>
          </div>
        </div>
      </section>

      <div className="tp-palette" aria-label="Proposed palette">
        <div><i style={{ background: 'var(--sand)' }} />Sand #F4EFE6</div>
        <div><i style={{ background: 'var(--sand-2)' }} />Sand 2 #E9E1D3</div>
        <div><i style={{ background: 'var(--sea)' }} />Deep sea #0B2A33</div>
        <div><i style={{ background: 'var(--sea-2)' }} />Sea 2 #123C48</div>
        <div><i style={{ background: 'var(--accent)' }} />Accent on sand #B4532A (5.0:1)</div>
        <div><i style={{ background: 'var(--accent-on-sea)' }} />Accent on sea #E08A5F (5.6:1)</div>
      </div>
    </div>
  )
}
