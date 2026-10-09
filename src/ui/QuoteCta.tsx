import { start } from '../config/content'
import { goTo } from '../engine/path'
import { useApp } from '../engine/store'

/** Sticky "Request export quote" (PRD F7): visible everywhere after the loader. Bottom bar on mobile. */
export function QuoteCta() {
  const ready = useApp((s) => s.ready)
  return (
    <a
      className={`quote-cta btn btn--solid${ready ? ' is-ready' : ''}`}
      href="#quote"
      onClick={(e) => {
        e.preventDefault()
        goTo('quote')
      }}
    >
      {start.cta}
    </a>
  )
}
