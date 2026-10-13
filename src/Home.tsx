import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import type { Gate } from './engine/preload'
import { useApp } from './engine/store'
import { bindStoryPrefetch } from './home/prefetch'
import { HeroFrame, bindLoop } from './ui/HeroFrame'
import { Loader } from './ui/Loader'
import { PageHeader } from './ui/PageHeader'
import './ui/chrome.css'

/** Everything below the hero: its own chunk, fetched once the first screen has painted (as /story does, #207). */
const Sections = lazy(() => import('./home/Sections'))

let mounted = () => {}
const WAIT: Gate = { mounted: new Promise<void>((r) => (mounted = r)) }

/** The homepage hero: the same loop and copy as /story, as the first screen of a scrolling page (no film, no ticker). */
function HomeHero() {
  const ready = useApp((s) => s.ready)
  const root = useRef<HTMLDivElement>(null)
  const media = useRef<HTMLDivElement>(null)
  const video = useRef<HTMLVideoElement>(null)
  useEffect(() => bindLoop(video.current).stop, [])
  useEffect(() => {
    if (!ready) return
    // the static copy from index.html sits in the same place above it until the loader removes it (#207)
    root.current!.style.visibility = 'visible'
    root.current!.style.opacity = '1'
  }, [ready])
  return <HeroFrame root={root} media={media} video={video} fork="/story#" />
}

/**
 * Homepage (#233): the looping coastal hero, then a normal scrolling company page. The film, its engine and its clips
 * live on /story; story links here only prefetch it on hover or focus.
 */
export default function Home() {
  const hero = useRef<HTMLDivElement>(null)
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
        <div className="home-hero" ref={hero}>
          <HomeHero />
        </div>
        <Suspense fallback={null}>
          <Sections onMount={mounted} />
        </Suspense>
      </main>
      <Loader wait={WAIT} />
    </>
  )
}
