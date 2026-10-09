import { lazy, Suspense } from 'react'
import type { ChapterDef } from '../config/chapters'
import { useApp } from '../engine/store'

const GlobeCanvas = lazy(() => import('../three/Globe'))

/** Mounts the R3F globe (lazy three.js chunk) only from two chapters before the world chapter. */
export function GlobeLayer({ chapters }: { chapters: ChapterDef[] }) {
  const chapter = useApp((s) => s.chapter)
  const world = chapters.findIndex((c) => c.id === 'world')
  const near = chapters.findIndex((c) => c.id === chapter) >= world - 2
  if (!near) return null
  return (
    <Suspense fallback={null}>
      <GlobeCanvas />
    </Suspense>
  )
}
