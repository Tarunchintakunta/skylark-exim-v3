import type { ChapterDef, Media } from '../config/chapters'
import { env } from '../engine/env'
import { MP4_V } from './manifest'

export interface Segment {
  media: Media
  chapter: number
  /** range inside the chapter's local progress */
  from: number
  to: number
  /** set on the last segment of a chapter */
  join?: ChapterDef['joinNext']
  scrim?: ChapterDef['scrim']
}

/**
 * A chapter's scroll length is split evenly across its media, unless a still sets its `span`.
 * Segments inside a chapter cross-fade (separate Higgsfield shots never share a boundary frame); the last one uses the chapter's join.
 */
export function toSegments(chapters: ChapterDef[]): Segment[] {
  return chapters.flatMap((ch, chapter) => {
    let from = 0
    return ch.media.map((media, j, all) => {
      const last = j === all.length - 1
      const to = last ? 1 : from + ((media.kind === 'still' && media.span) || 1 / all.length)
      const seg = { media, chapter, from, to, join: last ? ch.joinNext : ('crossfade' as const), scrim: ch.scrim }
      from = to
      return seg
    })
  })
}

/**
 * Media tier (redesign §2.6), chosen once at load: 960 on phones / Save-Data / 3G or slower, 1920 when the frame is wider than
 * 1600 device px, so the 1280 tier is never upscaled more than 1.25× (e.g. 1680 wide, or Retina above ~1067 css px, dpr capped at 1.5), else 1280.
 */
const dpr = Math.min(devicePixelRatio || 1, 1.5)
export const W = env.mobile || env.saveData || env.slow ? 960 : innerWidth * dpr > 1600 ? 1920 : 1280
/** stand-in stills (ph-*) only exist at 1280 / 720 */
const stillW = (w: number) => (w === 960 ? 720 : 1280)
/** versioned by content hash (#251): /media/*.mp4 is cached immutably, so a re-encoded clip needs a new URL */
export const clipUrl = (id: string, w = W) => {
  const v = MP4_V[`${id}_${w}`]
  return `/media/${id}_${w}.mp4${v ? `?v=${v}` : ''}`
}
/** Scrubbed film clips on phones load the 720 tier (lighter seek/decode on mid Android); posters stay at W. */
export const FILM_W = W === 960 ? 720 : W
export const posterUrl = (id: string, w = W) => `/media/${id}_${w}.webp`
const stillUrl = (id: string, w: number) => (id.startsWith('ph-') ? `/media/${id}_${stillW(w)}.webp` : posterUrl(id, w))
export const endPosterUrl = (id: string) => `/media/${id}_end_1920.webp`

/** First-frame poster for a segment, or null for gradient/globe. `w` is the media tier (tests pass each one). */
export function posterFor(m: Media, w = W): string | null {
  if (m.kind === 'video') return posterUrl(m.id, w)
  if (m.kind === 'still') return stillUrl(m.poster, w)
  // documentation: a pre-blurred, darkened still (no live CSS blur over the stage)
  if (m.kind === 'dom') return stillUrl(`${m.poster}-blur`, w)
  return null
}
