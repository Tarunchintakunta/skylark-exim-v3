import { chaptersFor } from './config/chapters'
import { useApp } from './engine/store'
import { Film } from './film/Film'

export default function App() {
  const path = useApp((s) => s.path)
  return (
    <main id="main">
      <h1 className="sr-only">Skylark Exim</h1>
      <Film chapters={chaptersFor(path)} />
    </main>
  )
}
