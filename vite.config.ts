import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { defineConfig, type Connect, type Plugin } from 'vite'

/** /quote and /news are their own HTML entries so they never boot the film. */
function documentRoutes(): Plugin {
  const rewrite = (req: Connect.IncomingMessage) => {
    const raw = req.url ?? '/'
    const cut = raw.search(/[?#]/)
    const path = (cut === -1 ? raw : raw.slice(0, cut)).replace(/\/+$/, '') || '/'
    const tail = cut === -1 ? '' : raw.slice(cut)
    let file: string | null = null
    if (path === '/quote') file = '/quote.html'
    else if (path === '/news' || path.startsWith('/news/')) file = '/news.html'
    if (file) req.url = file + tail
  }
  // Register inside the hook so this runs before Vite's htmlFallback.
  const attach = (server: { middlewares: Connect.Server }) => {
    server.middlewares.use((req, _res, next) => {
      rewrite(req)
      next()
    })
  }
  return {
    name: 'document-routes',
    configureServer: attach,
    configurePreviewServer: attach,
  }
}

export default defineConfig({
  plugins: [documentRoutes(), react()],
  build: {
    target: 'es2022',
    rolldownOptions: {
      input: {
        main: resolve(import.meta.dirname, 'index.html'),
        quote: resolve(import.meta.dirname, 'quote.html'),
        news: resolve(import.meta.dirname, 'news.html'),
      },
      output: {
        advancedChunks: {
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
