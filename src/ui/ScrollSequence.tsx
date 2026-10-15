import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useEffect, useRef, useState, type ReactNode, type Ref } from 'react'
import { env } from '../engine/env'
import { onTick } from '../engine/ticker'
import './sequence.css'

export type FrameSet = 'desktop' | 'mobile'

export interface ScrollSequenceProps {
  src: (set: FrameSet, index: number) => string
  frames: Record<FrameSet, number>
  length?: string
  className?: string
  sectionRef?: Ref<HTMLElement>
  alt?: string
  children?: ReactNode
}

const PORTRAIT = '(orientation: portrait)'
const KEY_STEP = 8
const PARALLEL = 6
const DPR_CAP = 2

const pickSet = (): FrameSet => (matchMedia(PORTRAIT).matches ? 'mobile' : 'desktop')

export function frameOrder(n: number) {
  const all = [...Array(n).keys()]
  return { keys: all.filter((i) => i % KEY_STEP === 0), gaps: all.filter((i) => i % KEY_STEP !== 0) }
}

export function nearestLoaded(frames: (ImageBitmap | undefined)[], target: number) {
  for (let d = 0; d < frames.length; d++) {
    if (frames[target - d]) return target - d
    if (frames[target + d]) return target + d
  }
  return -1
}

async function run(list: number[], load: (i: number) => Promise<void>) {
  let next = 0
  await Promise.all(
    Array.from({ length: PARALLEL }, async () => {
      while (next < list.length) await load(list[next++]).catch(() => {})
    }),
  )
}

const interacted = () =>
  new Promise<void>((done) => {
    const go = () => {
      for (const e of ['wheel', 'touchstart', 'keydown', 'scroll']) removeEventListener(e, go)
      clearTimeout(t)
      done()
    }
    for (const e of ['wheel', 'touchstart', 'keydown', 'scroll']) addEventListener(e, go, { passive: true, once: true })
    const t = setTimeout(go, 3000)
  })

export function ScrollSequence({ src, frames, length = '300vh', className = '', sectionRef, alt = '', children }: ScrollSequenceProps) {
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
    const ctx = cv.getContext('2d', { alpha: false })!
    const n = frames[set]
    const bitmaps: (ImageBitmap | undefined)[] = Array(n)
    const abort = new AbortController()
    let target = 0
    let shown = -1
    let dirty = true

    const load = async (i: number) => {
      const res = await fetch(src(set, i), { signal: abort.signal, priority: i === 0 ? 'high' : 'low' } as RequestInit)
      if (!res.ok) return
      bitmaps[i] = await createImageBitmap(await res.blob())
      if (Math.abs(i - target) < Math.abs(shown - target) || shown < 0) dirty = true
    }

    const size = () => {
      const dpr = Math.min(devicePixelRatio || 1, DPR_CAP)
      const w = Math.round(cv.clientWidth * dpr)
      const h = Math.round(cv.clientHeight * dpr)
      if (cv.width !== w || cv.height !== h) {
        cv.width = w
        cv.height = h
        dirty = true
      }
    }
    const ro = new ResizeObserver(size)
    ro.observe(cv)
    size()

    const stopTick = onTick(() => {
      const i = nearestLoaded(bitmaps, target)
      if (i < 0 || (i === shown && !dirty)) return
      const bmp = bitmaps[i]!
      const s = Math.max(cv.width / bmp.width, cv.height / bmp.height)
      const w = bmp.width * s
      const h = bmp.height * s
      ctx.drawImage(bmp, (cv.width - w) / 2, (cv.height - h) / 2, w, h)
      if (shown < 0) setPainted(true)
      shown = i
      el.dataset.frame = String(i)
      dirty = false
    })

    const st = ScrollTrigger.create({
      trigger: el,
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => {
        target = Math.round(self.progress * (n - 1))
      },
    })

    const { keys, gaps } = frameOrder(n)
    const start = () =>
      run(keys, load)
        .then(interacted)
        .then(() => {
          if (!abort.signal.aborted) return run(gaps, load)
        })
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return
        io.disconnect()
        void start()
      },
      { rootMargin: '100% 0px' },
    )
    io.observe(el)

    return () => {
      abort.abort()
      io.disconnect()
      ro.disconnect()
      st.kill()
      stopTick()
      bitmaps.forEach((b) => b?.close())
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
        <img className="seq__poster" src={src(set, 0)} alt={alt} width={set === 'mobile' ? 1080 : 1920} height={set === 'mobile' ? 1920 : 1080} decoding="async" />
        {!still && <canvas className="seq__canvas" ref={canvas} aria-hidden="true" />}
        {children}
      </div>
    </section>
  )
}
