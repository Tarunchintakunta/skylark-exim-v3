/**
 * Loader gate (#218). The loader holds until everything the first screens need can play:
 * - the fonts, through `document.fonts.load()` (index.html preloads the files)
 * - the page, mounted (on /story: the story chunk)
 * - the hero loop, then the page's own first clips at `canplaythrough` (on /story: the first chapter's clip of the chosen
 *   path, #ocean / #pond, else wild catch; the other story loads nothing until the visitor switches, #219)
 * Progress is real: each part reports its share (a clip by how much of it is buffered) and the bar shows the mean.
 * Times are from navigation start: at least `min` ms so the intro finishes drawing, and never more than MAX_MS.
 */
const FACES = ['400 1em "Instrument Serif"', '400 1em "Inter Tight"', '500 1em "Inter Tight"']
export const MAX_MS = 3000

const at = (ms: number) => new Promise<void>((r) => setTimeout(r, Math.max(0, ms - performance.now())))

/** Resolves once the video can play through, or errors; a video with no source (reduced motion) counts as done. */
function playable(v: HTMLVideoElement | null, report: (f: number) => void) {
  return new Promise<void>((resolve) => {
    if (!v?.getAttribute('src')) return resolve()
    const done = () => {
      report(1)
      resolve()
    }
    if (v.readyState >= 4) return done()
    v.addEventListener('canplaythrough', done, { once: true })
    v.addEventListener('error', done, { once: true })
    // `progress` events are sparse under throttling and can come before the duration is known: sample instead
    const iv = setInterval(() => {
      const b = v.buffered
      if (b.length && v.duration) report(b.end(b.length - 1) / v.duration)
    }, 150)
    v.addEventListener('canplaythrough', () => clearInterval(iv), { once: true })
    v.addEventListener('error', () => clearInterval(iv), { once: true })
    setTimeout(() => clearInterval(iv), MAX_MS)
  })
}

/** What a page's loader waits for besides the fonts and the hero loop. */
export interface Gate {
  mounted: Promise<void>
  /** the page's first clips: how many (the bar's denominator), and a call that starts them once the hero loop is in */
  clips?: { n: number; start: () => (HTMLVideoElement | null)[] }
}

export function gate(onProgress: (f: number) => void, min: number, { mounted, clips = { n: 0, start: () => [] } }: Gate) {
  const shares = Array<number>(FACES.length + 2 + clips.n).fill(0)
  const part = (k: number) => (f: number) => {
    shares[k] = Math.max(shares[k], f)
    onProgress(shares.reduce((a, b) => a + b, 0) / shares.length)
  }
  const fonts = FACES.map((f, k) => document.fonts.load(f).catch(() => {}).then(() => part(k)(1)))
  const page = mounted.then(() => part(FACES.length)(1))
  // the hero loop first, then the chapter clip: on a slow line they would otherwise split the bandwidth
  const k0 = FACES.length + 1
  const hero = playable(document.querySelector<HTMLVideoElement>('.hero__video'), part(k0))
  const first = hero.then(() => Promise.all(clips.start().map((v, k) => playable(v, part(k0 + 1 + k)))))
  return Promise.race([Promise.all([...fonts, page, first, at(min)]), at(MAX_MS)])
}
