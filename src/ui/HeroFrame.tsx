import * as m from 'motion/react-m'
import type { MouseEvent, Ref } from 'react'
import { exportsLine, start } from '../config/content'
import type { Path } from '../engine/store'
import { env } from '../engine/env'
import { useApp } from '../engine/store'
import { FILM_W, clipUrl, posterUrl } from '../film/segments'
import { DUR, EASE, STAGGER } from '../motion/tokens'
import './hero.css'

const PATHS = ['ocean', 'pond'] as const

/**
 * The headline's one-time reveal once the loader has gone (#237): word by word, a lift and a dip in light that starts and
 * ends fully visible. The static HTML copy is the LCP element and is never hidden; this runs on React's copy after the
 * hand-off, transform and opacity only. Words are inline-block (kerning inside a word is kept, so nothing reflows).
 */
const WAVE = (i: number) => ({
  y: ['0em', '-0.08em', '0em'],
  opacity: [1, 0.55, 1],
  transition: { duration: DUR.slow, ease: EASE, delay: i * STAGGER * 2 },
})

function Title({ lead, last }: { lead: string; last: string }) {
  const revealed = useApp((s) => s.revealed)
  const words = [...lead.split(' ').map((w) => <>{w}</>), <><em>{last}</em>.</>]
  return (
    <h1 className="hero__title">
      {words.map((w, i) => (
        <span key={i}>
          {i > 0 && ' '}
          <m.span className="hero__word" animate={revealed && !env.reduced ? WAVE(i) : undefined}>
            {w}
          </m.span>
        </span>
      ))}
    </h1>
  )
}

/**
 * The hero's markup (redesign §3), shared by the homepage and /story: a full-bleed looping coastal video (#197), one
 * editorial headline, one line of body, the exports line, Contact us, the story fork and a slim scroll cue.
 * scripts/static-hero.ts writes the same copy into the HTML. `fork` is where the fork links point ('#' in the film,
 * '/story#' on the homepage); `current` marks the chosen path (the film only).
 */
export function HeroFrame({
  root,
  media,
  video,
  fork,
  current,
  onFork,
}: {
  root: Ref<HTMLDivElement>
  media: Ref<HTMLDivElement>
  video: Ref<HTMLVideoElement>
  fork: '#' | '/story#'
  current?: Path
  onFork?: (path: Path, e: MouseEvent<HTMLAnchorElement>) => void
}) {
  const [lead, last] = [start.title.replace(/ world\.$/, ''), 'world']
  return (
    <div className="hero" ref={root}>
      {/* looping coastal shot (not scrubbed); reduced motion gets the poster only */}
      <div className="hero__media" ref={media}>
      <video
        ref={video}
        className="hero__video"
        src={env.reduced ? undefined : clipUrl('hero-loop', FILM_W)}
        poster={posterUrl('hero-loop')}
        autoPlay={!env.reduced}
        muted
        loop
        playsInline
        preload={env.reduced ? 'none' : 'auto'}
        disablePictureInPicture
        tabIndex={-1}
        aria-hidden="true"
      />
      </div>
      <div className="hero__copy">
        <Title lead={lead} last={last} />
        <p className="hero__body">{start.body}</p>
        <div className="hero__exports">
          <h2 className="hero__exports-title mono">{exportsLine.title}</h2>
          <ul>
            {exportsLine.items.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <a className="hero__contact" href="/quote">
          Contact us
        </a>
        {/* the fork (#219): two separate stories; the static copy in the HTML carries the same markup */}
        <div className="hero__fork" role="group" aria-label={start.choose}>
          <span className="hero__fork-label mono">{start.choose}</span>
          {PATHS.map((p) => (
            <a
              key={p}
              className="hero__fork-btn"
              href={`${fork}${p}`}
              data-path={p}
              aria-current={current === p ? 'true' : undefined}
              onClick={onFork && ((e) => onFork(p, e))}
            >
              {start[p].sub}
            </a>
          ))}
        </div>
      </div>
      <span className="hero__cue" aria-hidden="true">
        Scroll
      </span>
    </div>
  )
}

/** Plays the loop only while it can be seen: off-screen, a hidden tab or `hidden()` (the film's hand-off) pauses it. */
export function bindLoop(v: HTMLVideoElement | null, hidden: () => boolean = () => false) {
  if (!v || env.reduced) return { sync: () => {}, stop: () => {} }
  let inView = true
  const sync = () => (inView && !document.hidden && !hidden() ? v.play().catch(() => {}) : v.pause())
  const io = new IntersectionObserver(([e]) => {
    inView = e.isIntersecting
    sync()
  })
  io.observe(v)
  document.addEventListener('visibilitychange', sync)
  return {
    sync,
    stop: () => {
      io.disconnect()
      document.removeEventListener('visibilitychange', sync)
    },
  }
}
