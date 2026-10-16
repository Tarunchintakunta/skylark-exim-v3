import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ENTRY_CARDS } from './config/storyEntry'
import { env } from './engine/env'
import { startEngine } from './engine/ticker'
import { StoryEntry } from './home/StoryEntry'
import './styles/global.css'

// Design review for #268 (removed in phase 2): the section between a stand-in for the hero and the sand page below it.
// ?open=wild|farmed|world starts with that card open.
if (env.mobile) document.documentElement.classList.add('is-mobile')
if (env.reduced) document.documentElement.classList.add('is-reduced')
document.documentElement.dataset.ready = '1'
startEngine()

const q = new URLSearchParams(location.search).get('open')
const initial = ENTRY_CARDS.find((c) => c.id === q)?.id
const band = { display: 'grid', placeItems: 'center', fontFamily: 'var(--f-body)', fontSize: 'var(--fs-small)', letterSpacing: '0.04em' } as const

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <main>
      <div style={{ ...band, height: '40vh', color: 'var(--steel)' }}>Homepage hero above</div>
      <StoryEntry initial={initial} />
      <div className="theme-light" style={{ ...band, height: '60vh' }}>Homepage sections below</div>
    </main>
  </StrictMode>,
)
