import { lazy, Suspense, useEffect } from 'react'
import { chaptersFor, firstClip } from './config/chapters'
import { storyReady } from './engine/boot'
import { bindPathHash } from './engine/path'
import type { Gate } from './engine/preload'
import { store, useApp } from './engine/store'
import { scrollToY } from './engine/ticker'
import { ScrubStage } from './film/ScrubStage'
import { warm } from './film/scrub'
import { startWarmCache } from './film/warmcache'
import { Loader } from './ui/Loader'
import { Header } from './ui/Header'
import { Hero } from './ui/Hero'

const Story = lazy(() => import('./Story'))

// the chosen path's first clip (#ocean / #pond, else wild catch)
const clip = firstClip(store.getState().path)
const first = clip ? [clip.id] : []
const WAIT: Gate = { mounted: storyReady, clips: { n: first.length, start: () => warm(first) } }

export default function App() {
  const path = useApp((s) => s.path)
  const ready = useApp((s) => s.ready)
  const chapters = chaptersFor(path)
  useEffect(() => {
    if (!ready) return
    const id = location.hash.slice(1)
    if (!id || id === 'ocean' || id === 'pond') return
    let raf = 0
    let frames = 0
    const tick = () => {
      frames += 1
      if (document.getElementById('boot') && frames < 180) {
        raf = requestAnimationFrame(tick)
        return
      }
      const el = document.getElementById(id)
      if (el) scrollToY(el.getBoundingClientRect().top + window.scrollY, true)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [ready])
  // #ocean / #pond: the path anchors (#210); other section anchors (/#products from /quote) are handled above
  useEffect(bindPathHash, [])
  useEffect(startWarmCache, [])
  return (
    <>
      <a className="skip-link mono" href="#main">Skip to content</a>
      <a className="skip-link mono" href="/quote">Skip to quote</a>
      <ScrubStage chapters={chapters} />
      <Header />
      <main id="main" tabIndex={-1}>
        <Hero />
        <Suspense fallback={null}>
          <Story chapters={chapters} />
        </Suspense>
      </main>
      <Loader wait={WAIT} />
    </>
  )
}
