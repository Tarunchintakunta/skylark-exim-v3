import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { bindStoryPrefetch } from './home/prefetch'
import { HomeHero } from './home/HomeHero'
import { Loader } from './ui/Loader'
import { PageHeader } from './ui/PageHeader'
import './ui/chrome.css'

/** Everything below the hero: its own chunk, fetched once the first screen has painted (as /story does, #207). */
const Sections = lazy(() => import('./home/Sections'))

let mounted = () => {}
const MOUNTED = new Promise<void>((r) => {
  const was = mounted
  mounted = () => (was(), r())
})

/**
 * Homepage (#233): the scroll-scrubbed hero frame sequence, then a normal scrolling company page. The film, its engine and its clips
 * live on /story; story links here only prefetch it on hover or focus.
 */
export default function Home() {
  const hero = useRef<HTMLElement>(null)
  // the bar sits over the hero in the film's dark style, and turns to sand once the hero has scrolled under it
  const [light, setLight] = useState(false)
  useEffect(() => {
    const io = new IntersectionObserver(([e]) => setLight(!e.isIntersecting), { rootMargin: '-68px 0px 0px 0px' })
    io.observe(hero.current!)
    return () => io.disconnect()
  }, [])
  useEffect(bindStoryPrefetch, [])
  return (
    <>
      <a className="skip-link mono" href="#main">Skip to content</a>
      <a className="skip-link mono" href="/quote">Skip to quote</a>
      <PageHeader current="home" light={light} />
      <main id="main" tabIndex={-1}>
        <HomeHero sectionRef={hero} />
        <Suspense fallback={null}>
          <Sections onMount={mounted} />
        </Suspense>
      </main>
      <Loader mounted={MOUNTED} />
    </>
  )
}
