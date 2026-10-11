import { start } from '../config/content'

/** Last band on the homepage, after the story sections and before the contact footer. */
export function Close() {
  return (
    <section className="section theme-light close" aria-labelledby="close-title">
      <p id="close-title" className="close__line">{start.title}</p>
      <div className="close__actions">
        <a className="btn btn--solid" href="/quote">Request export quote</a>
        <a className="close__updates" href="/news">Latest updates</a>
      </div>
    </section>
  )
}
