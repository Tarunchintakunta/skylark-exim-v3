import type { ChapterDef } from '../config/chapters'
import { DocCards, LabelCard, MarketList } from './Extras'
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
          <article className={`caption${chapter.theme === 'light' ? ' caption--light' : ''}`} key={i}>
            {c.eyebrow && <p className="caption__eyebrow mono" data-fade>{c.eyebrow}</p>}
            <Title className="caption__title display">{c.title}</Title>
            {c.body && <p className="caption__body" data-fade>{c.body}</p>}
            {c.note && <p className="caption__note mono" data-fade>{c.note}</p>}
            {c.extra === 'label-card' && <LabelCard />}
            {c.extra === 'doc-cards' && <DocCards />}
            {c.extra === 'markets' && <MarketList />}
            {c.chips && (
              <p className="caption__list" data-fade>
                <span className="sr-only">Species: </span>
                {c.chips.join(' · ')}
              </p>
            )}
          </article>
        )
      })}
    </>
  )
}
