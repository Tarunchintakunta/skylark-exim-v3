import { chaptersFor } from './config/chapters'
import { useApp } from './engine/store'
import { Film } from './film/Film'
import { About } from './sections/About'
import { Products } from './sections/Products'
import { Quote } from './sections/Quote'
import { Trust } from './sections/Trust'
import { ScrubStage } from './film/ScrubStage'
import { Loader } from './ui/Loader'
import { Header } from './ui/Header'
import { QuoteCta } from './ui/QuoteCta'
import { StartScreen } from './ui/StartScreen'

export default function App() {
  const path = useApp((s) => s.path)
  const chapters = chaptersFor(path)
  return (
    <>
      <a className="skip-link mono" href="#main">Skip to content</a>
      <a className="skip-link mono" href="#quote">Skip to quote</a>
      <ScrubStage chapters={chapters} />
      <Header />
      <main id="main" tabIndex={-1}>
        <StartScreen />
        <Film chapters={chapters} />
        <Products />
        <Trust />
        <About />
        <Quote />
      </main>
      <QuoteCta />
      <Loader />
    </>
  )
}
