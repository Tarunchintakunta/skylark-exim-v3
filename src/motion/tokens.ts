import type { Transition, Variants } from 'motion/react'

/** The one set of motion values for every page (#235). /story's film keeps its own GSAP scrub. */
export const DUR = { fast: 0.35, base: 0.6, slow: 0.9 } as const
export const EASE = [0.22, 1, 0.36, 1] as const
export const SPRING = { type: 'spring', stiffness: 120, damping: 20 } as const satisfies Transition
export const STAGGER = 0.06
/** whileInView: once, when a quarter of the block is on screen */
export const VIEWPORT = { once: true, amount: 0.25 } as const

/** a block whose [variants={rise}] children come in one after another */
export const group: Variants = { hidden: {}, show: { transition: { staggerChildren: STAGGER } } }
/** fade and rise: transform and opacity only */
export const rise: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: DUR.base, ease: EASE } },
}
