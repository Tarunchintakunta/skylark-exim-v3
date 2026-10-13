import { useSpring } from 'motion/react'
import * as m from 'motion/react-m'
import type { PointerEvent } from 'react'
import { chaptersFor, firstClip } from '../config/chapters'
import { HOME } from '../config/content'
import { env } from '../engine/env'
import { cardSrcSet, mediaUrl } from '../film/segments'
import { SPRING_OPTS, reveal, rise } from '../motion/tokens'

const PATHS = ['ocean', 'pond'] as const
/** card width: one column on phones (gutters at most 2 × 32 px there), two above (CSS vars are not allowed in sizes) */
const SIZES = '(max-width: 819px) calc(100vw - 40px), 46vw'
/** poster travel at the card's edge (px) and the zoom that keeps its edges covered */
const SHIFT = 10
const ZOOM = 1.05

/** A path's own chapters, then where both end: the route the card's story takes. */
const route = (path: (typeof PATHS)[number]) => [...chaptersFor(path).filter((c) => c.path === path).map((c) => c.label), ...HOME.stories.end]

/** One story card: the poster drifts against the mouse (a spring, transform only); touch and reduced motion keep it still. */
function StoryCard({ path }: { path: (typeof PATHS)[number] }) {
  const clip = firstClip(path)!
  const x = useSpring(0, SPRING_OPTS)
  const y = useSpring(0, SPRING_OPTS)
  const scale = useSpring(1, SPRING_OPTS)
  const move = (e: PointerEvent<HTMLAnchorElement>) => {
    if (e.pointerType !== 'mouse' || env.reduced) return
    const r = e.currentTarget.getBoundingClientRect()
    x.set(((e.clientX - r.left) / r.width - 0.5) * -2 * SHIFT)
    y.set(((e.clientY - r.top) / r.height - 0.5) * -2 * SHIFT)
    scale.set(ZOOM)
  }
  const leave = () => (x.set(0), y.set(0), scale.set(1))
  return (
    <m.li className="story-card" variants={rise}>
      <a className="story-card__link" href={`/story#${path}`} data-story={path} onPointerMove={move} onPointerLeave={leave}>
        <span className="story-card__poster">
          {/* the path's first frame, from its own clip; lazy: nothing of the film loads before it is near */}
          <picture>
            <source type="image/avif" srcSet={cardSrcSet(clip.id, 'avif')} sizes={SIZES} />
            <m.img
              className="story-card__img"
              style={{ x, y, scale }}
              src={mediaUrl(`${clip.id}_960.webp`)}
              srcSet={cardSrcSet(clip.id, 'webp')}
              sizes={SIZES}
              width={960}
              height={540}
              alt={clip.alt}
              loading="lazy"
              decoding="async"
            />
          </picture>
        </span>
        <h3 className="story-card__title display">{HOME.stories[path].title}</h3>
        <p className="story-card__route mono">{route(path).join(' · ')}</p>
        <span className="story-card__cta">
          <u>{HOME.stories[path].cta}</u> <span aria-hidden="true">→</span>
        </span>
      </a>
    </m.li>
  )
}

/** Intro band and the two story cards: each opens its own path on /story, on its first chapter (o1 / p1). */
export function Intro() {
  return (
    <section id="intro" className="section theme-light home-intro" aria-labelledby="intro-title">
      <m.header className="section__head" {...reveal}>
        <m.p className="eyebrow mono" variants={rise}>{HOME.intro.eyebrow}</m.p>
        <m.h2 id="intro-title" className="section__title" variants={rise}>{HOME.intro.title}</m.h2>
        <m.p className="home-intro__body" variants={rise}>{HOME.intro.body}</m.p>
      </m.header>
      <m.ul className="story-cards" {...reveal}>
        {PATHS.map((path) => (
          <StoryCard key={path} path={path} />
        ))}
      </m.ul>
    </section>
  )
}
