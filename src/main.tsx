import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { startEngine } from './engine/ticker'
import './styles/global.css'

startEngine()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
