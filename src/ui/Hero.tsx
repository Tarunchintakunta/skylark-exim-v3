import gsap from 'gsap'
import { useEffect, useRef } from 'react'
import { env } from '../engine/env'
import { setPath } from '../engine/path'
import { frame, useApp } from '../engine/store'
import { onTick } from '../engine/ticker'
import { HeroFrame, bindLoop } from './HeroFrame'

/**
 * The film's hero: fixed while the start chapter is on screen; the loop dissolves into the scrubbed opening shot over
 * the first third of the start chapter, and the copy fades over its last 15%.
 */
export function Hero() {
  const revealed = useApp((s) => s.revealed)
  const path = useApp((s) => s.path)
  const root = useRef<HTMLDivElement>(null)
  const video = useRef<HTMLVideoElement>(null)
  const media = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const m = media.current!
    if (!video.current || env.reduced) return
    const loop = bindLoop(video.current, () => m.style.opacity === '0')
    const stop = onTick(() => {
      // hand-off: the loop dissolves into the scrubbed opening shot over the first third of the start chapter
      const o = frame.index <= 0 ? 1 - Math.min(1, Math.max(0, (frame.local - 0.05) / 0.3)) : 0
      const s = String(o)
      if (m.style.opacity === s) return
      const was = m.style.opacity
      m.style.opacity = s
      if ((was === '0') !== (s === '0')) loop.sync()
    })
    return () => {
      loop.stop()
      stop()
    }
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
      video={video}
      fork="#"
      current={path}
      onFork={(p, e) => {
        e.preventDefault()
        setPath(p, true)
      }}
    />
  )
}
