import { Line, useTexture } from '@react-three/drei'
import { Canvas, useThree } from '@react-three/fiber'
import { Suspense, useEffect, useMemo, useRef, type RefObject } from 'react'
import { ACESFilmicToneMapping, AdditiveBlending, BackSide, Color, Group, MathUtils, SRGBColorSpace, Vector3, type Mesh } from 'three'
import type { Line2 } from 'three-stdlib'
import { MARKET_COORDS, MARKETS_BY_REGION, ORIGIN } from '../config/markets'
import { env } from '../engine/env'
import { frame } from '../engine/store'
import { onTick } from '../engine/ticker'
import { film } from '../film/controller'
import { faceRotation, latLon, routePoints } from './geo'
import { globeUi } from './globeState'

const BRASS = new Color('#e08a5f')
const MARIGOLD = new Color('#eaa221')
const N = 64 // points per route
const FOV = 35
const TAN = Math.tan(MathUtils.degToRad(FOV / 2))
const ease = (t: number) => t * t * (3 - 2 * t)
const clamp01 = (t: number) => Math.min(1, Math.max(0, t))
const lerp = (a: number, b: number, t: number) => a + (b - a) * t
/** the fixed header (.topbar height); label lift above a dot, gap between labels, margin to the viewport edge (px) */
const HEADER = 68
const LIFT = 8
const GAP = 6
const EDGE = 8
/** at most this many labels on screen, the origin's included */
const MAX_LABELS = 4
/** a pointer within this many px of a dot reveals its label */
const HIT = 22
/** route widths in px (resting, highlighted) and opacities (resting, highlighted, dimmed) */
const LINE_W = env.mobile ? 1 : 1.25
const LINE_HL = 2
const OP = 0.5
const OP_HL = 0.95
const OP_DIM = 0.2
/** routes draw one by one between these scroll progresses of the world chapter */
const DRAW = [0.2, 0.8]

/** Settled view: centred between Algeria and Japan so every market faces the camera; the idle tour sways ±SWAY° around it. */
const C_LON = 70
const C_LAT = 24
const SWAY = 18
/** idle tour: one region at a time (≤3 markets, the origin label is the 4th), the globe easing toward it */
const SPOTS = MARKETS_BY_REGION.flatMap(({ markets }) => {
  const out: number[][] = []
  for (let i = 0; i < markets.length; i += MAX_LABELS - 1) out.push(markets.slice(i, i + MAX_LABELS - 1))
  return out
})
const toSway = (lon: number) => Math.min(SWAY, Math.max(-SWAY, lon - C_LON))
const SPOT_SWAY = SPOTS.map((ids) => toSway(ids.reduce((s, i) => s + MARKET_COORDS[i].lon, 0) / ids.length))
const DWELL = 3.2

const atmosphere = {
  uniforms: { color: { value: new Color('#9fd3ff') } },
  vertexShader: 'varying vec3 vN; void main(){ vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  // a thin, faint rim: only the outer sliver of the shell
  fragmentShader: 'uniform vec3 color; varying vec3 vN; void main(){ float i = pow(clamp(0.62 - dot(vN, vec3(0.0, 0.0, 1.0)), 0.0, 1.0), 3.0) * 0.7; gl_FragColor = vec4(color, i); }',
}
const haze = {
  uniforms: { color: { value: new Color('#cfe9ff') } },
  vertexShader: 'varying vec3 vN; void main(){ vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: 'uniform vec3 color; varying vec3 vN; void main(){ float i = pow(1.0 - max(dot(vN, vec3(0.0, 0.0, 1.0)), 0.0), 3.0); gl_FragColor = vec4(color * i * 0.35, 1.0); }',
}

export type GlobeLabels = { markets: (HTMLSpanElement | null)[]; origin: HTMLSpanElement | null }

/** Scroll-driven globe: camera pulls back from the sea off Visakhapatnam, routes draw one by one (STORY §11). */
function Earth({ worldIndex, labels }: { worldIndex: number; labels: RefObject<GlobeLabels> }) {
  // 2048×1024 everywhere (CLAUDE_PROMPT §13: not 4K); a 4K upload is a long task on weaker GPUs
  const tex = useTexture('/textures/earth_day_2048.webp')
  tex.colorSpace = SRGBColorSpace
  tex.anisotropy = 4
  const seg = env.mobile ? 64 : 128
  const group = useRef<Group>(null)
  const lines = useRef<(Line2 | null)[]>([])
  const dots = useRef<(Mesh | null)[]>([])
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
    () => MARKET_COORDS.map((m, j) => {
      const to = latLon(m.lat, m.lon, 1.002)
      // varied heights (a golden-ratio spread per market) so the routes don't bundle into one fan
      return { to, points: routePoints(origin, to, N, 0.12 + 0.26 * ((j * 0.618) % 1)) }
    }),
    [origin],
  )

  useEffect(() => {
    const L = labels.current!
    const tmp = new Vector3()
    const camDir = new Vector3()
    const sizes = new Map<HTMLElement, [number, number]>()
    const shown = new Map<HTMLElement, string>()

    // pause when the world chapter is off-screen or the tab is hidden (frameloop="demand": no invalidate, no render)
    let onScreen = true
    const section = document.querySelector('[data-chapter="world"]')
    const io = new IntersectionObserver(([e]) => void (onScreen = e.isIntersecting), { rootMargin: '50% 0px' })
    if (section) io.observe(section)

    // hover / tap on a dot: the stage takes no pointer events, so read the pointer on the window
    let px = -1e4
    let py = -1e4
    const onPointer = (e: PointerEvent) => {
      px = e.clientX
      py = e.clientY
    }
    const onLeave = () => (px = py = -1e4)
    addEventListener('pointermove', onPointer, { passive: true })
    addEventListener('pointerdown', onPointer, { passive: true })
    document.documentElement.addEventListener('pointerleave', onLeave)

    // layout in px (globe radius and centre), from the market caption's box: on resize and once a second
    let dirty = true
    let sinceMeasure = 0
    const onResize = () => (dirty = true)
    addEventListener('resize', onResize)
    const lay = { r: 0, cx: 0, cy: 0 }
    const measure = (vw: number, vh: number) => {
      const cap = section?.querySelector('.caption--markets')?.getBoundingClientRect()
      if (!cap?.height) return
      if (env.mobile) {
        // phones: the globe sits above the market list
        lay.r = Math.max(60, Math.min(vw * 0.4, (cap.top - HEADER) / 2 - 10))
        lay.cx = vw / 2
        lay.cy = (HEADER + cap.top) / 2
      } else {
        // right of the copy, its vertical centre on the headline block's
        const room = vw - cap.right
        lay.r = Math.min(room * 0.4, (vh - HEADER) * 0.36)
        lay.cx = cap.right + room / 2
        lay.cy = Math.min(Math.max(cap.top + cap.height / 2, HEADER + lay.r + 12), vh - lay.r - 12)
      }
    }

    /** places a label centred over (x, y): above it, else below it, else not at all (overlap) */
    const place = (label: HTMLElement, x: number, y: number, boxes: number[][], vw: number, vh: number) => {
      let s = sizes.get(label)
      if (!s) sizes.set(label, (s = [label.offsetWidth, label.offsetHeight]))
      const [w, h] = s
      const l = Math.min(Math.max(x - w / 2, EDGE), vw - EDGE - w)
      const free = (t: number) => !boxes.some(([bl, bt, br, bb]) => l < br + GAP && l + w > bl - GAP && t < bb + GAP && t + h > bt - GAP)
      const t = [y - LIFT - h, y + LIFT].map((t) => Math.min(Math.max(t, HEADER + EDGE), vh - EDGE - h)).find(free)
      if (t === undefined) return false
      boxes.push([l, t, l + w, t + h])
      const tf = `translate(${Math.round(l)}px, ${Math.round(t)}px)`
      if (shown.get(label) !== tf) {
        label.style.transform = tf
        shown.set(label, tf)
      }
      return true
    }
    const setOpacity = (label: HTMLElement | null, on: boolean) => {
      const o = on ? '1' : '0'
      if (label && label.style.opacity !== o) label.style.opacity = o
    }

    let last = -1
    let clock = 0
    let sway = 0
    let lastFocus = -2
    const screen: [number, number, boolean][] = routes.map(() => [0, 0, false])
    const placed = new Set<HTMLElement>()

    const off = onTick((time) => {
      const dt = last < 0 ? 0 : Math.min(0.05, time - last)
      last = time
      const i = frame.index
      const nearWorld = i === worldIndex || (i === worldIndex - 1 && frame.local > 0.8)
      if (!nearWorld || frame.past || !onScreen || document.hidden || !group.current) return
      const g = group.current
      const p = i === worldIndex ? frame.local : 0
      const { width: vw, height: vh } = get().size
      if (dirty || (sinceMeasure += dt) > 1) {
        measure(vw, vh)
        dirty = false
        sinceMeasure = 0
      }
      if (!lay.r) {
        lay.r = Math.min(vw, vh) * 0.3
        lay.cx = vw / 2
        lay.cy = vh / 2
      }

      // camera: close over the sea off Visakhapatnam → the full globe at its laid-out size and place
      const k = ease(clamp01(p / 0.5))
      const dEnd = Math.sqrt(1 + (vh / (2 * TAN * lay.r)) ** 2)
      const d = lerp(1.45, dEnd, k)
      camera.position.set(0, 0, d)
      camera.lookAt(0, 0, 0)
      const unit = (2 * d * TAN) / vh // world units per px at the globe's depth
      g.position.x = lerp(0, (lay.cx - vw / 2) * unit, k)
      g.position.y = lerp(0, (vh / 2 - lay.cy) * unit, k)
      const s = d / 4
      originDot.current?.scale.setScalar(s)

      // focus: a hovered list item, else a hovered/tapped dot (found below, from last frame's screen positions)
      let focus = globeUi.highlight
      if (focus < 0 && px > -1e3) {
        let best = HIT * HIT
        screen.forEach(([x, y, vis], j) => {
          const dd = (x - px) ** 2 + (y - py) ** 2
          if (vis && dd < best) {
            best = dd
            focus = j
          }
        })
      }

      // rotation: Visakhapatnam → the settled view, then (motion allowed) the idle tour eases toward each region
      const settled = p > DRAW[1]
      if (settled) clock += dt
      const spot = SPOTS[Math.floor(clock / DWELL) % SPOTS.length]
      if (!env.reduced) {
        const target = focus >= 0 ? toSway(MARKET_COORDS[focus].lon) : settled ? SPOT_SWAY[SPOTS.indexOf(spot)] : 0
        sway += (target - sway) * (1 - Math.exp(-dt * 0.9))
      }
      const lon = lerp(ORIGIN.lon + 4, C_LON, ease(clamp01(p / 0.6))) + sway
      const lat = lerp(15, C_LAT, k)
      const [rx, ry] = faceRotation(lat, lon)
      g.rotation.set(rx, ry, 0, 'XYZ')
      g.updateMatrixWorld()
      camera.updateMatrixWorld()
      camDir.copy(camera.position).normalize()

      // routes draw one by one; dots appear as each lands
      const w = (DRAW[1] - DRAW[0]) / routes.length
      routes.forEach((r, j) => {
        const a = clamp01((p - DRAW[0] - j * w) / (w * 1.6))
        const line = lines.current[j]
        if (line) {
          line.geometry.instanceCount = Math.round(a * (N - 1))
          if (focus !== lastFocus) {
            line.material.opacity = focus < 0 ? OP : focus === j ? OP_HL : OP_DIM
            line.material.linewidth = focus === j ? LINE_HL : LINE_W
          }
        }
        const landed = a >= 1
        dots.current[j]?.scale.setScalar(landed ? s : 0)
        tmp.copy(r.to).applyMatrix4(g.matrixWorld).sub(g.position)
        const facing = tmp.dot(camDir) > 0.2
        tmp.copy(r.to).applyMatrix4(g.matrixWorld).project(camera)
        const sc = screen[j]
        sc[0] = ((tmp.x + 1) / 2) * vw
        sc[1] = ((1 - tmp.y) / 2) * vh
        sc[2] = landed && facing
      })
      lastFocus = focus

      // labels in screen space: the origin, then the focus (or the tour's region), ≤ MAX_LABELS, never overlapping
      const boxes: number[][] = []
      placed.clear()
      tmp.copy(origin).applyMatrix4(g.matrixWorld).project(camera)
      if (k > 0.6 && L.origin && place(L.origin, ((tmp.x + 1) / 2) * vw, ((1 - tmp.y) / 2) * vh, boxes, vw, vh)) placed.add(L.origin)
      const want = focus >= 0 ? [focus] : settled ? spot : []
      for (const j of want) {
        const label = L.markets[j]
        if (placed.size >= MAX_LABELS || !label || !screen[j][2]) continue
        if (place(label, screen[j][0], screen[j][1], boxes, vw, vh)) placed.add(label)
      }
      setOpacity(L.origin, placed.has(L.origin!))
      L.markets.forEach((label) => setOpacity(label, placed.has(label!)))
      invalidate()
    })

    return () => {
      off()
      io.disconnect()
      removeEventListener('pointermove', onPointer)
      removeEventListener('pointerdown', onPointer)
      document.documentElement.removeEventListener('pointerleave', onLeave)
      removeEventListener('resize', onResize)
    }
  }, [camera, get, invalidate, labels, origin, routes, worldIndex])

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
      <mesh scale={1.025}>
        <sphereGeometry args={[1, 64, 32]} />
        <shaderMaterial args={[atmosphere]} side={BackSide} transparent depthWrite={false} />
      </mesh>
      {/* origin pin: marigold, a touch larger than the market dots */}
      <mesh position={origin} ref={originDot}>
        <sphereGeometry args={[0.016, 12, 8]} />
        <meshBasicMaterial color={MARIGOLD} />
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
            lineWidth={LINE_W}
            opacity={OP}
            transparent
            depthWrite={false}
          />
          <mesh position={r.to} scale={0} ref={(m) => void (dots.current[j] = m)}>
            <sphereGeometry args={[0.009, 10, 8]} />
            <meshBasicMaterial color={BRASS} />
          </mesh>
        </group>
      ))}
    </group>
  )
}

export default function GlobeCanvas() {
  const worldIndex = film.chapters.findIndex((c) => c.id === 'world')
  const labels = useRef<GlobeLabels>({ markets: [], origin: null })
  return (
    <>
      <Canvas
        className="globe-canvas"
        dpr={env.mobile ? 1 : [1, 1.5]}
        frameloop="demand"
        gl={{ antialias: false, alpha: true, powerPreference: 'high-performance' }}
        camera={{ fov: FOV, near: 0.01, far: 20, position: [0, 0, 3.2] }}
        onCreated={({ gl }) => {
          gl.toneMapping = ACESFilmicToneMapping
          gl.toneMappingExposure = 1.1
        }}
      >
        <ambientLight intensity={0.9} />
        <hemisphereLight args={['#ffffff', '#cfe3ea', 0.8]} />
        <directionalLight position={[-3, 2, 3]} intensity={2.5} />
        <Suspense fallback={null}>
          <Earth worldIndex={worldIndex} labels={labels} />
        </Suspense>
      </Canvas>
      {/* positioned per frame by Earth; decorative (the stage is aria-hidden), the market list is the real text */}
      <div className="globe-labels">
        <span className="globe-label globe-label--origin mono" ref={(s) => void (labels.current.origin = s)}>
          {ORIGIN.name}
        </span>
        {MARKET_COORDS.map((m, j) => (
          <span key={m.name} className="globe-label mono" ref={(s) => void (labels.current.markets[j] = s)}>
            {m.name}
          </span>
        ))}
      </div>
    </>
  )
}
