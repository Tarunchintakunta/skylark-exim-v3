import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import type { Plugin } from 'vite'
import { chaptersFor } from '../src/config/chapters'

/**
 * Clip tiers (segments.ts): 'm' = 810×1440 portrait crop for phones held upright, 960 landscape phones / Save-Data,
 * 1280 / 1920 / 2560 by the frame's device px. Codecs: AV1 and HEVC everywhere, H.264 as the fallback (no 2560).
 */
export const TIERS = ['m', 960, 1280, 1920, 2560] as const
export type Tier = (typeof TIERS)[number]
export const CODECS = ['av1', 'hevc', 'h264'] as const
export type Codec = (typeof CODECS)[number]
export const clipFile = (id: string, tier: Tier, codec: Codec) => `${id}_${tier}${codec === 'h264' ? '' : `.${codec}`}.mp4`

/** TRD §13 budgets per /story path, and per file (tests/weight.spec.ts, tests/hd.spec.ts) */
const BUDGET = { desktop: 25e6, mobile: 12e6 }
export const FILE_CAP = 2300 * 1024
/**
 * What a /story path downloads besides /media (document, JS, CSS, fonts, globe placeholder and texture): the baseline
 * build's "other" bytes over a whole path (tests/hd.spec.ts: 0.78 MB at 1920×1080, 0.60 MB at 390×844), plus 10 %.
 * With the files below this model gave 31.42 MB for the baseline's farmed path at 1920; hd.spec measured 31.34 MB.
 */
const OTHER = { desktop: 0.86e6, mobile: 0.66e6 }
const profile = (t: Tier) => (t === 'm' || t === 960 ? 'mobile' : 'desktop')
/**
 * the hero loop is not a path clip: fixed caps, no larger than before the HD pass (the loader waits for it to play, so
 * its bytes are first-screen time): 6 s of calm sea
 */
const HERO_CAP: Record<Tier, number> = { m: 380 * 1024, 960: 380 * 1024, 1280: 630 * 1024, 1920: 1000 * 1024, 2560: FILE_CAP }

const OUT = new URL('../src/film/manifest.ts', import.meta.url)
const media = (f: string) => new URL(`../public/media/${f}`, import.meta.url)
const hash = (buf: Buffer) => createHash('sha256').update(buf).digest('hex').slice(0, 10)
/** a /media file's URL with its content hash, as segments.ts mediaUrl writes it (for the static HTML) */
export const versioned = (f: string) => `/media/${f}${existsSync(media(f)) ? `?v=${hash(readFileSync(media(f)))}` : ''}`
const PATHS = ['ocean', 'pond'] as const
const fileSize = (f: string) => (existsSync(media(f)) ? statSync(media(f)).size : 0)
const pathClips = (p: (typeof PATHS)[number]) => [
  ...new Set(chaptersFor(p).flatMap((ch) => ch.media.flatMap((m) => (m.kind === 'video' ? [m.id] : [])))),
]

/**
 * A path's bytes besides its clips at tier t, from the files on disk (AVIF: every browser that plays AV1 or HEVC here
 * decodes it): OTHER, the hero loop at its cap and its poster, each clip's first-frame poster, desktop's end frames,
 * the documentation still and the product stills the page shows at that size.
 */
function overhead(path: (typeof PATHS)[number], t: Tier) {
  const p = profile(t)
  // no 2560 posters yet when the 2560 tier is being decided: its 1920 posters stand in (an underestimate)
  const poster = (id: string) => fileSize(`${id}_${t}.avif`) || (t === 2560 ? fileSize(`${id}_1920.avif`) : 0)
  const posters = pathClips(path).reduce((a, id) => a + poster(id) + (p === 'desktop' ? fileSize(`${id}_end_1280.avif`) : 0), 0)
  const products = readdirSync(media('')).filter((f) => f.startsWith('prod-') && f.endsWith(p === 'desktop' ? '_640.avif' : '_960.avif'))
  return OTHER[p] + HERO_CAP[t] + poster('hero-loop') + posters + fileSize(`ph-docs-blur_${t}.avif`) + products.reduce((a, f) => a + fileSize(f), 0)
}

/**
 * Budget solver: bytes per clip and tier so each path's clips fill (budget − overhead) in proportion to their length,
 * max-min fair across the two paths (a clip on both paths gets the tighter path's rate; what that leaves over in the
 * other path goes to its own clips), never above the 2,300 KB file cap. Every tier gets the whole budget: a device
 * downloads one tier and one codec, so the tier on screen gets all of it.
 */
export function solveCaps(dur: Record<string, number>) {
  const caps: Record<string, Partial<Record<Tier, number>>> = { 'hero-loop': HERO_CAP }
  for (const t of TIERS) {
    const left = Object.fromEntries(PATHS.map((p) => [p, BUDGET[profile(t)] - overhead(p, t)]))
    const open = new Set(PATHS.flatMap(pathClips))
    while (open.size) {
      const rate = PATHS.map((p) => {
        const ids = pathClips(p).filter((id) => open.has(id))
        return { p, ids, r: ids.length ? left[p] / ids.reduce((a, id) => a + dur[id], 0) : Infinity }
      }).sort((a, b) => a.r - b.r)[0]
      for (const id of rate.ids) {
        const bytes = Math.floor(Math.min(FILE_CAP, rate.r * dur[id]))
        ;(caps[id] ??= {})[t] = bytes
        open.delete(id)
        for (const p of PATHS) if (pathClips(p).includes(id)) left[p] -= bytes
      }
    }
  }
  return caps
}

/**
 * The 2560 tier is served only where it fits (#hd): every 2560 file of a codec, encoded at its target quality, under the
 * file cap, and each path's 2560 clips plus overhead under the desktop budget. Otherwise that codec tops out at 1920.
 */
export function topTier(codec: Codec, size: (f: string) => number | null) {
  if (codec === 'h264') return { top: 1920 as const, why: 'H.264 has no 2560 tier' }
  const sizes = PATHS.map((p) => pathClips(p).map((id) => size(clipFile(id, 2560, codec))))
  if (sizes.flat().some((s) => s === null)) return { top: 1920 as const, why: `no ${codec} 2560 files: scripts/encode-all.sh drops them when a path does not fit` }
  const total = sizes.map((s, i) => (s as number[]).reduce((a, b) => a + b, 0) + overhead(PATHS[i], 2560))
  const over = (sizes.flat() as number[]).filter((s) => s > FILE_CAP).length
  const mb = total.map((b, i) => `${PATHS[i]} ${(b / 1e6).toFixed(1)} MB`).join(', ')
  if (over || total.some((b) => b > BUDGET.desktop))
    return { top: 1920 as const, why: `${codec} 2560 at target quality: ${mb}, ${over} files over 2,300 KB; budget 25 MB` }
  return { top: 2560 as const, why: `${codec} 2560 fits: ${mb}` }
}

/**
 * src/film/manifest.ts (#251, #hd): every clip of each path in story order, with its chapter, its place in the chapter,
 * and per codec and tier the byte size and a short content hash; the solver's top tier per codec; and a content hash for
 * every file in public/media. The hash goes on the URL (`?v=`), so /media/* is cached immutably and a re-encoded file is
 * still picked up. Rewritten on every build (only when it changed); committed, so typecheck runs without a build.
 */
export function manifestSource() {
  const files = readdirSync(media('')).filter((f) => !f.startsWith('.'))
  const v = new Map(files.map((f) => [f, hash(readFileSync(media(f)))]))
  const size = (f: string) => (v.has(f) ? readFileSync(media(f)).length : null)
  const top = Object.fromEntries(CODECS.map((c) => [c, topTier(c, size)]))
  const paths = PATHS.map((path) => {
    const clips = chaptersFor(path).flatMap((ch, chapter) => {
      const videos = ch.media.filter((m) => m.kind === 'video')
      return videos.map((m, seg) => {
        const codecs = CODECS.map((c) => {
          const tiers = TIERS.filter((t) => t !== 2560 || top[c].top === 2560).flatMap((t) => {
            const f = clipFile(m.id, t, c)
            if (!v.has(f)) {
              if (c === 'h264' && t !== 2560) throw new Error(`clip-manifest: missing public/media/${f}`)
              return []
            }
            return [`${typeof t === 'number' ? t : `'${t}'`}: { bytes: ${size(f)}, v: '${v.get(f)}' }`]
          })
          return `${c}: { ${tiers.join(', ')} }`
        })
        return `    { id: '${m.id}', chapter: ${chapter}, seg: ${seg}, of: ${videos.length}, files: { ${codecs.join(', ')} } },`
      })
    })
    return `  ${path}: [\n${clips.join('\n')}\n  ],`
  })
  return `// Generated by scripts/clip-manifest.ts from src/config/chapters.ts and public/media. Do not edit.
export type Tier = 'm' | 960 | 1280 | 1920 | 2560
export type Codec = 'av1' | 'hevc' | 'h264'
export interface ClipFile {
  bytes: number
  v: string
}
export interface Clip {
  id: string
  /** chapter index in the path's chapter list */
  chapter: number
  /** this clip's place among the chapter's clips, and how many it has */
  seg: number
  of: number
  files: Record<Codec, Partial<Record<Tier, ClipFile>>>
}

export const CLIPS: Record<'ocean' | 'pond', Clip[]> = {
${paths.join('\n')}
}

/** the budget solver's top desktop tier per codec (scripts/clip-manifest.ts topTier) */
export const TOP: Record<Codec, 1920 | 2560> = { ${CODECS.map((c) => `${c}: ${top[c].top}`).join(', ')} }

/** content hash of every file in public/media; mediaUrl (segments.ts) puts it on the URL */
export const MEDIA_V: Record<string, string> = {
${[...v].sort(([a], [b]) => (a < b ? -1 : 1)).map(([f, h]) => `  '${f}': '${h}',`).join('\n')}
}
`
}

export function clipManifest(): Plugin {
  return {
    name: 'clip-manifest',
    buildStart() {
      const next = manifestSource()
      for (const c of CODECS) {
        const t = topTier(c, (f) => (existsSync(media(f)) ? readFileSync(media(f)).length : null))
        this.info(`top tier ${c}: ${t.top} (${t.why})`)
      }
      if (!existsSync(OUT) || readFileSync(OUT, 'utf8') !== next) writeFileSync(OUT, next)
    },
  }
}

// CLI for scripts/encode-hf.sh: `tsx scripts/clip-manifest.ts caps <id>` prints "<tier> <bytes>" per tier, solved over
// the masters' durations; `tsx scripts/clip-manifest.ts top <codec>` prints the 2560 decision for that codec.
if (process.argv[1]?.endsWith('clip-manifest.ts')) {
  const [cmd, arg] = process.argv.slice(2)
  if (cmd === 'caps') {
    const probe = (id: string) =>
      +execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', `masters/${id}/master.mp4`], { encoding: 'utf8' })
    const dur = Object.fromEntries([...new Set(PATHS.flatMap(pathClips))].map((id) => [id, probe(id)]))
    const caps = solveCaps(dur)[arg]
    if (!caps) throw new Error(`clip-manifest: ${arg} is on no path`)
    for (const t of TIERS) console.log(t, caps[t])
  } else if (cmd === 'top') {
    const t = topTier(arg as Codec, (f) => (existsSync(media(f)) ? readFileSync(media(f)).length : null))
    console.log(t.top, t.why)
  }
}
