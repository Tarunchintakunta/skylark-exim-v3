import { useStore } from 'zustand'
import { createStore } from 'zustand/vanilla'

export type Path = 'ocean' | 'pond'

/** React-visible state: changes only on chapter change, path change or load. */
export interface AppState {
  path: Path
  ready: boolean
  /** id of the chapter currently on screen */
  chapter: string
}

const hashPath = (): Path => (location.hash === '#pond' ? 'pond' : 'ocean')

export const store = createStore<AppState>(() => ({ path: hashPath(), ready: false, chapter: 'start' }))
export const useApp = <T,>(sel: (s: AppState) => T) => useStore(store, sel)

/** Per-frame values. Mutable on purpose: written by the ticker, read by ticker callbacks. Never put these in React state. */
export const frame = {
  /** smoothed scroll position in px */
  scroll: 0,
  /** +1 scrolling down, -1 up */
  dir: 1,
  /** index into the active chapter list */
  index: 0,
  /** 0..1 progress inside the active chapter */
  local: 0,
  /** true once the whole film has scrolled away (business sections on screen) */
  past: false,
}
