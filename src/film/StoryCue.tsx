import { useEffect, useRef } from 'react'
import { frame } from '../engine/store'
import { onTick } from '../engine/ticker'
import { film } from './controller'

const TOP = 'Scroll to explore'
const NEXT = 'Scroll to continue'
const GLOBE = 'Drag to rotate globe · Click a market · Scroll for products'

/**
 * The film's "scroll on" cue: loud at the top of /story, then back whenever the scroll has sat still for 1.2 s, between
 * two captions, and on the docs and globe chapters, so the page never reads as stuck or finished. Gone once the film has
 * scrolled away. Written straight to the DOM from the tick, like the header's state.
 */
export function StoryCue() {
  const root = useRef<HTMLParagraphElement>(null)
  const label = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    let text = ''
    let cls = ''
    let y = -1
    let still = 0
    return onTick((time) => {
      if (frame.scroll !== y) (y = frame.scroll), (still = time)
      const ch = film.chapters[frame.index]
      const between = !!ch && !ch.captions.some((c) => frame.local >= c.at[0] && frame.local < c.at[1])
      const top = frame.scroll < 80
      const on = !frame.past && (top || time - still > 1.2 || between || ch?.id === 'docs' || ch?.id === 'world')
      const t = top ? TOP : ch?.id === 'world' ? GLOBE : NEXT
      const c = `story-cue mono${on ? ' is-on' : ''}${top ? ' is-top' : ''}${ch?.theme === 'light' ? ' is-light' : ''}`
      if (t !== text) label.current!.textContent = text = t
      if (c !== cls) root.current!.className = cls = c
    })
  }, [])
  return (
    <p className="story-cue mono" ref={root} aria-hidden="true">
      <span ref={label}>{TOP}</span> <span className="story-cue__arrow">↓</span>
    </p>
  )
}
