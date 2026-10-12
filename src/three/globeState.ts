import { env } from '../engine/env'

/** Earth albedo: 2048×1024 on desktop, 1024×512 on phones (WebP, 114 / 33 KB); no other maps are used (#D). */
export const GLOBE_TEXTURE = env.mobile ? '/textures/earth_day_1024.webp' : '/textures/earth_day_2048.webp'

/** Shared, mutable UI state between the DOM market list and the globe (no React renders). */
export const globeUi = {
  /** index into MARKET_COORDS of the hovered/focused market, or -1 */
  highlight: -1,
  /** index of the clicked market the globe turns to face, or -1 */
  focus: -1,
  /** true after the first drag: the "Drag to explore" hint stays hidden */
  explored: false,
}
