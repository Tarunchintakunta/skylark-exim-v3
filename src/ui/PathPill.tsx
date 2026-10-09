import { setPath } from '../engine/path'
import { useApp } from '../engine/store'

/** Header pill: switch Ocean ⇄ Pond at any time; jumps to the other path's first chapter. */
export function PathPill() {
  const path = useApp((s) => s.path)
  const other = path === 'ocean' ? 'pond' : 'ocean'
  return (
    <button className="path-pill mono" onClick={() => setPath(other, true)}>
      <span aria-current={path === 'ocean'}>Ocean</span>
      <span aria-hidden="true">⇄</span>
      <span aria-current={path === 'pond'}>Pond</span>
      <span className="sr-only">: switch to the {other} path</span>
    </button>
  )
}
