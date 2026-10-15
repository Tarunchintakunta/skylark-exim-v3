import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useEffect, useRef, useState, type ReactNode, type Ref } from 'react'
import { env } from '../engine/env'
import { onTick } from '../engine/ticker'
import { Sequence, createStage } from '../film/sequence'
import './sequence.css'

/**
 * A sticky canvas that scrubs an image sequence with the scroll (#249). The frames, their decode and their memory are
 * the engine's business (src/film/sequence.ts, #264): a worker keeps each frame's bytes and decodes on demand, frames
 * arrive coarse first, and the decoded bitmaps are capped, so a long set never holds hundreds of megabytes of bitmaps.
 * This component owns the markup, the ScrollTrigger that turns scroll into a position, and the poster that stands in
 * until the first frame has painted (the poster alone with reduced motion).
 */
export type FrameSet = 1920 | 'm'

export interface ScrollSequenceProps {
  src: (set: FrameSet, index: number) => string
  frames: Record<FrameSet, number>
  /** resolved before the first frame URL is built (the hero waits for the AVIF probe) */
  wait?: Promise<unknown>
  /** the first frame as an image, shown until the canvas has painted and the only thing reduced motion gets */
  poster: ReactNode
  length?: string
  className?: string
  sectionRef?: Ref<HTMLElement>
  children?: ReactNode
}

/** phones held upright get the 810×1440 portrait crop, as the clips do (src/config/hero.ts PORTRAIT) */
const PORTRAIT = '(orientation: portrait) and (max-width: 819px), (orientation: portrait) and (pointer: coarse)'
const pickSet = (): FrameSet => (matchMedia(PORTRAIT).matches ? 'm' : 1920)

export function ScrollSequence({ src, frames, wait, poster, length = '300vh', className = '', sectionRef, children }: ScrollSequenceProps) {
  const [set, setSet] = useState<FrameSet>(pickSet)
  const [painted, setPainted] = useState(false)
  const section = useRef<HTMLElement | null>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const still = env.reduced

  useEffect(() => {
    const mq = matchMedia(PORTRAIT)
    const change = () => setSet(pickSet())
    mq.addEventListener('change', change)
    return () => mq.removeEventListener('change', change)
  }, [])

  useEffect(() => {
    if (still) return
    const el = section.current!
    const cv = canvas.current!
    let seq: Sequence | null = null
    const stage = createStage(cv)
    let at = 0

    const ro = new ResizeObserver(stage.resize)
    ro.observe(cv)
    stage.resize()

    let first = true
    const stopTick = onTick(() => {
      if (!seq) return
      const i = stage.draw({ seq, at })
      if (i < 0) return
      if (first) {
        first = false
        setPainted(true)
      }
      el.dataset.frame = String(i)
    })

    const st = ScrollTrigger.create({
      trigger: el,
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => (at = self.progress),
    })

    // the set starts loading as it comes near, from the frame on screen outwards
    let near = false
    let waited = !wait
    const start = () => {
      if (!near || !waited || seq) return
      seq = new Sequence({ id: `${className || 'seq'}-${set}`, frames: frames[set], url: (i) => src(set, i) })
      seq.pump(seq.index(at))
    }
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return
        io.disconnect()
        near = true
        start()
      },
      { rootMargin: '100% 0px' },
    )
    io.observe(el)
    void (wait ?? Promise.resolve()).then(() => {
      waited = true
      start()
    })

    return () => {
      io.disconnect()
      ro.disconnect()
      st.kill()
      stopTick()
      seq?.destroy()
      setPainted(false)
    }
  }, [set, still])

  const setRef = (node: HTMLElement | null) => {
    section.current = node
    if (typeof sectionRef === 'function') sectionRef(node)
    else if (sectionRef) (sectionRef as { current: HTMLElement | null }).current = node
  }

  return (
    <section ref={setRef} className={`seq ${className}`} style={{ height: still ? '100svh' : length }} data-set={set} data-painted={painted || undefined}>
      <div className="seq__stage">
        {poster}
        {!still && <canvas className="seq__canvas" ref={canvas} aria-hidden="true" />}
        {children}
      </div>
    </section>
  )
}
