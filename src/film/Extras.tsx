import { DOC_CARDS, LABEL_FIELDS } from '../config/content'
import { MARKET_COORDS } from '../config/markets'
import { globeUi } from '../three/globeState'

/** Packing caption: a carton label that types in its field names. Field names only, never values (STORY §7). */
export function LabelCard() {
  return (
    <div className="label-card" data-fade aria-label="Carton label fields">
      <p className="label-card__head mono">Skylark Exim · Export carton</p>
      <dl>
        {LABEL_FIELDS.map((f) => (
          <div className="label-card__row" key={f}>
            <dt className="mono" data-type>
              {f}
            </dt>
            <dd aria-hidden="true" />
          </div>
        ))}
      </dl>
    </div>
  )
}

/** Documentation interlude: three paper cards labelled by function only, no document contents (STORY §8). */
export function DocCards() {
  return (
    <ul className="doc-cards" aria-label="Export paperwork">
      {DOC_CARDS.map((c, i) => (
        <li className="doc-card" key={c} data-card style={{ ['--i' as string]: i }}>
          <span className="doc-card__no mono">{String(i + 1).padStart(2, '0')}</span>
          <span className="doc-card__title mono">{c}</span>
          <span className="doc-card__lines" aria-hidden="true">
            <i /><i /><i /><i />
          </span>
        </li>
      ))}
    </ul>
  )
}

/** World caption: the 16 markets as real text; hover/focus highlights that route on the globe (PRD F8). */
export function MarketList() {
  const set = (i: number) => () => void (globeUi.highlight = i)
  return (
    <ul className="markets" aria-label="Markets">
      {MARKET_COORDS.map((m, i) => (
        <li key={m.name} data-fade>
          <button type="button" className="markets__item mono" onMouseEnter={set(i)} onMouseLeave={set(-1)} onFocus={set(i)} onBlur={set(-1)}>
            {m.name}
          </button>
        </li>
      ))}
    </ul>
  )
}
