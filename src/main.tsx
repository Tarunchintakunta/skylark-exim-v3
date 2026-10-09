import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { startEngine } from './engine/ticker'
import './styles/global.css'

import { env } from './engine/env'

if (env.mobile) document.documentElement.classList.add('is-mobile')
if (env.reduced) document.documentElement.classList.add('is-reduced')

// /type: font pairing preview for Tarun (#88), dev and preview builds only
const TypePreview = lazy(() => import('./type/TypePreview'))
const typePage = __PREVIEW__ && location.pathname === '/type'
if (typePage) document.getElementById('boot')?.remove()
else startEngine()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {typePage ? (
      <Suspense fallback={null}>
        <TypePreview />
      </Suspense>
    ) : (
      <App />
    )}
  </StrictMode>,
)
