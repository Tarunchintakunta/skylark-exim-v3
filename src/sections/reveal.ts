import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { env } from '../engine/env'

/** Business-section reveals: [data-reveal] children rise in once as they enter (transform/opacity only). */
export function bindReveals(root: HTMLElement) {
  const els = root.querySelectorAll<HTMLElement>('[data-reveal]')
  if (env.reduced || !els.length) return () => {}
  gsap.set(els, { y: 28, autoAlpha: 0 })
  const triggers = ScrollTrigger.batch(els, {
    start: 'top 88%',
    once: true,
    onEnter: (batch) => gsap.to(batch, { y: 0, autoAlpha: 1, duration: 0.8, stagger: 0.07, ease: 'power3.out' }),
  })
  return () => triggers.forEach((t) => t.kill())
}
