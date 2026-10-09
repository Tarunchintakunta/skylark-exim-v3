import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // preview deployments (and local) label placeholder scenes; production never does
  define: { __PREVIEW__: JSON.stringify(process.env.VERCEL_ENV !== 'production') },
  // three/R3F/drei load as a lazy chunk via React.lazy (src/film/GlobeLayer.tsx); no manualChunks needed
  build: { target: 'es2022' },
})
