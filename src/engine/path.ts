import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { film } from '../film/controller'
import { store, type Path } from './store'
import { scrollToY } from './ticker'

/** Switch path. The chapter list below the fork swaps; `jump` lands on the new path's first chapter. */
export function setPath(path: Path, jump = false) {
  if (store.getState().path !== path) {
    store.setState({ path })
    history.replaceState(null, '', `#${path}`)
    // the page height changed: rebuild section triggers once, off the critical path
    const idle = 'requestIdleCallback' in window ? requestIdleCallback : (fn: () => void) => setTimeout(fn, 100)
    idle(() => ScrollTrigger.refresh())
  }
  // wait for React to commit the new chapter list and the controller to re-measure
  if (jump) requestAnimationFrame(() => requestAnimationFrame(() => scrollToY(film.top(1), true)))
}

export function goTo(id: string) {
  const el = document.getElementById(id)
  if (el) scrollToY(el.getBoundingClientRect().top + window.scrollY)
}
