import { DOC_CARDS, LABEL_FIELDS, start } from '../config/content'
import { setPath } from '../engine/path'
import { useApp } from '../engine/store'
import { MARKET_COORDS, MARKETS_BY_REGION } from '../config/markets'
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

/** World caption: every market as real text, grouped by region; hover/focus highlights that route on the globe (PRD F8), a click turns the globe to it. */
export function MarketList() {
  const set = (i: number) => () => void (globeUi.highlight = i)
  return (
    <div className="markets" aria-label="Markets" role="group">
      {MARKETS_BY_REGION.map(({ region, markets }) => (
        <div className="markets__group" key={region} data-fade>
          <h3 className="markets__region mono">{region}</h3>
          <ul className="markets__list">
            {markets.map((i) => (
              <li key={i}>
                <button type="button" className="markets__item" onMouseEnter={set(i)} onMouseLeave={set(-1)} onFocus={set(i)} onBlur={set(-1)} onClick={() => void (globeUi.focus = globeUi.highlight = i)}>
                  {MARKET_COORDS[i].name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

/** End of a path's own chapters (#219): one quiet link over to the other story, before the shared ending. */
export function OtherPath() {
  const other = useApp((s) => (s.path === 'ocean' ? 'pond' : 'ocean'))
  return (
    <p className="caption__other" data-fade>
      <a
        href={`#${other}`}
        data-other-path={other}
        onClick={(e) => {
          e.preventDefault()
          setPath(other, true)
        }}
      >
        {start.other}: {start[other].sub} →
      </a>
    </p>
  )
}
