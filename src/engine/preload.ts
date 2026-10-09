/**
 * Critical set for the loader (redesign §2.5): fonts and the head of the opening clip, nothing else.
 * - Fonts load through `document.fonts.load()` only (the <link rel=preload> in index.html already fetches them).
 * - The opening clip is the stage's own <video> (the scrub engine sets its src on the first tick), so it downloads once.
 *   Progress is the buffered share of the first HEAD_S seconds.
 * Never blocks: resolves at MAX_MS whatever is still loading.
 */
const FACES = ['400 1em "Instrument Serif"', '400 1em "Inter Tight"', '500 1em "Inter Tight"']
const HEAD_S = 2.5
const MAX_MS = 2500

export function preloadCritical(onProgress: (f: number) => void) {
  let fontsDone = 0
  let clip = 0
  const report = () => onProgress(Math.min(1, 0.15 * (fontsDone / FACES.length) + 0.85 * clip))

  const fonts = Promise.all(
    FACES.map((f) =>
      document.fonts
        .load(f)
        .catch(() => {})
        .then(() => {
          fontsDone++
          report()
        }),
    ),
  )

  const video = new Promise<void>((done) => {
    const find = () => [...document.querySelectorAll<HTMLVideoElement>('.stage__video')].find((v) => v.currentSrc.includes('/opening_'))
    const watch = (v: HTMLVideoElement) => {
      const update = () => {
        const b = v.buffered
        const end = b.length ? b.end(0) : 0
        const head = Math.min(HEAD_S, Number.isFinite(v.duration) ? v.duration : HEAD_S)
        clip = Math.max(clip, Math.min(1, end / head))
        report()
        if (clip >= 1 || v.readyState >= 4) {
          clip = 1
          report()
          v.removeEventListener('progress', update)
          v.removeEventListener('canplaythrough', update)
          done()
        }
      }
      v.addEventListener('progress', update)
      v.addEventListener('canplaythrough', update)
      v.addEventListener('error', () => done(), { once: true })
      update()
    }
    const poll = () => {
      const v = find()
      if (v) watch(v)
      else requestAnimationFrame(poll)
    }
    poll()
  })

  return Promise.race([Promise.all([fonts, video]), new Promise((r) => setTimeout(r, MAX_MS))])
}
