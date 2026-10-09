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

/** A chapter's scroll length is split evenly across its media (o1 = a1 then a2). */
export function toSegments(chapters: ChapterDef[]): Segment[] {
  return chapters.flatMap((ch, chapter) =>
    ch.media.map((media, j, all) => ({
      media,
      chapter,
      from: j / all.length,
      to: (j + 1) / all.length,
      join: j === all.length - 1 ? ch.joinNext : undefined,
    })),
  )
}

export const W = env.mobile || env.saveData ? 720 : 1280
export const clipUrl = (id: string) => `/media/${id}_${W}.mp4`
export const posterUrl = (id: string) => `/media/${id}_${W}.webp`
export const endPosterUrl = (id: string) => `/media/${id}_end_1280.webp`

/** First-frame poster for a segment, or null for gradient/globe. */
export function posterFor(m: Media): string | null {
  if (m.kind === 'video') return posterUrl(m.id)
  if (m.kind === 'still') return posterUrl(m.poster)
  // documentation: a pre-blurred, darkened still (no live CSS blur over the stage)
  if (m.kind === 'dom') return posterUrl(`${m.poster}-blur`)
  return null
}
