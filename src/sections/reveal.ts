import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { env } from '../engine/env'

/**
 * Business-section reveals: [data-reveal] children rise in once as they enter (transform/opacity only).
 * Opacity, not autoAlpha: a hidden-until-scrolled element must stay focusable and clickable, so keyboard users can
 * tab to a card below the fold and the click/scroll that brings it into view also reveals it.
 */
export function bindReveals(root: HTMLElement) {
  const els = root.querySelectorAll<HTMLElement>('[data-reveal]')
  if (env.reduced || !els.length) return () => {}
  gsap.set(els, { y: 28, opacity: 0 })
  const triggers = ScrollTrigger.batch(els, {
    start: 'top 88%',
    once: true,
    onEnter: (batch) => gsap.to(batch, { y: 0, opacity: 1, duration: 0.8, stagger: 0.07, ease: 'power3.out' }),
  })
  // focusing an element that hasn't revealed yet (keyboard) shows it at once
  const onFocus = (e: FocusEvent) => {
    const el = (e.target as HTMLElement).closest<HTMLElement>('[data-reveal]')
    if (el && Number(getComputedStyle(el).opacity) < 1) gsap.to(el, { y: 0, opacity: 1, duration: 0.3, overwrite: true })
  }
  root.addEventListener('focusin', onFocus)
  return () => {
    root.removeEventListener('focusin', onFocus)
    triggers.forEach((t) => t.kill())
  }
}
