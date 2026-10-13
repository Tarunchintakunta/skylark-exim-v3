import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { defineConfig, type Connect, type Plugin } from 'vite'
import { clipManifest } from './scripts/clip-manifest'
import { staticHero } from './scripts/static-hero'

/** /story, /quote and /news are their own HTML entries: only /story boots the film. */
function documentRoutes(): Plugin {
  const rewrite = (req: Connect.IncomingMessage) => {
    const raw = req.url ?? '/'
    const cut = raw.search(/[?#]/)
    const path = (cut === -1 ? raw : raw.slice(0, cut)).replace(/\/+$/, '') || '/'
    const tail = cut === -1 ? '' : raw.slice(cut)
    let file: string | null = null
    if (path === '/story') file = '/story.html'
    else if (path === '/quote') file = '/quote.html'
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

// Three builds, so no page shares a chunk: a shared chunk adds a request before the hero paints (LCP budget).
// '' → the homepage (and it empties dist), 'story' → the film, 'documents' → /quote and /news.
const entries = process.env.BUILD_ENTRIES ?? ''
const page = (name: string) => resolve(import.meta.dirname, name)
const INPUTS: Record<string, Record<string, string>> = {
  '': { main: page('index.html') },
  story: { story: page('story.html') },
  documents: { quote: page('quote.html'), news: page('news.html') },
}

export default defineConfig({
  plugins: [clipManifest(), documentRoutes(), react(), staticHero()],
  build: {
    target: 'es2022',
    // the later builds add their pages and must not wipe the homepage
    emptyOutDir: !entries,
    rolldownOptions: {
      input: INPUTS[entries],
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
