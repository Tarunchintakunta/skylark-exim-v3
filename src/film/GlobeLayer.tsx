import { lazy, Suspense, useEffect, useState } from 'react'
import type { ChapterDef } from '../config/chapters'
import { env } from '../engine/env'
import { useApp } from '../engine/store'
import { GLOBE_TEXTURE } from '../three/globeState'

const loadGlobe = () => import('../three/Globe')
const GlobeCanvas = lazy(loadGlobe)
/** the globe's entry frame (close over the sea off Visakhapatnam), shown until the live globe has drawn */
const PLACEHOLDER = `/textures/globe-ph_${env.mobile ? 720 : 1280}.webp`

const idle = (fn: () => void) => ('requestIdleCallback' in window ? requestIdleCallback(fn, { timeout: 2000 }) : setTimeout(fn, 300))
let fetched = false
/** Warm the globe in idle time, never during the first load: placeholder first (smallest), then the chunks and the texture. */
function prefetch() {
  if (fetched) return
  fetched = true
  idle(() => {
    new Image().src = PLACEHOLDER
    void loadGlobe()
    new Image().src = GLOBE_TEXTURE
  })
}

/**
 * Mounts the R3F globe (lazy three.js chunks) from two chapters before the world chapter, and unmounts it once the film
 * has scrolled past (redesign §2.8): no WebGL context or render loop alive behind the business sections.
 * One chapter earlier the chunks, texture and placeholder are fetched in idle time, so the globe is ready on arrival;
 * the placeholder covers the frames until the live globe draws (#D).
 */
export function GlobeLayer({ chapters }: { chapters: ChapterDef[] }) {
  const chapter = useApp((s) => s.chapter)
  const past = useApp((s) => s.past)
  const ready = useApp((s) => s.ready)
  const world = chapters.findIndex((c) => c.id === 'world')
  const at = chapters.findIndex((c) => c.id === chapter)
  const warm = ready && at >= world - 3
  const near = at >= world - 2
  const [ph, setPh] = useState(false)
  useEffect(() => {
    if (!warm) return
    prefetch()
    setPh(true)
  }, [warm])
  if (past) return null
  return (
    <>
      {ph && <img className="globe-ph" src={PLACEHOLDER} alt="" decoding="async" />}
      {near && (
        <Suspense fallback={null}>
          <GlobeCanvas />
        </Suspense>
      )}
    </>
  )
}
