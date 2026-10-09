import { chaptersFor } from './config/chapters'
import { useApp } from './engine/store'
import { Film } from './film/Film'
import { ScrubStage } from './film/ScrubStage'
import { Hud } from './ui/Hud'
import { Loader } from './ui/Loader'
import { PathPill } from './ui/PathPill'
import { StartScreen } from './ui/StartScreen'

export default function App() {
  const path = useApp((s) => s.path)
  const chapters = chaptersFor(path)
  return (
    <>
      <ScrubStage chapters={chapters} />
      <main id="main">
        <StartScreen />
        <Film chapters={chapters} />
      </main>
      <Hud />
      <PathPill />
      <Loader />
    </>
  )
}
