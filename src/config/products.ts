import { MARINE_FISH, SHRIMPS, STATES } from './content'

// docs/CONTENT.md "Products". No sizes, counts, MOQ or prices anywhere.
export type Category = 'marine' | 'shrimps'

export interface ModelDef {
  name: string
  /** set to the file name in public/models once the optimised GLB exists (#33); until then a DOM card is shown */
  glb?: string
}

export const CATEGORIES: Record<Category, { label: string; species: string[]; models: ModelDef[] }> = {
  marine: { label: 'Marine Fish', species: MARINE_FISH, models: [{ name: 'Tuna' }, { name: 'Swordfish' }] },
  shrimps: { label: 'Shrimps', species: SHRIMPS, models: [{ name: 'Shrimp' }] },
}

export const SPECIES_OFFERED = 'Litopenaeus vannamei (Vannamei) & Penaeus monodon (Black Tiger)'

/** Full names as on the site (confirm-list #11 fallback: no HOSO/HLSO abbreviations). */
export const SHRIMP_FORMS: { name: string; options: string }[] = [
  { name: 'Head-on Shell-on', options: 'Vannamei / Black Tiger' },
  { name: 'Headless Shell-on', options: 'Vannamei / Black Tiger' },
  { name: 'PUD', options: 'Vannamei' },
  { name: 'Peeled & Deveined', options: 'Tail on / Tail off' },
  { name: 'Pin Deveined', options: 'Tail on / Tail off' },
  { name: 'Easy Peel', options: 'Vannamei / Black Tiger' },
]

export { STATES }
