import { useEffect, useRef } from 'react'
import type { ChapterDef } from '../config/chapters'
import { frame, useApp } from '../engine/store'
import { onTick, scrollToY } from '../engine/ticker'
import { film } from '../film/controller'

/** Left chapter rail (PRD F6): one tick per chapter; click or keyboard to jump. Re-renders only on chapter change. */
export function Rail({ chapters }: { chapters: ChapterDef[] }) {
  const active = useApp((s) => s.chapter)
  const root = useRef<HTMLElement>(null)

  useEffect(() => {
    let hidden = false
    return onTick(() => {
      if (frame.past !== hidden) {
        hidden = frame.past
        root.current!.style.visibility = hidden ? 'hidden' : 'visible'
        root.current!.style.opacity = hidden ? '0' : '1'
      }
    })
  }, [])

  return (
    <nav className="rail" ref={root} aria-label="Chapters">
      <ol>
        {chapters.map((ch, i) => (
          <li key={ch.id}>
            <button
              className="rail__tick"
              aria-current={active === ch.id ? 'step' : undefined}
              onClick={() => scrollToY(film.top(i) + (i === 0 ? 0 : 2))}
            >
              <span className="rail__label mono">
                {String(i).padStart(2, '0')} · {ch.label}
              </span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}
