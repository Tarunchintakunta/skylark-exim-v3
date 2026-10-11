import { PRODUCT_W, STATES, productSrc, type Product } from '../config/products'

const MOBILE = '(max-width: 819px)'
const PHONE_W = PRODUCT_W.slice(0, 2)
/** card width: swipe row on phones, 3 columns to 1099 px, 4 or 5 above */
const SIZES = `${MOBILE} 76vw, (max-width: 1099px) 30vw, 22vw`

/** One product: a 1:1 catalogue still, category label, name in the display serif, the scientific name where the site
 * gives one, the states it ships in, and an Enquire button. Phones only get the 480/640 stills; the first card loads eagerly. */
export function ProductCard({ product, label, index, onEnquire }: { product: Product; label: string; index: number; onEnquire: () => void }) {
  const first = index === 0
  return (
    <li className="pcard" data-reveal>
      <picture className="pcard__media">
        <source type="image/avif" media={MOBILE} srcSet={productSrc(product.image, 'avif', PHONE_W)} sizes="76vw" />
        <source type="image/webp" media={MOBILE} srcSet={productSrc(product.image, 'webp', PHONE_W)} sizes="76vw" />
        <source type="image/avif" srcSet={productSrc(product.image, 'avif')} sizes={SIZES} />
        <img
          className="pcard__img"
          src={`/media/${product.image}_640.webp`}
          srcSet={productSrc(product.image, 'webp')}
          sizes={SIZES}
          width={640}
          height={640}
          alt={`${product.name}, whole, on crushed ice`}
          loading={first ? 'eager' : 'lazy'}
          decoding="async"
        />
      </picture>
      <p className="pcard__meta">
        <span className="pcard__no">{String(index + 1).padStart(2, '0')}</span>
        {label}
      </p>
      <h3 className="pcard__name display">{product.name}</h3>
      {product.latin && <p className="pcard__latin">{product.latin}</p>}
      <ul className="pcard__tags" aria-label="Available as">
        {STATES.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
      <button type="button" className="pcard__cta" onClick={onEnquire} aria-label={`Enquire about ${product.name}`}>
        <u>Enquire</u> <span aria-hidden="true">→</span>
      </button>
    </li>
  )
}
