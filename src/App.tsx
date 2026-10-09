import { useEffect } from 'react'
import { chaptersFor } from './config/chapters'
import { store, useApp } from './engine/store'
import { Film } from './film/Film'
import { ScrubStage } from './film/ScrubStage'

export default function App() {
  const path = useApp((s) => s.path)
  const chapters = chaptersFor(path)
  // replaced by the loader (#4)
  useEffect(() => {
    store.setState({ ready: true })
    document.documentElement.dataset.ready = '1'
  }, [])
  return (
    <>
      <ScrubStage chapters={chapters} />
      <main id="main">
        <h1>Skylark Exim</h1>
        <Film chapters={chapters} />
      </main>
    </>
  )
}
