import { lazy, Suspense } from 'react'
import type { ChapterDef } from '../config/chapters'
import { useApp } from '../engine/store'

const GlobeCanvas = lazy(() => import('../three/Globe'))

/**
 * Mounts the R3F globe (lazy three.js chunks) from two chapters before the world chapter, and unmounts it once the film
 * has scrolled past (redesign §2.8): no WebGL context or render loop alive behind the business sections.
 */
export function GlobeLayer({ chapters }: { chapters: ChapterDef[] }) {
  const chapter = useApp((s) => s.chapter)
  const past = useApp((s) => s.past)
  const world = chapters.findIndex((c) => c.id === 'world')
  const near = chapters.findIndex((c) => c.id === chapter) >= world - 2
  if (!near || past) return null
  return (
    <Suspense fallback={null}>
      <GlobeCanvas />
    </Suspense>
  )
}
