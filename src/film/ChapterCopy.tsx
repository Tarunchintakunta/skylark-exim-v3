import type { ChapterDef } from '../config/chapters'
import { DocCards, LabelCard, MarketList } from './Extras'
import './film.css'

/** Chapters whose copy sits in a right-hand column instead of bottom-left, for editorial rhythm (redesign §6). */
const RIGHT = new Set(['o3', 'p2', 'process', 'port'])

/** Captions are real HTML inside each chapter section (indexable, read in order); captions.ts shows one at a time. */
export function ChapterCopy({ chapter }: { chapter: ChapterDef }) {
  const place = RIGHT.has(chapter.id) ? ' caption--right' : ''
  return (
    <>
      {chapter.media.map((m, i) => (
        <p className="sr-only" key={`alt${i}`}>{m.alt}</p>
      ))}
      {chapter.captions.map((c, i) => {
        const Title = i === 0 ? 'h2' : 'h3'
        return (
          // keyed by content, not index: after a path switch the same chapter can gain or lose the bridge caption, and
          // SplitText.revert() in bindCaptions would write the old title back into a reused node (#210)
          <article className={`caption${place}${chapter.theme === 'light' ? ' caption--light' : ''}`} key={`${i}:${c.title}`}>
            {c.eyebrow && <Eyebrow text={c.eyebrow} />}
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

/** "The Ocean · 01" → a small serif numeral beside the chapter name (Mont-Fort chapter style). */
function Eyebrow({ text }: { text: string }) {
  const m = text.match(/^(.*?)\s*·\s*(\d{2})$/)
  return (
    <p className="caption__eyebrow mono" data-fade>
      {m ? (
        <>
          <span className="caption__num">{m[2]}</span>
          {m[1]}
        </>
      ) : (
        text
      )}
    </p>
  )
}
