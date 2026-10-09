import type { ModelDef } from '../config/products'

/** DOM stand-in for a product model (CLAUDE_PROMPT §6) until the GLB exists. */
export function ProductCard({ model, index }: { model: ModelDef; index: number }) {
  return (
    <figure className="product-card" data-reveal>
      <span className="product-card__no mono">{String(index + 1).padStart(2, '0')}</span>
      <span className="product-card__ring" aria-hidden="true" />
      <figcaption className="product-card__name display">{model.name}</figcaption>
    </figure>
  )
}
