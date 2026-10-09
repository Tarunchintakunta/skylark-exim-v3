import { film } from '../film/controller'
import { store, type Path } from './store'
import { scrollToY } from './ticker'

/** Switch path. The chapter list below the fork swaps; `jump` lands on the new path's first chapter. */
export function setPath(path: Path, jump = false) {
  if (store.getState().path !== path) {
    store.setState({ path })
    history.replaceState(null, '', `#${path}`)
  }
  // wait for React to commit the new chapter list and the controller to re-measure
  if (jump) requestAnimationFrame(() => requestAnimationFrame(() => scrollToY(film.top(1), true)))
}

export function goTo(id: string) {
  const el = document.getElementById(id)
  if (el) scrollToY(el.getBoundingClientRect().top + window.scrollY)
}
