import { MARINE_FISH, SHRIMPS, STATES } from './content'

// docs/CONTENT.md "Products". No sizes, counts, MOQ or prices anywhere.
export type Category = 'marine' | 'shrimps'

export interface Product {
  name: string
  /** scientific name, only where CONTENT.md gives one ("Species offered") */
  latin?: string
  /** optional photo (approved source only, never stock); none = typographic card */
  image?: string
}

const LATIN: Record<string, string> = { Vannamei: 'Litopenaeus vannamei', 'Black Tiger Shrimp': 'Penaeus monodon' }

export const CATEGORIES: Record<Category, { label: string; products: Product[] }> = {
  marine: { label: 'Marine fish', products: MARINE_FISH.map((name) => ({ name })) },
  shrimps: { label: 'Shrimps', products: SHRIMPS.map((name) => ({ name, latin: LATIN[name] })) },
}

export const SPECIES_OFFERED = 'Litopenaeus vannamei (Vannamei) & Penaeus monodon (Black Tiger)'

/** Full names only (confirm-list #11 fallback: no HOSO/HLSO/PUD abbreviations). */
export const SHRIMP_FORMS: { name: string; options: string }[] = [
  { name: 'Head-on Shell-on', options: 'Vannamei / Black Tiger' },
  { name: 'Headless Shell-on', options: 'Vannamei / Black Tiger' },
  { name: 'Peeled Undeveined', options: 'Vannamei' },
  { name: 'Peeled & Deveined', options: 'Tail on / Tail off' },
  { name: 'Pin Deveined', options: 'Tail on / Tail off' },
  { name: 'Easy Peel', options: 'Vannamei / Black Tiger' },
]

export { STATES }
