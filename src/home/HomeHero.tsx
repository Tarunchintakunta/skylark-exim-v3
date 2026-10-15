import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'
import { useEffect, useRef, type RefObject } from 'react'
import { exportsLine, start } from '../config/content'
import { env } from '../engine/env'
import { useApp } from '../engine/store'
import { ScrollSequence, type FrameSet } from '../ui/ScrollSequence'
import '../ui/hero.css'

gsap.registerPlugin(SplitText)

const FRAMES = { desktop: 60, mobile: 60 }
export const heroFrame = (set: FrameSet, i: number) => `/sequence/hero/${set}/hero_${String(i + 1).padStart(3, '0')}.webp`
const PATHS = ['ocean', 'pond'] as const

export function HomeHero({ sectionRef }: { sectionRef: RefObject<HTMLElement | null> }) {
  const ready = useApp((s) => s.ready)
  const root = useRef<HTMLDivElement>(null)
  const lead = start.title.replace(/ world\.$/, '')

  useEffect(() => {
    if (!ready) return
    root.current!.style.visibility = 'visible'
    root.current!.style.opacity = '1'
  }, [ready])

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
    <ScrollSequence src={heroFrame} frames={FRAMES} length="300vh" className="home-hero" sectionRef={sectionRef}>
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
