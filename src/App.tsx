import { lazy, Suspense } from 'react'
import { chaptersFor } from './config/chapters'
import { useApp } from './engine/store'
import { ScrubStage } from './film/ScrubStage'
import { Loader } from './ui/Loader'
import { Header } from './ui/Header'
import { Hero } from './ui/Hero'

const Story = lazy(() => import('./Story'))

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
        <Hero />
        <Suspense fallback={null}>
          <Story chapters={chapters} />
        </Suspense>
      </main>
      <Loader />
    </>
  )
}
