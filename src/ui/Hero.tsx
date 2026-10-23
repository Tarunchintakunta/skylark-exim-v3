import gsap from 'gsap'
import { useEffect, useRef } from 'react'
import { setPath } from '../engine/path'
import { frame, useApp } from '../engine/store'
import { onTick } from '../engine/ticker'
import { HeroFrame } from './HeroFrame'

/**
 * The film's hero: fixed while the start chapter is on screen; its still first frame dissolves into the scrubbed
 * opening shot (the same frame) over the first tenth of the start chapter, and the copy fades over its last 15%.
 */
export function Hero() {
  const revealed = useApp((s) => s.revealed)
  const path = useApp((s) => s.path)
  const root = useRef<HTMLDivElement>(null)
  const media = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const m = media.current!
    return onTick(() => {
      // hand-off: the still dissolves into the scrubbed opening shot, which starts on the same first frame
      const s = String(frame.index <= 0 ? 1 - Math.min(1, Math.max(0, (frame.local - 0.02) / 0.08)) : 0)
      if (m.style.opacity !== s) m.style.opacity = s
    })
  }, [])

  useEffect(() => {
    if (!revealed) return
    const el = root.current!
    // no intro animation: the same copy is already on screen from the HTML (#207), above the loader
    gsap.set(el, { autoAlpha: 1 })
    let op = -1
    return onTick(() => {
      const o = frame.index <= 0 ? 1 - Math.min(1, Math.max(0, (frame.local - 0.85) / 0.15)) : 0
      if (o === op) return
      op = o
      el.style.opacity = String(o)
      el.style.visibility = o > 0 ? 'visible' : 'hidden'
    })
  }, [revealed])

  return (
    <HeroFrame
      root={root}
      media={media}
      fork="#"
      current={path}
      onFork={(p, e) => {
        e.preventDefault()
        setPath(p, true)
      }}
    />
  )
}
