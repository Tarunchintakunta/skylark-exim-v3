import { useEffect, useRef } from 'react'
import { chaptersFor, firstClip } from '../config/chapters'
import { HOME } from '../config/content'
import { bindReveals } from '../sections/reveal'

const PATHS = ['ocean', 'pond'] as const
const POSTER_W = [720, 960, 1280] as const

/** A path's own chapters, then where both end: the route the card's story takes. */
const route = (path: (typeof PATHS)[number]) => [...chaptersFor(path).filter((c) => c.path === path).map((c) => c.label), ...HOME.stories.end]

/** Intro band and the two story cards: each opens its own path on /story, on its first chapter (o1 / p1). */
export function Intro() {
  const root = useRef<HTMLElement>(null)
  useEffect(() => bindReveals(root.current!), [])
  return (
    <section id="intro" className="section theme-light home-intro" ref={root} aria-labelledby="intro-title">
      <header className="section__head">
        <p className="eyebrow mono" data-reveal>{HOME.intro.eyebrow}</p>
        <h2 id="intro-title" className="section__title" data-reveal>{HOME.intro.title}</h2>
        <p className="home-intro__body" data-reveal>{HOME.intro.body}</p>
      </header>
      <ul className="story-cards">
        {PATHS.map((path) => {
          const clip = firstClip(path)!
          return (
            <li key={path} className="story-card" data-reveal>
              <a className="story-card__link" href={`/story#${path}`} data-story={path}>
                {/* the path's first frame, from its own clip; lazy: nothing of the film loads before it is near */}
                <img
                  className="story-card__img"
                  src={`/media/${clip.id}_960.webp`}
                  srcSet={POSTER_W.map((w) => `/media/${clip.id}_${w}.webp ${w}w`).join(', ')}
                  sizes="(max-width: 819px) calc(100vw - 2 * var(--gutter)), 46vw"
                  width={960}
                  height={540}
                  alt={clip.alt}
                  loading="lazy"
                  decoding="async"
                />
                <h3 className="story-card__title display">{HOME.stories[path].title}</h3>
                <p className="story-card__route mono">{route(path).join(' · ')}</p>
                <span className="story-card__cta">
                  <u>{HOME.stories[path].cta}</u> <span aria-hidden="true">→</span>
                </span>
              </a>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
