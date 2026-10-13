import { LazyMotion, MotionConfig } from 'motion/react'
import type { ReactNode } from 'react'
import { DUR, EASE } from './tokens'

const features = () => import('./features').then((m) => m.default)

/** Every page renders inside this: `m.` components only (strict), and reduced motion follows the OS setting. */
export function MotionRoot({ children }: { children: ReactNode }) {
  return (
    <LazyMotion features={features} strict>
      <MotionConfig reducedMotion="user" transition={{ duration: DUR.base, ease: EASE }}>
        {children}
      </MotionConfig>
    </LazyMotion>
  )
}
