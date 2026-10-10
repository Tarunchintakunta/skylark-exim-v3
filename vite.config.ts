import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

/** Inline the entry stylesheet (~6 KB gzipped) into index.html: one render-blocking round trip less before first paint. */
function inlineCss(): Plugin {
  return {
    name: 'inline-entry-css',
    apply: 'build',
    enforce: 'post',
    transformIndexHtml: {
      order: 'post',
      handler(html, ctx) {
        if (!ctx.bundle) return html
        return html.replace(/<link rel="stylesheet" crossorigin href="\/(assets\/[^"]+\.css)">/g, (tag, file: string) => {
          const asset = ctx.bundle![file]
          return asset && asset.type === 'asset' ? `<style>${String(asset.source)}</style>` : tag
        })
      },
    },
  }
}

export default defineConfig({
  plugins: [react(), inlineCss()],
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
