import { lazy, startTransition, Suspense, useEffect, useRef, useState } from 'react'
import { film } from '../config/content'
import { MarketList } from '../sections/MarketList'
import { GLOBE_PH } from '../three/globeState'
import * as m from 'motion/react-m'
import { reveal, rise } from '../motion/tokens'

const GlobeCanvas = lazy(() => import('../three/Globe'))

/** Markets: the region list and the live globe, placeholder first; the three.js chunks load only as the section nears. */
export function Markets() {
  const box = useRef<HTMLDivElement>(null)
  const [near, setNear] = useState(false)
  useEffect(() => {
    // mounting three.js is one long task (WebGL context, shaders): start it once the section is near AND the page has
    // stopped scrolling for 200 ms, as a transition, so it never lands in the middle of a scroll (#239). The placeholder
    // frame shows until then.
    let inView = false
    let quiet = 0
    const mount = () => inView && startTransition(() => setNear(true))
    const wait = () => (clearTimeout(quiet), (quiet = window.setTimeout(mount, 200)))
    const io = new IntersectionObserver(([e]) => (inView = e.isIntersecting) && wait(), { rootMargin: '50% 0px' })
    addEventListener('scroll', wait, { passive: true })
    io.observe(box.current!)
    return () => (io.disconnect(), removeEventListener('scroll', wait), clearTimeout(quiet))
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
        {/* the globe's entry frame (close over the sea off Visakhapatnam), shown until the live globe has drawn (#223) */}
        <picture>
          <source type="image/avif" srcSet={GLOBE_PH('avif').sq} />
          <img className="globe-ph" src={GLOBE_PH('webp').sq} alt="" width={1440} height={1440} loading="lazy" decoding="async" />
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
