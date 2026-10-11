import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { staticHero } from './scripts/static-hero'

export default defineConfig({
  plugins: [react(), staticHero()],
  // three/R3F/drei load as a lazy chunk via React.lazy (src/film/GlobeLayer.tsx); no manualChunks needed
  build: {
    target: 'es2022',
    rolldownOptions: {
      output: {
        // the lazy globe pulls three.js + R3F; give each its own chunk so none is ~1 MB (both still load only with the globe)
        advancedChunks: {
          // keep shared deps (react, zustand) out of these groups so the boot bundle never needs them
          includeDependenciesRecursively: false,
          groups: [
            { name: 'three', test: /node_modules[\\/]three[\\/]/ },
            { name: 'r3f', test: /node_modules[\\/]@react-three[\\/]/ },
          ],
        },
      },
    },
  },
})
