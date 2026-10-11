import { Html, Line, useTexture } from '@react-three/drei'
import { Canvas, useThree } from '@react-three/fiber'
import { Suspense, useEffect, useMemo, useRef } from 'react'
import { ACESFilmicToneMapping, AdditiveBlending, BackSide, Color, Group, SRGBColorSpace, Vector3, type Mesh } from 'three'
import type { Line2 } from 'three-stdlib'
import { MARKET_COORDS, ORIGIN } from '../config/markets'
import { env } from '../engine/env'
import { frame } from '../engine/store'
import { onTick } from '../engine/ticker'
import { film } from '../film/controller'
import { faceRotation, latLon, routePoints, toLatLon } from './geo'
import { globeUi } from './globeState'

const BRASS = new Color('#e08a5f')
const N = 64 // points per route
const ease = (t: number) => t * t * (3 - 2 * t)
const clamp01 = (t: number) => Math.min(1, Math.max(0, t))
const lerp = (a: number, b: number, t: number) => a + (b - a) * t
/** market labels: lift above the dot (.globe-label translateY), gap between labels, margin to the viewport edge (px) */
const LIFT = 16
const GAP = 4
const EDGE = 8
/** the fixed header (.topbar height): labels stay below it */
const HEADER = 68
/** user rotation: max tilt from the scroll view (deg), idle seconds before easing home, inertia/ease/home rates (1/s) */
const TILT = 25
const IDLE = 3
const FRICTION = 4
const SEEK = 4
const HOME = 1.2
/** wraps a longitude difference into −180..180 */
const wrapLon = (d: number) => ((((d + 180) % 360) + 360) % 360) - 180
const clampTilt = (t: number) => Math.min(TILT, Math.max(-TILT, t))

const atmosphere = {
  uniforms: { color: { value: new Color('#9fd3ff') } },
  vertexShader: 'varying vec3 vN; void main(){ vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: 'uniform vec3 color; varying vec3 vN; void main(){ float i = pow(0.72 - dot(vN, vec3(0.0, 0.0, 1.0)), 2.4); gl_FragColor = vec4(color, clamp(i, 0.0, 1.0)); }',
}
const haze = {
  uniforms: { color: { value: new Color('#cfe9ff') } },
  vertexShader: 'varying vec3 vN; void main(){ vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: 'uniform vec3 color; varying vec3 vN; void main(){ float i = pow(1.0 - max(dot(vN, vec3(0.0, 0.0, 1.0)), 0.0), 3.0); gl_FragColor = vec4(color * i * 0.75, 1.0); }',
}

/** Scroll-driven globe: camera pulls back from the sea off Visakhapatnam, routes draw one by one (STORY §11). */
function Earth({ worldIndex }: { worldIndex: number }) {
  // 2048×1024 everywhere (CLAUDE_PROMPT §13: not 4K); a 4K upload is a long task on weaker GPUs
  const tex = useTexture('/textures/earth_day_2048.webp')
  tex.colorSpace = SRGBColorSpace
  tex.anisotropy = 4
  const seg = env.mobile ? 64 : 128
  const group = useRef<Group>(null)
  const lines = useRef<(Line2 | null)[]>([])
  const dots = useRef<(Mesh | null)[]>([])
  const labels = useRef<(HTMLSpanElement | null)[]>([])
  const originDot = useRef<Mesh>(null)
  const { camera, invalidate, gl, scene, get } = useThree()

  // pre-warm two chapters early, in separate idle slices: GPU texture upload, then shader compile, then one render
  useEffect(() => {
    const idle = (fn: () => void) => ('requestIdleCallback' in window ? requestIdleCallback(fn, { timeout: 1500 }) : setTimeout(fn, 200))
    idle(() => {
      gl.initTexture(tex)
      // compileAsync uses KHR_parallel_shader_compile: no main-thread wait on link status
      idle(() => void gl.compileAsync(scene, camera).then(() => idle(() => invalidate())))
    })
  }, [gl, scene, camera, tex, invalidate])

  const origin = useMemo(() => latLon(ORIGIN.lat, ORIGIN.lon, 1.002), [])
  const routes = useMemo(
    () => MARKET_COORDS.map((m) => {
      const to = latLon(m.lat, m.lon, 1.002)
      // the globe faces the middle of the arc when this market is clicked: the market and its route both sit in front
      return { to, points: routePoints(origin, to, N), face: toLatLon(origin.clone().add(to)) }
    }),
    [origin],
  )

  useEffect(() => {
    const tmp = new Vector3()
    const camDir = new Vector3()
    /** labels that have landed and face the camera this frame; label sizes (measured once) and current nudges */
    const want: number[] = []
    const sizes: [number, number][] = []
    const nudges: string[] = []
    let lastHl = -2

    // drag / keys / market clicks: an offset on top of the scroll view (lat, lon in degrees), with inertia; after IDLE
    // seconds without input it eases home and the idle spin resumes. Wheel is never handled: it always scrolls the page.
    const wrap = gl.domElement.closest<HTMLElement>('.globe-canvas')!
    const off = { lat: 0, lon: 0 }
    const vel = { lat: 0, lon: 0 }
    let spin = 0
    let now = 0
    let prev = -1
    let idleAt = -Infinity
    let lastFocus = -1
    let drag: { id: number; x: number; y: number; t: number; live: boolean } | null = null
    const interact = () => {
      off.lon = wrapLon(off.lon + spin)
      spin = 0
      idleAt = now
    }
    const turn = (dLat: number, dLon: number) => {
      off.lat = clampTilt(off.lat + dLat)
      off.lon += dLon
    }
    const down = (e: PointerEvent) => {
      if (e.button !== 0) return
      // touch: wait to see the gesture; mouse/pen: grab at once
      drag = { id: e.pointerId, x: e.clientX, y: e.clientY, t: e.timeStamp, live: e.pointerType !== 'touch' }
      if (drag.live) grab(e)
    }
    const grab = (e: PointerEvent) => {
      wrap.setPointerCapture(e.pointerId)
      wrap.classList.add('is-grabbing')
      vel.lat = vel.lon = 0
      globeUi.focus = lastFocus = -1
      interact()
      if (!globeUi.explored) {
        globeUi.explored = true
        wrap.parentElement?.querySelector('.globe-hint')?.classList.add('is-gone')
      }
    }
    const move = (e: PointerEvent) => {
      if (!drag || e.pointerId !== drag.id) return
      const dx = e.clientX - drag.x
      const dy = e.clientY - drag.y
      if (!drag.live) {
        // touch-action: pan-y hands vertical swipes to the page (pointercancel); only a mostly-horizontal drag turns
        if (Math.hypot(dx, dy) < 6) return
        if (Math.abs(dx) <= Math.abs(dy)) return void (drag = null)
        drag.live = true
        grab(e)
      }
      // ≈ 180° across the globe's on-screen diameter
      const k = 230 / wrap.clientHeight
      const dt = Math.max(e.timeStamp - drag.t, 8) / 1000
      turn(dy * k, -dx * k)
      vel.lat = lerp(vel.lat, (dy * k) / dt, 0.5)
      vel.lon = lerp(vel.lon, (-dx * k) / dt, 0.5)
      Object.assign(drag, { x: e.clientX, y: e.clientY, t: e.timeStamp })
      idleAt = now
    }
    const up = (e: PointerEvent) => {
      if (!drag || e.pointerId !== drag.id) return
      // a pause before letting go means no fling
      if (env.reduced || e.timeStamp - drag.t > 80) vel.lat = vel.lon = 0
      drag = null
      wrap.classList.remove('is-grabbing')
      idleAt = now
    }
    const key = (e: KeyboardEvent) => {
      const d = { ArrowLeft: [0, -15], ArrowRight: [0, 15], ArrowUp: [10, 0], ArrowDown: [-10, 0] }[e.key]
      if (!d) return
      e.preventDefault()
      globeUi.focus = lastFocus = -1
      interact()
      // instant under reduced motion; otherwise an inertia kick that glides the same distance
      if (env.reduced) turn(d[0], d[1])
      else {
        vel.lat = d[0] * FRICTION
        vel.lon = d[1] * FRICTION
      }
    }
    wrap.addEventListener('pointerdown', down)
    wrap.addEventListener('pointermove', move)
    wrap.addEventListener('pointerup', up)
    wrap.addEventListener('pointercancel', up)
    wrap.addEventListener('keydown', key)

    const stop = onTick((time) => {
      const dt = prev < 0 ? 0 : Math.min(time - prev, 0.1)
      prev = now = time
      const i = frame.index
      // only the world chapter takes pointer and keyboard input; the layer is invisible before it
      const live = i === worldIndex && !frame.past
      if (wrap.tabIndex !== (live ? 0 : -1)) {
        wrap.tabIndex = live ? 0 : -1
        wrap.style.pointerEvents = live ? 'auto' : 'none'
      }
      const nearWorld = i === worldIndex || (i === worldIndex - 1 && frame.local > 0.8)
      if (!nearWorld || frame.past || !group.current) {
        off.lat = off.lon = vel.lat = vel.lon = spin = 0
        globeUi.focus = lastFocus = -1
        return
      }
      const p = i === worldIndex ? frame.local : 0
      // camera: close over the sea off Visakhapatnam → full globe
      const k = ease(clamp01(p / 0.5))
      const d = lerp(1.45, env.mobile ? 4.6 : 4.1, k)
      camera.position.set(0, 0, d)
      camera.lookAt(0, 0, 0)
      // desktop: the globe slides right to leave the copy its space; the origin dot keeps a constant screen size
      group.current.position.x = env.mobile ? 0 : lerp(0, 0.78, k)
      group.current.position.y = env.mobile ? lerp(0, 0.55, k) : 0
      originDot.current?.scale.setScalar(d / 3.2)
      // rotate from Visakhapatnam toward Europe, then East Asia, as routes draw
      const baseLon = p < 0.45 ? lerp(88, 62, ease(p / 0.45)) : lerp(62, 104, ease(clamp01((p - 0.45) / 0.45)))
      const baseLat = lerp(15, 26, k)

      // a clicked market: turn so it and its arc face the camera (shortest way round), hold while it stays highlighted
      const f = globeUi.focus
      if (f !== lastFocus) {
        lastFocus = f
        if (f >= 0) {
          interact()
          vel.lat = vel.lon = 0
        }
      }
      if (f >= 0 && globeUi.highlight === f) idleAt = time
      const idle = time - idleAt > IDLE
      if (f >= 0 && idle) globeUi.focus = lastFocus = -1
      if (drag?.live) {
        // the pointer moves the globe directly
      } else if (globeUi.focus >= 0) {
        const [fLat, fLon] = routes[f].face
        const tLat = clampTilt(fLat - baseLat)
        const tLon = off.lon + wrapLon(fLon - baseLon - off.lon)
        const a = env.reduced ? 1 : 1 - Math.exp(-dt * SEEK)
        off.lat += (tLat - off.lat) * a
        off.lon += (tLon - off.lon) * a
      } else if (idle) {
        // ease home to the scroll view, then the idle spin takes over again
        off.lon = wrapLon(off.lon)
        const a = env.reduced ? 1 : 1 - Math.exp(-dt * HOME)
        off.lat -= off.lat * a
        off.lon -= off.lon * a
        if (Math.abs(off.lat) + Math.abs(off.lon) < 0.05) off.lat = off.lon = 0
      } else {
        turn(vel.lat * dt, vel.lon * dt)
        const a = Math.exp(-dt * FRICTION)
        vel.lat *= a
        vel.lon *= a
      }
      // ends with a slow auto-rotation while in view (none under reduced motion)
      if (p > 0.92 && idle && !off.lat && !off.lon && !env.reduced) spin += dt * 3
      const [rx, ry] = faceRotation(baseLat + off.lat, baseLon + off.lon + spin)
      group.current.rotation.set(rx, ry, 0, 'XYZ')
      group.current.updateMatrixWorld()

      // routes draw one by one between 20% and 85%
      const hl = globeUi.highlight
      camDir.copy(camera.position).normalize()
      routes.forEach((r, j) => {
        const w = 0.65 / routes.length
        const a = clamp01((p - 0.2 - j * w) / (w * 1.6))
        const line = lines.current[j]
        if (line) {
          line.geometry.instanceCount = Math.round(a * (N - 1))
          if (hl !== lastHl) {
            line.material.opacity = hl < 0 || hl === j ? 1 : 0.3
            line.material.linewidth = hl === j ? (env.mobile ? 2 : 4) : env.mobile ? 1 : 2
          }
        }
        const landed = a >= 1
        const dot = dots.current[j]
        if (dot) dot.scale.setScalar(landed ? 1 : 0)
        tmp.copy(r.to).applyMatrix4(group.current!.matrixWorld).sub(group.current!.position)
        if (landed && labels.current[j] && tmp.dot(camDir) > 0.25) want.push(j)
      })

      // labels in screen space, the highlighted one first, then list order: a label that would overlap one already
      // placed stays hidden (Thailand / Bangkok, Taiwan / Hong Kong on phones), and placed ones are nudged inside the view
      const { width: vw, height: vh } = get().size
      camera.updateMatrixWorld()
      const boxes: number[][] = []
      const placed = new Set<number>()
      for (const j of want.includes(hl) ? [hl, ...want.filter((k) => k !== hl)] : want) {
        const label = labels.current[j]!
        const [w, h] = (sizes[j] ??= [label.offsetWidth, label.offsetHeight])
        tmp.copy(routes[j].to).applyMatrix4(group.current!.matrixWorld).project(camera)
        const x = ((tmp.x + 1) / 2) * vw - w / 2
        const y = ((1 - tmp.y) / 2) * vh - LIFT - h / 2
        const l = Math.min(Math.max(x, EDGE), vw - EDGE - w)
        // above the dot, else below it, else hidden
        const free = (t: number) => !boxes.some(([bl, bt, br, bb]) => l < br + GAP && l + w > bl - GAP && t < bb + GAP && t + h > bt - GAP)
        const t = [y, y + 2 * LIFT].map((t) => Math.min(Math.max(t, HEADER + EDGE), vh - EDGE - h)).find(free)
        if (t === undefined) continue
        boxes.push([l, t, l + w, t + h])
        placed.add(j)
        const nudge = `${Math.round(l - x)}px ${Math.round(t - y)}px`
        if (nudges[j] !== nudge) label.style.translate = nudges[j] = nudge
      }
      want.length = 0
      labels.current.forEach((label, j) => {
        const o = placed.has(j) ? (hl < 0 || hl === j ? '1' : '0.4') : '0'
        if (label && label.style.opacity !== o) label.style.opacity = o
      })
      lastHl = hl
      invalidate()
    })
    return () => {
      stop()
      wrap.removeEventListener('pointerdown', down)
      wrap.removeEventListener('pointermove', move)
      wrap.removeEventListener('pointerup', up)
      wrap.removeEventListener('pointercancel', up)
      wrap.removeEventListener('keydown', key)
    }
  }, [camera, get, gl, invalidate, routes, worldIndex])

  return (
    <group ref={group}>
      <mesh>
        <sphereGeometry args={[1, seg, seg / 2]} />
        {/* emissive copy of the albedo lifts the dark Blue Marble oceans: the globe must read bright daytime */}
        <meshStandardMaterial map={tex} roughness={0.85} metalness={0} emissive="#ffffff" emissiveMap={tex} emissiveIntensity={0.25} />
      </mesh>
      <mesh scale={1.001}>
        <sphereGeometry args={[1, seg, seg / 2]} />
        <shaderMaterial args={[haze]} blending={AdditiveBlending} transparent depthWrite={false} />
      </mesh>
      <mesh scale={1.06}>
        <sphereGeometry args={[1, 64, 32]} />
        <shaderMaterial args={[atmosphere]} side={BackSide} transparent depthWrite={false} />
      </mesh>
      <mesh position={origin} ref={originDot}>
        <sphereGeometry args={[0.012, 12, 8]} />
        <meshBasicMaterial color={BRASS} />
      </mesh>
      {routes.map((r, j) => (
        <group key={MARKET_COORDS[j].name}>
          <Line
            ref={(l) => {
              lines.current[j] = l as unknown as Line2 | null
              if (l) (l as unknown as Line2).geometry.instanceCount = 0
            }}
            points={r.points}
            color={BRASS}
            lineWidth={env.mobile ? 1 : 2}
            transparent
          />
          <mesh position={r.to} scale={0} ref={(m) => void (dots.current[j] = m)}>
            <sphereGeometry args={[0.011, 10, 8]} />
            <meshBasicMaterial color={BRASS} />
          </mesh>
          <Html position={r.to} center zIndexRange={[5, 0]} style={{ pointerEvents: 'none' }}>
            <span className="globe-label mono" aria-hidden="true" ref={(s) => void (labels.current[j] = s)} style={{ opacity: 0 }}>
              {MARKET_COORDS[j].name}
            </span>
          </Html>
        </group>
      ))}
    </group>
  )
}

export default function GlobeCanvas() {
  const worldIndex = film.chapters.findIndex((c) => c.id === 'world')
  return (
    <>
    <Canvas
      className="globe-canvas"
      role="application"
      aria-roledescription="globe"
      aria-label="Globe of the 16 export markets. Drag or use the arrow keys to turn it."
      tabIndex={-1}
      style={{ pointerEvents: 'none' }}
      dpr={env.mobile ? 1 : [1, 1.5]}
      frameloop="demand"
      gl={{ antialias: false, alpha: true, powerPreference: 'high-performance' }}
      camera={{ fov: 35, near: 0.01, far: 20, position: [0, 0, 3.2] }}
      onCreated={({ gl }) => {
        gl.toneMapping = ACESFilmicToneMapping
        gl.toneMappingExposure = 1.1
      }}
    >
      <ambientLight intensity={0.9} />
      <hemisphereLight args={['#ffffff', '#cfe3ea', 0.8]} />
      <directionalLight position={[-3, 2, 3]} intensity={2.5} />
      <Suspense fallback={null}>
        <Earth worldIndex={worldIndex} />
      </Suspense>
    </Canvas>
    <p className={`globe-hint mono${globeUi.explored ? ' is-gone' : ''}`} aria-hidden="true">
      Drag to explore
    </p>
    </>
  )
}
