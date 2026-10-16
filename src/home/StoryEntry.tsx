import gsap from 'gsap'
import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type MouseEvent, type PointerEvent } from 'react'
import { flushSync } from 'react-dom'
import { ENTRY_CARDS, type EntryCard } from '../config/storyEntry'
import { env } from '../engine/env'
import { lockScroll, scrollToY, unlockScroll } from '../engine/ticker'
import { cardSrcSet, clipUrl, mediaUrl } from '../film/segments'
import { prefetchStory } from './prefetch'
import { Orbit } from './Orbit'
import './story-entry.css'

type Id = EntryCard['id']
/** phones get the 810×1440 portrait crops (CROP_X in config/chapters.ts) */
const PHONE = '(max-width: 768px)'
const phone = () => matchMedia(PHONE).matches
/** grow / shrink: ~650 ms, a decelerating ease with no overshoot */
const GROW = { duration: 0.65, ease: 'expo.out' } as const
const SIZES: Record<Id, string> = { wild: '58vw', farmed: '41vw', world: '41vw' }
const FOCUSABLE = 'a[href], button:not([disabled])'

/** The card's still: the clip's first frame, the portrait crop on phones. Lazy: nothing loads before the section is near. */
function Still({ card, open }: { card: EntryCard; open: boolean }) {
  const id = card.clip!
  return (
    <picture>
      <source media={PHONE} type="image/avif" srcSet={mediaUrl(`${id}_m.avif`)} />
      <source media={PHONE} type="image/webp" srcSet={mediaUrl(`${id}_m.webp`)} />
      <source type="image/avif" srcSet={cardSrcSet(id, 'avif')} sizes={open ? '100vw' : SIZES[card.id]} />
      <img
        className="se-media__still"
        src={mediaUrl(`${id}_960.webp`)}
        srcSet={cardSrcSet(id, 'webp')}
        sizes={open ? '100vw' : SIZES[card.id]}
        alt=""
        loading="lazy"
        decoding="async"
      />
    </picture>
  )
}

/** A muted loop, src set only once it should play (hover, or in view on touch), then faded in over the still. */
function Loop({ src, play, className }: { src: string | null; play: boolean; className: string }) {
  const v = useRef<HTMLVideoElement>(null)
  useEffect(() => {
    const el = v.current!
    if (!src || !play) return void el.pause()
    if (el.getAttribute('src') !== src) el.src = src
    el.play().catch(() => {})
  }, [src, play])
  return <video ref={v} className={className} muted loop playsInline preload="none" aria-hidden="true" onPlaying={(e) => e.currentTarget.classList.add('is-on')} />
}

function Card({ card, open, onOpen, onClose }: { card: EntryCard; open: boolean; onOpen: (el: HTMLElement) => void; onClose: () => void }) {
  const root = useRef<HTMLDivElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState(false)
  const [inView, setInView] = useState(false)
  const path = card.id === 'wild' ? 'ocean' : card.id === 'farmed' ? 'pond' : null
  const loops = !!card.clip && !env.reduced

  // touch has no hover: the loop plays while the card is half on screen
  useEffect(() => {
    if (!loops || env.fine) return
    const io = new IntersectionObserver(([e]) => setInView(e.isIntersecting), { threshold: 0.5 })
    io.observe(root.current!)
    return () => io.disconnect()
  }, [loops])

  const warm = () => {
    setHover(true)
    if (path) prefetchStory(path)
  }

  // parallax: the widgets drift against the cursor, each by its own depth (transform only)
  const parallax = (e: PointerEvent) => {
    if (!open || env.reduced || e.pointerType !== 'mouse') return
    const [dx, dy] = [e.clientX / innerWidth - 0.5, e.clientY / innerHeight - 0.5]
    panel.current!.querySelectorAll<HTMLElement>('.se-widget').forEach((w, i) => {
      const depth = 10 + (i % 3) * 8
      gsap.to(w, { x: -dx * depth, y: -dy * depth, duration: 0.8, ease: 'power3.out', overwrite: 'auto' })
    })
  }

  // focus stays inside while open; Esc closes
  const keys = (e: KeyboardEvent) => {
    if (e.key === 'Escape') return onClose()
    if (e.key !== 'Tab') return
    const f = [...panel.current!.querySelectorAll<HTMLElement>(FOCUSABLE)]
    const [first, last] = [f[0], f[f.length - 1]]
    if (e.shiftKey && document.activeElement === first) (e.preventDefault(), last.focus())
    else if (!e.shiftKey && document.activeElement === last) (e.preventDefault(), first.focus())
  }
  // a click on the open card's empty space (not a widget, the copy or a button) closes it, as a click outside would
  const backdrop = (e: MouseEvent) => e.target === e.currentTarget && !phone() && onClose()

  // phones: drag the sheet down from its top to close it
  useEffect(() => {
    const el = panel.current!
    if (!open || !env.coarse) return
    let y0 = -1
    let dy = 0
    const start = (e: TouchEvent) => void (y0 = el.scrollTop <= 0 ? e.touches[0].clientY : -1)
    const move = (e: TouchEvent) => {
      if (y0 < 0) return
      dy = Math.max(0, e.touches[0].clientY - y0)
      if (dy > 0) e.preventDefault()
      gsap.set(root.current, { y: dy * 0.7 })
    }
    const end = () => {
      if (y0 < 0) return
      if (dy > 110) onClose()
      else gsap.to(root.current, { y: 0, duration: 0.35, ease: 'power3.out' })
      y0 = -1
      dy = 0
    }
    el.addEventListener('touchstart', start, { passive: true })
    el.addEventListener('touchmove', move, { passive: false })
    el.addEventListener('touchend', end)
    return () => (el.removeEventListener('touchstart', start), el.removeEventListener('touchmove', move), el.removeEventListener('touchend', end))
  }, [open, onClose])

  const titleId = `se-${card.id}-title`
  return (
    <div
      ref={root}
      className={`se-card se-card--${card.id}${open ? ' is-open' : ''}${card.clip ? '' : ' se-card--dark'}`}
      data-card={card.id}
      onPointerEnter={(e) => e.pointerType === 'mouse' && warm()}
      onPointerLeave={() => setHover(false)}
      onFocus={() => path && prefetchStory(path)}
      onPointerMove={parallax}
    >
      <div className="se-media" aria-hidden="true">
        {card.clip ? (
          <>
            <Still card={card} open={open} />
            <Loop className="se-media__loop" src={loops ? clipUrl(card.clip, phone() ? 'm' : 960) : null} play={hover || inView || open} />
            {/* the full-quality loop, only once the card is open */}
            <Loop className="se-media__loop" src={loops && open && !phone() ? clipUrl(card.clip) : null} play={open} />
          </>
        ) : (
          <Orbit className="se-orbit" />
        )}
        <span className="se-media__scrim" />
      </div>

      <button className="se-hit" type="button" aria-expanded={open} aria-controls={`se-${card.id}-panel`} onClick={(e) => onOpen(e.currentTarget)}>
        <span className="se-tag mono">{card.tag}</span>
        <span className="se-title display">{card.title}</span>
        {card.clip && (
          <span className="se-cta">
            {card.cta} <span aria-hidden="true">→</span>
          </span>
        )}
        {!card.clip && <span className="se-markets mono">{card.widgets.map((w) => w.value).join(' · ')}</span>}
      </button>
      {!card.clip && (
        <a className="se-cta se-cta--link" href={card.start.href}>
          {card.cta} <span aria-hidden="true">→</span>
        </a>
      )}

      <div
        ref={panel}
        id={`se-${card.id}-panel`}
        className="se-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        hidden={!open}
        onKeyDown={keys}
        onClick={backdrop}
        data-lenis-prevent
      >
        <ul className="se-widgets" onClick={backdrop}>
          {card.widgets.map((w) => (
            <li key={w.label} className="se-widget">
              <span className="se-widget__label mono">{w.label}</span>
              <span className="se-widget__value">{w.value}</span>
            </li>
          ))}
        </ul>
        <div className="se-center">
          <p className="se-tag mono">{card.tag}</p>
          <h3 id={titleId} className="se-heading display">{card.heading}</h3>
          <p className="se-sub">{card.sub}</p>
          <div className="se-actions">
            <a className="se-btn se-btn--primary" href={card.start.href}>
              {card.start.label} <span aria-hidden="true">→</span>
            </a>
            <button className="se-btn" type="button" onClick={onClose}>Back</button>
          </div>
        </div>
        <button className="se-close" type="button" aria-label="Close" onClick={onClose}>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>
    </div>
  )
}

/**
 * Story Entry (#268): three bento cards after the hero. A card grows from its cell to the full viewport (GSAP, ~650 ms),
 * then its facts float in; Back, Esc, the close button or a click on its empty space shrink it back to the cell, and
 * the page is where it was. Reduced motion: a crossfade, no growth and no float.
 */
export function StoryEntry({ initial }: { initial?: Id }) {
  const [open, setOpen] = useState<Id | null>(null)
  const from = useRef<{ trigger: HTMLElement | null; y: number }>({ trigger: null, y: 0 })
  const cards = useRef<HTMLUListElement>(null)

  const card = (id: Id) => cards.current!.querySelector<HTMLElement>(`[data-card="${id}"]`)!

  const openCard = (id: Id, trigger: HTMLElement | null) => {
    from.current = { trigger, y: scrollY }
    if (env.coarse) document.documentElement.classList.add('is-locked')
    else lockScroll()
    setOpen(id)
  }

  const closeCard = () => {
    if (!open) return
    const el = card(open)
    const cell = el.parentElement!.getBoundingClientRect()
    const done = () => {
      // back in the cell before the inline sizes go, so no frame shows the card full screen without them
      flushSync(() => setOpen(null))
      gsap.set([el, ...el.querySelectorAll('.se-widget, .se-center, .se-close')], { clearProps: 'all' })
      if (env.coarse) document.documentElement.classList.remove('is-locked')
      else unlockScroll()
      scrollToY(from.current.y, true)
      from.current.trigger?.focus({ preventScroll: true })
    }
    const tl = gsap.timeline({ onComplete: done })
    tl.to(el.querySelectorAll('.se-widget, .se-center, .se-close'), { autoAlpha: 0, duration: 0.18, ease: 'power1.out' })
    if (env.reduced) tl.to(el, { autoAlpha: 0, duration: 0.3 })
    else tl.to(el, { top: cell.top, left: cell.left, width: cell.width, height: cell.height, y: 0, borderRadius: getComputedStyle(el.parentElement!).borderRadius, ...GROW }, '<0.05')
  }

  // grow from the cell, then float the facts in, 60 ms apart
  useLayoutEffect(() => {
    if (!open) return
    const el = card(open)
    const cell = el.parentElement!.getBoundingClientRect()
    const radius = getComputedStyle(el.parentElement!).borderRadius
    const items = el.querySelectorAll('.se-widget')
    const tl = gsap.timeline()
    if (env.reduced) {
      tl.fromTo(el, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3 })
    } else {
      tl.fromTo(el, { top: cell.top, left: cell.left, width: cell.width, height: cell.height, borderRadius: radius }, { top: 0, left: 0, width: innerWidth, height: innerHeight, borderRadius: 0, ...GROW })
      tl.fromTo(el.querySelector('.se-center'), { autoAlpha: 0, y: 16 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'expo.out' }, 0.32)
      tl.fromTo(items, { autoAlpha: 0, y: 28 }, { autoAlpha: 1, y: 0, duration: 0.7, ease: 'expo.out', stagger: 0.06 }, 0.4)
      // opacity only: the close button takes focus at once
      tl.fromTo(el.querySelector('.se-close'), { opacity: 0 }, { opacity: 1, duration: 0.3 }, 0.45)
    }
    el.querySelector<HTMLElement>('.se-close')!.focus({ preventScroll: true })
    return () => void tl.kill()
  }, [open])

  // design review: ?open=<id> starts with that card open
  useEffect(() => {
    if (initial) openCard(initial, null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <section id="story-entry" className="se" aria-labelledby="se-title">
      <h2 id="se-title" className="sr-only">Choose a story</h2>
      <ul className="se-grid" ref={cards}>
        {ENTRY_CARDS.map((c) => (
          <li key={c.id} className={`se-cell se-cell--${c.id}`}>
            <Card card={c} open={open === c.id} onOpen={(t) => openCard(c.id, t)} onClose={closeCard} />
          </li>
        ))}
      </ul>
    </section>
  )
}
