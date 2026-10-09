import { useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import type { ChapterDef } from '../config/chapters'
import { useApp } from '../engine/store'
import { GlobeLayer } from './GlobeLayer'
import { bindStage, preloadPosters } from './scrub'
import { posterFor, toSegments } from './segments'
import './stage.css'

/** The one fixed stage: posters under two video decoders, a veil for cuts and the bottom scrim. */
export function ScrubStage({ chapters }: { chapters: ChapterDef[] }) {
  const segs = useMemo(() => toSegments(chapters), [chapters])
  const ready = useApp((s) => s.ready)
  const ref = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => bindStage(ref.current!, segs), [segs])
  useEffect(() => {
    if (ready) preloadPosters()
  }, [ready, segs])

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
            className={`stage__layer${m.kind === 'dom' ? ' stage__blur' : ''}`}
            // only the opening poster loads before the loader finishes; the rest right after
            src={ready || i === 0 ? posterFor(m)! : undefined}
            alt=""
            decoding="async"
            fetchPriority={i === 0 ? 'high' : 'low'}
          />
        )
      })}
      <video className="stage__video" muted playsInline preload="auto" disablePictureInPicture tabIndex={-1} />
      <video className="stage__video" muted playsInline preload="auto" disablePictureInPicture tabIndex={-1} />
      {__PREVIEW__ &&
        segs.map((s, i) =>
          'awaiting' in s.media ? (
            <span key={`ph${i}`} data-ph={i} className="stage__ph mono">
              Placeholder · awaiting {s.media.awaiting}
            </span>
          ) : null,
        )}
      <div className="stage__veil" />
      <div className="stage__scrim" />
    </div>
  )
}
