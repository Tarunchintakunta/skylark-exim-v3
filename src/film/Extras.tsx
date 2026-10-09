import { LABEL_FIELDS } from '../config/content'

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
