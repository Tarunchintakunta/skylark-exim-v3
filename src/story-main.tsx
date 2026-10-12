import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { startEngine } from './engine/ticker'
import './styles/global.css'

import { env } from './engine/env'

if (env.mobile) document.documentElement.classList.add('is-mobile')
if (env.reduced) document.documentElement.classList.add('is-reduced')

startEngine()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
