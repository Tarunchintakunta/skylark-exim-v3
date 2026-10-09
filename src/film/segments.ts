import type { ChapterDef, Media } from '../config/chapters'
import { env } from '../engine/env'

export interface Segment {
  media: Media
  chapter: number
  /** range inside the chapter's local progress */
  from: number
  to: number
  /** set on the last segment of a chapter */
  join?: ChapterDef['joinNext']
}

/** A chapter's scroll length is split evenly across its media (o1 = a1 then a2), unless a still sets its `span`. */
export function toSegments(chapters: ChapterDef[]): Segment[] {
  return chapters.flatMap((ch, chapter) => {
    let from = 0
    return ch.media.map((media, j, all) => {
      const last = j === all.length - 1
      const to = last ? 1 : from + ((media.kind === 'still' && media.span) || 1 / all.length)
      const seg = { media, chapter, from, to, join: last ? ch.joinNext : undefined }
      from = to
      return seg
    })
  })
}

/**
 * Media tier (redesign §2.6), chosen once at load: 960 on phones / Save-Data, 1920 when the frame is wider than
 * 1280 device px (e.g. 1440 wide, or Retina above ~860 css px, dpr capped at 1.5), else 1280.
 */
const dpr = Math.min(devicePixelRatio || 1, 1.5)
export const W = env.mobile || env.saveData ? 960 : innerWidth * dpr > 1280 ? 1920 : 1280
/** stand-in stills only exist at 1280 / 720 */
const STILL_W = env.mobile || env.saveData ? 720 : 1280
export const clipUrl = (id: string) => `/media/${id}_${W}.mp4`
export const posterUrl = (id: string) => `/media/${id}_${W}.webp`
const stillUrl = (id: string) => `/media/${id}_${STILL_W}.webp`
export const endPosterUrl = (id: string) => `/media/${id}_end_1920.webp`

/** First-frame poster for a segment, or null for gradient/globe. */
export function posterFor(m: Media): string | null {
  if (m.kind === 'video') return posterUrl(m.id)
  if (m.kind === 'still') return stillUrl(m.poster)
  // documentation: a pre-blurred, darkened still (no live CSS blur over the stage)
  if (m.kind === 'dom') return stillUrl(`${m.poster}-blur`)
  return null
}
