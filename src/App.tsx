import { useEffect } from 'react'
import { chaptersFor } from './config/chapters'
import { bindPathHash } from './engine/path'
import { useApp } from './engine/store'
import { scrollToY } from './engine/ticker'
import { Film } from './film/Film'
import { About } from './sections/About'
import { Close } from './sections/Close'
import { Products } from './sections/Products'
import { Trust } from './sections/Trust'
import { bindRise } from './sections/rise'
import { Contact } from './sections/Contact'
import { ScrubStage } from './film/ScrubStage'
import { Loader } from './ui/Loader'
import { Header } from './ui/Header'
import { Hero } from './ui/Hero'

export default function App() {
  const path = useApp((s) => s.path)
  const ready = useApp((s) => s.ready)
  const chapters = chaptersFor(path)
  useEffect(() => bindRise(document.getElementById('products')!), [])
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
  return (
    <>
      <a className="skip-link mono" href="#main">Skip to content</a>
      <a className="skip-link mono" href="/quote">Skip to quote</a>
      <ScrubStage chapters={chapters} />
      <Header />
      <main id="main" tabIndex={-1}>
        <Hero />
        <Film chapters={chapters} />
        <Products />
        <Trust />
        <About />
        <Close />
        <Contact />
      </main>
      <Loader />
    </>
  )
}
