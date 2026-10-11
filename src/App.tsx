import { useEffect } from 'react'
import { chaptersFor } from './config/chapters'
import { bindPathHash } from './engine/path'
import { useApp } from './engine/store'
import { Film } from './film/Film'
import { About } from './sections/About'
import { Products } from './sections/Products'
import { Quote } from './sections/Quote'
import { Trust } from './sections/Trust'
import { bindRise } from './sections/rise'
import { Contact } from './sections/Contact'
import { ScrubStage } from './film/ScrubStage'
import { Loader } from './ui/Loader'
import { Header } from './ui/Header'
import { Hero } from './ui/Hero'

export default function App() {
  const path = useApp((s) => s.path)
  const chapters = chaptersFor(path)
  useEffect(() => bindRise(document.getElementById('products')!), [])
  useEffect(bindPathHash, [])
  return (
    <>
      <a className="skip-link mono" href="#main">Skip to content</a>
      <a className="skip-link mono" href="#quote">Skip to quote</a>
      <ScrubStage chapters={chapters} />
      <Header />
      <main id="main" tabIndex={-1}>
        <Hero />
        <Film chapters={chapters} />
        <Products />
        <Trust />
        <About />
        <Quote />
        <Contact />
      </main>
      <Loader />
    </>
  )
}
