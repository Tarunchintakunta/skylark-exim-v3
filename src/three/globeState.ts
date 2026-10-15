import { PORTRAIT } from '../config/hero'
import { env } from '../engine/env'

/** Earth albedo: 2048×1024 on desktop, 1024×512 on phones (WebP, 114 / 33 KB); no other maps are used (#D). */
export const GLOBE_TEXTURE = env.mobile ? '/textures/earth_day_1024.webp' : '/textures/earth_day_2048.webp'

/**
 * The globe's placeholder (#D, #hd): its first frame of the world chapter, shown until the live globe draws. 16:9 at
 * 1280 / 1920 / 2560 for the desktop film, a 1440 px centre square for the round homepage globe and upright phones
 * (scripts/globe-placeholder.mjs).
 */
export const GLOBE_PH = (ext: 'avif' | 'webp') => ({
  sq: `/textures/globe-ph_sq.${ext}`,
  wide: [1280, 1920, 2560].map((w) => `/textures/globe-ph_${w}.${ext} ${w}w`).join(', '),
})
/** fetch the placeholder the film's <picture> will pick (GlobeLayer), ahead of time */
export function warmGlobePlaceholder(avif: boolean) {
  const ph = GLOBE_PH(avif ? 'avif' : 'webp')
  const img = new Image()
  if (matchMedia(PORTRAIT).matches) img.src = ph.sq
  else {
    img.sizes = '100vw'
    img.srcset = ph.wide
  }
  return img
}

/** Shared, mutable UI state between the DOM market list and the globe (no React renders). */
export const globeUi = {
  /** index into MARKET_COORDS of the hovered/focused market, or -1 */
  highlight: -1,
  /** index of the clicked market the globe turns to face, or -1 */
  focus: -1,
  /** true after the first drag: the "Drag to explore" hint stays hidden */
  explored: false,
}
