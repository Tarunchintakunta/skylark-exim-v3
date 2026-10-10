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

/**
 * Hero turntable slot (#130): photoreal clips `/media/<id>_{1920,1280,960}.mp4` + `.webp` posters from the Blender
 * pass. Flip `available` once the files are in public/media; until then the slot is a typographic composition.
 */
export const HERO: { id: string; name: string; category: Category; available: boolean }[] = [
  { id: 'prod-tuna', name: 'Tuna', category: 'marine', available: true },
  { id: 'prod-shrimp', name: 'Vannamei', category: 'shrimps', available: false },
]

export { STATES }
