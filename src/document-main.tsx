import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { DocumentApp } from './pages/DocumentApp'
import './styles/global.css'
import './ui/chrome.css'
import './sections/sections.css'
import './ui/pages.css'

document.documentElement.dataset.ready = '1'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DocumentApp />
  </StrictMode>,
)
