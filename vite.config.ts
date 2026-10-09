import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  build: {
    target: 'es2022',
    rollupOptions: {
      output: {
        // three + R3F stay in their own lazy chunk (TRD §9: initial JS ≤ 250 KB gzip)
        manualChunks(id) {
          if (/node_modules\/(three|@react-three)/.test(id)) return 'three'
        },
      },
    },
  },
})
