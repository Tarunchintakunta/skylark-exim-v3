import { chaptersFor } from './config/chapters'
import { useApp } from './engine/store'
import { Film } from './film/Film'
import { ScrubStage } from './film/ScrubStage'
import { Loader } from './ui/Loader'

export default function App() {
  const path = useApp((s) => s.path)
  const chapters = chaptersFor(path)
  return (
    <>
      <ScrubStage chapters={chapters} />
      <main id="main">
        <h1>Skylark Exim</h1>
        <Film chapters={chapters} />
      </main>
      <Loader />
    </>
  )
}
