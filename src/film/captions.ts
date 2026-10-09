import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'
import type { ChapterDef } from '../config/chapters'
import { env } from '../engine/env'

gsap.registerPlugin(SplitText)

interface Cap {
  el: HTMLElement
  split?: SplitText
  /** character splits for [data-type] (typed-in labels) */
  typed?: SplitText
}

/** captions[chapterIndex][captionIndex] */
let caps: Cap[][] = []
let active: Cap | null = null

export function bindCaptions(sections: HTMLElement[]) {
  for (const c of caps.flat()) {
    c.split?.revert()
    c.typed?.revert()
  }
  caps = sections.map((s) => [...s.querySelectorAll<HTMLElement>('.caption')].map((el) => ({ el })))
  active = null
  if (env.reduced) return
  document.fonts.ready.then(() => {
    for (const c of caps.flat()) {
      const h = c.el.querySelector<HTMLElement>('.caption__title')
      if (h) c.split = SplitText.create(h, { type: 'lines', mask: 'lines', linesClass: 'line', autoSplit: true })
      const typed = c.el.querySelectorAll('[data-type]')
      if (typed.length) c.typed = SplitText.create(typed, { type: 'chars' })
    }
  })
}

export function updateCaptions(ch: ChapterDef, index: number, p: number) {
  const k = ch.captions.findIndex((c) => p >= c.at[0] && p < c.at[1])
  const next = k >= 0 ? (caps[index]?.[k] ?? null) : null
  if (next === active) return
  if (active) hide(active)
  if (next) show(next)
  active = next
}

function show(c: Cap) {
  const { el } = c
  gsap.killTweensOf(el)
  gsap.set(el, { visibility: 'visible', autoAlpha: 1, y: 0 })
  if (env.reduced) return
  const fades = el.querySelectorAll('[data-fade]')
  if (c.split) gsap.fromTo(c.split.lines, { yPercent: 100 }, { yPercent: 0, duration: 0.9, stagger: 0.08, ease: 'power3.out', overwrite: true })
  gsap.fromTo(fades, { y: 24, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.8, delay: 0.2, stagger: 0.05, ease: 'power3.out', overwrite: true })
  const cards = el.querySelectorAll('[data-card]')
  if (cards.length) gsap.fromTo(cards, { yPercent: 40, autoAlpha: 0 }, { yPercent: 0, autoAlpha: 1, duration: 0.9, stagger: 0.12, delay: 0.15, ease: 'power3.out', overwrite: true })
  if (c.typed) gsap.fromTo(c.typed.chars, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.01, stagger: 0.035, delay: 0.6, ease: 'none', overwrite: true })
}

function hide(c: Cap) {
  gsap.to(c.el, { autoAlpha: 0, y: -40, duration: env.reduced ? 0.01 : 0.45, ease: 'power2.in', overwrite: true })
}
