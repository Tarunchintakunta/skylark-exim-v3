import { lazy, startTransition, Suspense, useEffect, useRef, useState } from 'react'
import { film } from '../config/content'
import { MarketList } from '../sections/MarketList'
import { store } from '../engine/store'
import { GLOBE_POSTER } from '../three/globeState'
import * as m from 'motion/react-m'
import { reveal, rise } from '../motion/tokens'

/** the globe box's width (home.css .home-globe) */
const POSTER_SIZES = '(max-width: 819px) min(420px, 100vw), min(720px, 45vw)'
const loadGlobe = () => import('../three/Globe')
const GlobeCanvas = lazy(loadGlobe)
let warmed: Promise<unknown> | null = null
/** the globe's chunk and its decoded texture, once (#274) */
const warmGlobe = () => (warmed ??= loadGlobe().then((g) => g.preloadGlobe()).catch(() => void (warmed = null)))

const idle = (fn: () => void, timeout: number) => ('requestIdleCallback' in window ? requestIdleCallback(fn, { timeout }) : setTimeout(fn, 200))

/**
 * Markets: the region list and the live globe. The poster (the globe's exact first view) shows at once; the globe's code
 * and texture are fetched and decoded in idle time after the intro. When the section is 1.5 viewports away the live
 * globe mounts in idle time (it warms its texture and shaders in further idle slices, see three/Globe.tsx) and
 * crossfades in over the poster, usually before the section is on screen.
 */
export function Markets() {
  const box = useRef<HTMLDivElement>(null)
  const [near, setNear] = useState(false)
  useEffect(() => {
    // the mount itself is short once the chunk and the decoded texture are in (the heavy parts, texture upload and
    // shader compile, run in idle slices after it), so it may land mid-scroll, as a transition in idle time (#239)
    let gone = false
    const near = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return
      near.disconnect()
      void warmGlobe().then(() => idle(() => !gone && startTransition(() => setNear(true)), 500))
    }, { rootMargin: '150% 0px' })
    near.observe(box.current!)
    const warm = () => idle(() => void warmGlobe(), 4000)
    const off = store.getState().revealed ? (warm(), () => {}) : store.subscribe((s) => s.revealed && (off(), warm()))
    return () => ((gone = true), near.disconnect(), off())
  }, [])
  const world = film.world[0]
  return (
    <section id="markets" className="section theme-light home-markets" aria-labelledby="markets-title">
      <m.div className="home-markets__copy" {...reveal}>
        <m.p className="eyebrow mono" variants={rise}>Markets</m.p>
        <m.h2 id="markets-title" className="section__title" variants={rise}>{world.title}</m.h2>
        <MarketList />
      </m.div>
      <div className="home-globe" ref={box} data-globe>
        {/* the live globe's first view, shown until it has drawn (#223, #274) */}
        <picture>
          <source type="image/avif" srcSet={GLOBE_POSTER('avif')} sizes={POSTER_SIZES} />
          <img className="globe-ph" srcSet={GLOBE_POSTER('webp')} sizes={POSTER_SIZES} src="/textures/globe-home_1280.webp" alt="" width={2560} height={2560} loading="lazy" decoding="async" />
        </picture>
        {near && (
          <Suspense fallback={null}>
            <GlobeCanvas worldIndex={-1} />
          </Suspense>
        )}
      </div>
    </section>
  )
}
