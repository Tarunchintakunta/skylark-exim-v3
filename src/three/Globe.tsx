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
import { faceRotation, latLon, routePoints } from './geo'
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

/** Scroll-driven globe: camera pulls back from the Bay of Bengal, routes draw one by one (STORY §11). */
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
      return { to, points: routePoints(origin, to, N) }
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
    let t0 = -1
    let lastHl = -2
    return onTick((time) => {
      const i = frame.index
      const nearWorld = i === worldIndex || (i === worldIndex - 1 && frame.local > 0.8)
      if (!nearWorld || frame.past || !group.current) {
        t0 = -1
        return
      }
      const p = i === worldIndex ? frame.local : 0
      // camera: close over the Bay of Bengal → full globe
      const k = ease(clamp01(p / 0.5))
      const d = lerp(1.45, env.mobile ? 4.6 : 4.1, k)
      camera.position.set(0, 0, d)
      camera.lookAt(0, 0, 0)
      // desktop: the globe slides right to leave the copy its space; the origin dot keeps a constant screen size
      group.current.position.x = env.mobile ? 0 : lerp(0, 0.78, k)
      group.current.position.y = env.mobile ? lerp(0, 0.55, k) : 0
      originDot.current?.scale.setScalar(d / 3.2)
      // rotate from the Bay of Bengal toward Europe, then East Asia, as routes draw
      let lon = p < 0.45 ? lerp(88, 62, ease(p / 0.45)) : lerp(62, 104, ease(clamp01((p - 0.45) / 0.45)))
      const lat = lerp(15, 26, k)
      // ends with a slow auto-rotation while in view
      if (p > 0.92) {
        if (t0 < 0) t0 = time
        lon += (time - t0) * 3
      } else t0 = -1
      const [rx, ry] = faceRotation(lat, lon)
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
  }, [camera, get, invalidate, routes, worldIndex])

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
            <span className="globe-label mono" ref={(s) => void (labels.current[j] = s)} style={{ opacity: 0 }}>
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
    <Canvas
      className="globe-canvas"
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
  )
}
