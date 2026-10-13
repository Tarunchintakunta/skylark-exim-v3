import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Home from './Home'
import { env } from './engine/env'
import './styles/global.css'

if (env.mobile) document.documentElement.classList.add('is-mobile')
if (env.reduced) document.documentElement.classList.add('is-reduced')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Home />
  </StrictMode>,
)
