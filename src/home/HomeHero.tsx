import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'
import { useEffect, useRef, type RefObject } from 'react'
import { exportsLine, start } from '../config/content'
import { HERO_SEQ, heroFrameFile } from '../config/hero'
import { env } from '../engine/env'
import { store, useApp } from '../engine/store'
import { HERO_POSTER, avifReady, mediaUrl } from '../film/segments'
import { ScrollSequence, type FrameSet } from '../ui/ScrollSequence'
import '../ui/hero.css'

gsap.registerPlugin(SplitText)

/** AVIF where it decodes, else WebP; settled before the first frame URL is built (ScrollSequence `wait`) */
let ext: 'avif' | 'webp' = 'webp'

/**
 * The frame set waits for the intro to open and then for idle time (#264): the LCP image is the hero's own poster, and
 * nothing of the sequence competes with the first screen. Terminal loads its frames the same way.
 */
const idle = (f: () => void) => ('requestIdleCallback' in window ? requestIdleCallback(() => f(), { timeout: 2000 }) : setTimeout(f, 300))
const afterLcp = new Promise<void>((done) => {
  const go = () => idle(done)
  if (store.getState().revealed) return go()
  const off = store.subscribe((s) => {
    if (!s.revealed) return
    off()
    go()
  })
})
const ready = Promise.all([avifReady.then((ok) => (ext = ok ? 'avif' : 'webp')), afterLcp])
export const heroFrame = (set: FrameSet, i: number) => mediaUrl(heroFrameFile(set, i, ext))

/** the hero's first frame, the LCP image: the same <picture> and preloads the film's hero uses (config/hero.ts) */
const Poster = () => (
  <picture>
    {HERO_POSTER.map((p) => (
      <source key={p.type + p.media} type={p.type} media={p.media} srcSet={p.srcSet} sizes="100vw" />
    ))}
    <img className="seq__poster" src={mediaUrl('hero-loop_1280.webp')} alt="" fetchPriority="high" decoding="async" />
  </picture>
)
const PATHS = ['ocean', 'pond'] as const

export function HomeHero({ sectionRef }: { sectionRef: RefObject<HTMLElement | null> }) {
  const revealed = useApp((s) => s.revealed)
  const root = useRef<HTMLDivElement>(null)
  const lead = start.title.replace(/ world\.$/, '')

  useEffect(() => {
    if (!revealed) return
    root.current!.style.visibility = 'visible'
    root.current!.style.opacity = '1'
  }, [revealed])

  useGSAP(
    () => {
      if (env.reduced) return
      const q = gsap.utils.selector(root)
      const body = SplitText.create(q('.hero__body'), { type: 'lines', mask: 'lines' })
      const tl = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: { trigger: sectionRef.current, start: 'top top', end: 'bottom bottom', scrub: true },
      })
      tl.to({}, { duration: 1 }, 0)
      tl.fromTo(q('.hero__title'), { y: 0 }, { y: '-3vh', ease: 'power2.out', duration: 0.15 }, 0)
      tl.fromTo(q('.hero__cue'), { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.1 }, 0)
      tl.fromTo(body.lines, { yPercent: 110 }, { yPercent: 0, ease: 'power3.out', duration: 0.12, stagger: 0.015 }, 0.35)
      tl.fromTo(q('.hero__body, .hero__exports'), { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.04 }, 0.35)
      tl.fromTo(q('.hero__exports'), { y: 24 }, { y: 0, ease: 'power3.out', duration: 0.1 }, 0.4)
      tl.fromTo(q('.hero__contact, .hero__fork'), { autoAlpha: 0, y: 32 }, { autoAlpha: 1, y: 0, ease: 'power3.out', duration: 0.15, stagger: 0.03 }, 0.85)
      return () => body.revert()
    },
    { scope: root },
  )

  return (
    <ScrollSequence src={heroFrame} frames={HERO_SEQ} wait={ready} poster={<Poster />} length="300vh" className="home-hero" sectionRef={sectionRef}>
      <div className="hero" ref={root}>
        <div className="hero__media" />
        <div className="hero__copy">
          <h1 className="hero__title">
            {lead} <em>world</em>.
          </h1>
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
          <div className="hero__fork" role="group" aria-label={start.choose}>
            <span className="hero__fork-label mono">{start.choose}</span>
            {PATHS.map((p) => (
              <a key={p} className="hero__fork-btn" href={`/story#${p}`} data-path={p}>
                {start[p].sub}
              </a>
            ))}
          </div>
        </div>
        <span className="hero__cue" aria-hidden="true">
          Scroll
        </span>
      </div>
    </ScrollSequence>
  )
}
