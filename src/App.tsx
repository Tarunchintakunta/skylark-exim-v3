import { chaptersFor } from './config/chapters'
import { useApp } from './engine/store'
import { Film } from './film/Film'
import { Products } from './sections/Products'
import { ScrubStage } from './film/ScrubStage'
import { Hud } from './ui/Hud'
import { Loader } from './ui/Loader'
import { Header } from './ui/Header'
import { QuoteCta } from './ui/QuoteCta'
import { Rail } from './ui/Rail'
import { StartScreen } from './ui/StartScreen'

export default function App() {
  const path = useApp((s) => s.path)
  const chapters = chaptersFor(path)
  return (
    <>
      <a className="skip-link mono" href="#main">Skip to content</a>
      <ScrubStage chapters={chapters} />
      <Header />
      <main id="main" tabIndex={-1}>
        <StartScreen />
        <Rail chapters={chapters} />
        <Film chapters={chapters} />
        <Products />
      </main>
      <Hud />
      <QuoteCta />
      <Loader />
    </>
  )
}
