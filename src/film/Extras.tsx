import { DOC_CARDS, LABEL_FIELDS } from '../config/content'
import { MARKET_COORDS } from '../config/markets'
import { globeUi } from '../three/globeState'

/** Packing caption: the carton label's field names as a quiet hairline list. Field names only, never values (STORY §7). */
export function LabelCard() {
  return (
    <dl className="caption__fields" data-fade aria-label="Carton label fields">
      {LABEL_FIELDS.map((f) => (
        <div key={f}>
          <dt data-type>{f}</dt>
          <dd aria-hidden="true" />
        </div>
      ))}
    </dl>
  )
}

/** Documentation interlude: what the paperwork covers, as text (no paper-card boxes). */
export function DocCards() {
  return (
    <ul className="caption__fields" aria-label="Export paperwork">
      {DOC_CARDS.map((c) => (
        <li key={c} data-fade>
          {c}
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
          <button type="button" className="markets__item" onMouseEnter={set(i)} onMouseLeave={set(-1)} onFocus={set(i)} onBlur={set(-1)}>
            {m.name}
          </button>
        </li>
      ))}
    </ul>
  )
}
