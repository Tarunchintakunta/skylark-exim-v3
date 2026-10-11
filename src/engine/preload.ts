import { posterUrl } from '../film/segments'

/**
 * Critical set for the loader (redesign §2.5, #134 LCP): the fonts and the hero loop's poster, nothing else.
 * - Fonts load through `document.fonts.load()` only (index.html preloads the two critical files).
 * - The poster is the first frame of the hero loop at this device's tier (also preloaded in index.html).
 * - The loop itself keeps downloading behind: the hero shows the poster until the video has painted, then plays.
 * Never blocks: resolves at MAX_MS whatever is still loading.
 */
const FACES = ['400 1em "Instrument Serif"', '400 1em "Inter Tight"', '500 1em "Inter Tight"']
const MAX_MS = 2500

export function preloadCritical(onProgress: (f: number) => void) {
  let done = 0
  const total = FACES.length + 1
  const tick = () => onProgress(++done / total)

  const fonts = FACES.map((f) => document.fonts.load(f).catch(() => {}).then(tick))
  const poster = new Promise<void>((resolve) => {
    const img = new Image()
    img.onload = img.onerror = () => resolve()
    img.src = posterUrl('hero-loop')
  }).then(tick)

  return Promise.race([Promise.all([...fonts, poster]), new Promise((r) => setTimeout(r, MAX_MS))])
}
