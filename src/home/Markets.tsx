import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { film } from '../config/content'
import { env } from '../engine/env'
import { MarketList } from '../sections/MarketList'
import * as m from 'motion/react-m'
import { reveal, rise } from '../motion/tokens'

const GlobeCanvas = lazy(() => import('../three/Globe'))
/** the globe's entry frame (close over the sea off Visakhapatnam), shown until the live globe has drawn (#223) */
const PLACEHOLDER = `/textures/globe-ph_${env.mobile ? 720 : 1280}.webp`

/** Markets: the region list and the live globe, placeholder first; the three.js chunks load only as the section nears. */
export function Markets() {
  const box = useRef<HTMLDivElement>(null)
  const [near, setNear] = useState(false)
  useEffect(() => {
    const io = new IntersectionObserver(([e]) => e.isIntersecting && setNear(true), { rootMargin: '50% 0px' })
    io.observe(box.current!)
    return () => io.disconnect()
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
        <img className="globe-ph" src={PLACEHOLDER} alt="" width={1280} height={720} loading="lazy" decoding="async" />
        {near && (
          <Suspense fallback={null}>
            <GlobeCanvas worldIndex={-1} />
          </Suspense>
        )}
      </div>
    </section>
  )
}
