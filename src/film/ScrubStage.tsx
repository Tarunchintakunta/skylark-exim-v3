import { useLayoutEffect, useMemo, useRef } from 'react'
import type { ChapterDef } from '../config/chapters'
import { GlobeLayer } from './GlobeLayer'
import { bindStage } from './scrub'
import { posterFor, toSegments } from './segments'
import './stage.css'

/** The one fixed stage: posters under three video decoders (prev, current, next), a veil for cuts and the bottom scrim. */
export function ScrubStage({ chapters }: { chapters: ChapterDef[] }) {
  const segs = useMemo(() => toSegments(chapters), [chapters])
  const ref = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => bindStage(ref.current!, segs), [segs])

  return (
    <div className="stage" ref={ref} aria-hidden="true">
      {segs.map((s, i) => {
        const m = s.media
        if (m.kind === 'gradient') return <div key={i} data-seg={i} className="stage__layer stage__gradient" />
        if (m.kind === 'globe')
          return (
            <div key={i} data-seg={i} className="stage__layer stage__light">
              <GlobeLayer chapters={chapters} />
            </div>
          )
        return (
          <img
            key={i}
            data-seg={i}
            className={m.kind === 'dom' ? 'stage__layer stage__dom' : 'stage__layer'}
            // only the opening poster loads up front; scrub.ts sets the rest from data-src (current + next 2)
            src={i === 0 ? posterFor(m)! : undefined}
            data-src={posterFor(m)!}
            alt=""
            decoding="async"
            fetchPriority={i === 0 ? 'high' : 'low'}
          />
        )
      })}
      <video className="stage__video" muted playsInline preload="auto" disablePictureInPicture tabIndex={-1} />
      <video className="stage__video" muted playsInline preload="auto" disablePictureInPicture tabIndex={-1} />
      <video className="stage__video" muted playsInline preload="auto" disablePictureInPicture tabIndex={-1} />
      <div className="stage__veil" />
      <div className="stage__scrim" />
    </div>
  )
}
