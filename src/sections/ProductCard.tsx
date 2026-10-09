import type { Product } from '../config/products'

/** One product: category label, name in the display serif, the scientific name where the site gives one, and an Enquire button.
 * The states (raw fresh, chilled, frozen) are stated for the range as a whole, so they sit once in the section head, not per species. */
export function ProductCard({ product, label, index, onEnquire }: { product: Product; label: string; index: number; onEnquire: () => void }) {
  return (
    <li className="pcard" data-reveal>
      {product.image && <img className="pcard__img" src={product.image} alt="" loading="lazy" decoding="async" />}
      <p className="pcard__meta">
        <span className="pcard__no">{String(index + 1).padStart(2, '0')}</span>
        {label}
      </p>
      <h3 className="pcard__name display">{product.name}</h3>
      {product.latin && <p className="pcard__latin">{product.latin}</p>}
      <button type="button" className="pcard__cta" onClick={onEnquire} aria-label={`Enquire about ${product.name}`}>
        <u>Enquire</u> <span aria-hidden="true">→</span>
      </button>
    </li>
  )
}
