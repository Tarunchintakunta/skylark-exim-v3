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
    // not aria-hidden as a whole: the globe inside is a focusable, labelled control; the rest is decorative
    <div className="stage" ref={ref}>
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
            className="stage__layer"
            // no poster loads up front (the hero loop covers the first screen); scrub.ts sets them from data-src after the first scroll
            src={undefined}
            data-src={posterFor(m)!}
            alt=""
            decoding="async"
            fetchPriority="low"
          />
        )
      })}
      <video className="stage__video" muted playsInline preload="auto" disablePictureInPicture tabIndex={-1} aria-hidden="true" />
      <video className="stage__video" muted playsInline preload="auto" disablePictureInPicture tabIndex={-1} aria-hidden="true" />
      <video className="stage__video" muted playsInline preload="auto" disablePictureInPicture tabIndex={-1} aria-hidden="true" />
      <div className="stage__veil" />
      <div className="stage__scrim" />
    </div>
  )
}
