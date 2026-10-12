import { chaptersFor } from '../config/chapters'
import { warm } from '../film/scrub'
import { storyReady } from './boot'

/**
 * Loader gate (#218). The loader holds until everything the first screens need can play:
 * - the fonts, through `document.fonts.load()` (index.html preloads the files)
 * - the story chunk, mounted
 * - the hero loop, and the first chapter's clip on each path (wild catch and farmed), at `canplaythrough`
 * Progress is real: each part reports its share (a clip by how much of it is buffered) and the bar shows the mean.
 * Times are from navigation start: at least `min` ms so the intro finishes drawing, and never more than MAX_MS.
 */
const FACES = ['400 1em "Instrument Serif"', '400 1em "Inter Tight"', '500 1em "Inter Tight"']
export const MAX_MS = 3000

/** first clip after the shared start chapter, per path */
const FIRST = (['ocean', 'pond'] as const).flatMap((p) => {
  const m = chaptersFor(p).slice(1).flatMap((ch) => ch.media).find((m) => m.kind === 'video')
  return m?.kind === 'video' ? [m.id] : []
})

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
    v.addEventListener('progress', () => {
      const b = v.buffered
      if (b.length && v.duration) report(b.end(b.length - 1) / v.duration)
    })
  })
}

export function gate(onProgress: (f: number) => void, min: number) {
  const videos = [document.querySelector<HTMLVideoElement>('.hero__video'), ...warm(FIRST)]
  const shares = Array<number>(FACES.length + 1 + videos.length).fill(0)
  const part = (k: number) => (f: number) => {
    shares[k] = Math.max(shares[k], f)
    onProgress(shares.reduce((a, b) => a + b, 0) / shares.length)
  }
  const fonts = FACES.map((f, k) => document.fonts.load(f).catch(() => {}).then(() => part(k)(1)))
  const story = storyReady.then(() => part(FACES.length)(1))
  const clips = videos.map((v, k) => playable(v, part(FACES.length + 1 + k)))
  return Promise.race([Promise.all([...fonts, story, ...clips, at(min)]), at(MAX_MS)])
}
