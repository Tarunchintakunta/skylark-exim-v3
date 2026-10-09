import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // three/R3F/drei load as a lazy chunk via React.lazy (src/film/GlobeLayer.tsx); no manualChunks needed
  build: { target: 'es2022' },
})
