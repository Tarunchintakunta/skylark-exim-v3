/** Phones held upright (env.mobile, portrait): the 810×1440 portrait crops (#hd). The same test in CSS media query form. */
export const PORTRAIT = '(orientation: portrait) and (max-width: 819px), (orientation: portrait) and (pointer: coarse)'
const OTHER = '(orientation: landscape), (min-width: 820px) and (pointer: fine)'

/**
 * The hero loop's first frame (#197, #hd): the LCP image. One list for the hero <picture> (HeroFrame.tsx) and its
 * preloads (scripts/static-hero.ts), so the browser picks the same file for both. `url` versions a /media file.
 */
export const heroPoster = (url: (file: string) => string) =>
  (['avif', 'webp'] as const).flatMap((ext) => [
    { type: `image/${ext}`, media: PORTRAIT, srcSet: `${url(`hero-loop_m.${ext}`)} 810w` },
    { type: `image/${ext}`, media: OTHER, srcSet: [960, 1280, 1920].map((w) => `${url(`hero-loop_${w}.${ext}`)} ${w}w`).join(', ') },
  ])

/**
 * The hero's scroll sequence (#249, #264): frames per tier, from the same master as the hero loop. 1920×1080 on
 * desktop, the 810×1440 portrait crop on phones held upright, both AVIF and WebP (scripts/make-frames.sh).
 */
export const HERO_SEQ = { 1920: 60, m: 48 } as const
export type SeqTier = keyof typeof HERO_SEQ
export const heroFrameFile = (tier: SeqTier, i: number, ext: 'avif' | 'webp') =>
  `hero-seq_${tier}_${String(i + 1).padStart(3, '0')}.${ext}`
