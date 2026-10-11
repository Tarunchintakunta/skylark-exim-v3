import { useEffect } from 'react'
import { newsPost } from '../content/news'
import { PageFooter } from '../ui/PageFooter'
import { PageHeader } from '../ui/PageHeader'
import { NewsPage } from './NewsPage'
import { QuotePage } from './QuotePage'

const ORIGIN = 'https://skylarkexim.com'

export type DocRoute = { name: 'quote' } | { name: 'news' } | { name: 'article'; slug: string }

export function parseDocRoute(pathname = location.pathname): DocRoute {
  const path = pathname.replace(/\.html$/, '').replace(/\/+$/, '') || '/'
  if (path === '/quote') return { name: 'quote' }
  const article = path.match(/^\/news\/([^/]+)$/)
  if (article) return { name: 'article', slug: decodeURIComponent(article[1]) }
  return { name: 'news' }
}

function usePageMeta(title: string, description: string, path: string) {
  useEffect(() => {
    document.title = title
    document.querySelector('meta[name="description"]')?.setAttribute('content', description)
    document.querySelector('link[rel="canonical"]')?.setAttribute('href', `${ORIGIN}${path}`)
  }, [title, description, path])
}

/** /quote, /news, and /news/:slug. The film app stays on index.html. */
export function DocumentApp() {
  const route = parseDocRoute()
  const post = route.name === 'article' ? newsPost(route.slug) : undefined
  const title = route.name === 'quote'
    ? 'Request an export quote | Skylark Exim'
    : route.name === 'article'
      ? post ? `${post.title} | Skylark Exim` : 'Update not found | Skylark Exim'
      : 'News & updates | Skylark Exim'
  const description = route.name === 'quote'
    ? 'Request an export quote from Skylark Exim in Sheela Nagar, Visakhapatnam. Tell us the species, the form, and whether you need it raw fresh, chilled or frozen.'
    : post?.summary ?? 'News and updates from Skylark Exim, the seafood exporter in Visakhapatnam.'
  const path = route.name === 'quote' ? '/quote' : route.name === 'article' ? `/news/${route.slug}` : '/news'
  usePageMeta(title, description, path)

  return (
    <div className="doc">
      <PageHeader current={route.name === 'quote' ? 'quote' : 'news'} />
      {route.name === 'quote' ? <QuotePage /> : <NewsPage slug={route.name === 'article' ? route.slug : undefined} />}
      <PageFooter />
    </div>
  )
}
