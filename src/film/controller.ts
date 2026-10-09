import type { ChapterDef } from '../config/chapters'
import { env } from '../engine/env'
import { frame, store } from '../engine/store'
import { onTick } from '../engine/ticker'
import { bindCaptions, updateCaptions } from './captions'

/**
 * Film controller: maps the scroll position onto (chapter index, local progress).
 * Layout is read only in measure() (mount, resize, path switch), never in the tick.
 */
let chapters: ChapterDef[] = []
let els: HTMLElement[] = []
let tops: number[] = []
let lens: number[] = []
let vh = innerHeight
/** scroll position where the film has fully left the screen */
let filmEnd = Infinity

export const film = {
  get chapters() { return chapters },
  top: (i: number) => tops[i] ?? 0,
  get end() { return filmEnd },
}

export function setChapters(list: ChapterDef[], elements: HTMLElement[]) {
  chapters = list
  els = elements
  measure()
  bindCaptions(els)
  frame.index = -1
}

export function measure() {
  if (!els.length) return
  vh = innerHeight
  const y = window.scrollY
  tops = els.map((el) => el.getBoundingClientRect().top + y)
  const heights = els.map((el) => el.offsetHeight)
  // the last chapter (globe) finishes one viewport early so the next section can slide over it
  lens = heights.map((h, i) => (i === heights.length - 1 ? Math.max(1, h - vh) : h))
  filmEnd = tops[tops.length - 1] + heights[heights.length - 1]
}

let rt = 0
addEventListener('resize', () => {
  clearTimeout(rt)
  rt = window.setTimeout(measure, env.coarse ? 300 : 120)
})

onTick(() => {
  const n = tops.length
  if (!n) return
  const y = frame.scroll
  let i = Math.max(frame.index, 0)
  while (i < n - 1 && y >= tops[i + 1]) i++
  while (i > 0 && y < tops[i]) i--
  frame.local = Math.min(1, Math.max(0, (y - tops[i]) / lens[i]))
  frame.past = y >= filmEnd
  if (i !== frame.index) {
    frame.index = i
    store.setState({ chapter: chapters[i].id })
  }
  updateCaptions(chapters[i], i, frame.local)
}, -10)
