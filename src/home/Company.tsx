import { useEffect, useRef } from 'react'
import { ABOUT, HOME } from '../config/content'
import { NEWS, formatNewsDate } from '../content/news'
import { bindReveals } from '../sections/reveal'

/** About in short (the lead paragraph and the partners), and the latest news item, or a quiet "coming soon". */
export function Company() {
  const root = useRef<HTMLElement>(null)
  useEffect(() => bindReveals(root.current!), [])
  const latest = NEWS[0]
  return (
    <section id="about" className="section theme-light home-company" ref={root} aria-labelledby="about-title">
      <div className="home-company__about">
        <p className="eyebrow mono" data-reveal>About</p>
        <h2 id="about-title" className="section__title" data-reveal>{ABOUT.title}</h2>
        <p className="about__lead" data-reveal>{ABOUT.company[0]}</p>
        <p className="home-company__partners" data-reveal>
          <span className="mono">Managing partners</span> {ABOUT.partners.map((p) => p.name).join(' · ')}
        </p>
      </div>
      <aside className="home-news" aria-labelledby="news-title" data-reveal>
        <p className="eyebrow mono">News</p>
        <h2 id="news-title" className="home-news__title display">{HOME.news.title}</h2>
        {latest ? (
          <a className="home-news__item" href={`/news/${latest.slug}`}>
            <time className="mono" dateTime={latest.date}>{formatNewsDate(latest.date)}</time>
            <span className="home-news__item-title">{latest.title}</span>
            <span className="home-news__summary">{latest.summary}</span>
          </a>
        ) : (
          <p className="home-news__empty">{HOME.news.empty}</p>
        )}
        <a className="home-news__all" href="/news">
          {HOME.news.all} <span aria-hidden="true">→</span>
        </a>
      </aside>
    </section>
  )
}
