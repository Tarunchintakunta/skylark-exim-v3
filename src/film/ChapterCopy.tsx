import type { ChapterDef } from '../config/chapters'
import './film.css'

/** Captions are real HTML inside each chapter section (indexable, read in order); captions.ts shows one at a time. */
export function ChapterCopy({ chapter }: { chapter: ChapterDef }) {
  return (
    <>
      {chapter.media.map((m, i) => (
        <p className="sr-only" key={`alt${i}`}>{m.alt}</p>
      ))}
      {chapter.captions.map((c, i) => {
        const Title = i === 0 ? 'h2' : 'h3'
        return (
          <article className="caption" key={i}>
            {c.eyebrow && <p className="caption__eyebrow mono" data-fade>{c.eyebrow}</p>}
            <Title className="caption__title display">{c.title}</Title>
            {c.body && <p className="caption__body" data-fade>{c.body}</p>}
            {c.note && <p className="caption__note mono" data-fade>{c.note}</p>}
            {c.chips && (
              <ul className="chips" aria-label="Species">
                {c.chips.map((chip) => (
                  <li className="chip mono" key={chip} data-fade>{chip}</li>
                ))}
              </ul>
            )}
          </article>
        )
      })}
    </>
  )
}
