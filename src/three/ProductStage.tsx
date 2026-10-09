import { Center, OrbitControls, useGLTF } from '@react-three/drei'
import { Canvas, useThree } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import { Box3, Group, Vector3 } from 'three'
import type { ModelDef } from '../config/products'
import { env } from '../engine/env'
import { onTick } from '../engine/ticker'

/**
 * Product GLBs on a light stage (STORY §12): rotate ±25° with scroll; drag to orbit on desktop only.
 * Renders on demand, and only while the stage is on screen.
 */
function Model({ file, x, progress }: { file: string; x: number; progress: { current: number } }) {
  const { scene: shared } = useGLTF(`/models/${file}`)
  // useGLTF caches one scene per file; clone so a file can appear more than once
  const scene = useMemo(() => shared.clone(), [shared])
  const ref = useRef<Group>(null)
  const scale = useMemo(() => {
    const size = new Box3().setFromObject(scene).getSize(new Vector3())
    return 1.8 / Math.max(size.x, size.y, size.z)
  }, [scene])
  const { invalidate } = useThree()
  useEffect(
    () =>
      onTick(() => {
        if (progress.current < 0 || !ref.current) return
        ref.current.rotation.y = (progress.current - 0.5) * ((50 * Math.PI) / 180)
        invalidate()
      }),
    [invalidate, progress],
  )
  return (
    <group ref={ref} position={[x, 0, 0]} scale={scale}>
      <Center>
        <primitive object={scene} />
      </Center>
    </group>
  )
}

export default function ProductStage({ models }: { models: ModelDef[] }) {
  const wrap = useRef<HTMLDivElement>(null)
  /** 0..1 while the stage crosses the viewport, -1 when off screen */
  const progress = useRef(-1)
  useEffect(() => {
    const el = wrap.current!
    let visible = false
    const io = new IntersectionObserver(([e]) => (visible = e.isIntersecting))
    io.observe(el)
    let top = 0
    let h = 1
    const measure = () => {
      const r = el.getBoundingClientRect()
      top = r.top + window.scrollY
      h = r.height
    }
    measure()
    addEventListener('resize', measure)
    const off = onTick(() => {
      progress.current = visible ? Math.min(1, Math.max(0, (window.scrollY + innerHeight - top) / (innerHeight + h))) : -1
    }, -1)
    return () => {
      io.disconnect()
      removeEventListener('resize', measure)
      off()
    }
  }, [])
  const files = models.filter((m) => m.glb)
  const gap = 2.1
  return (
    <div className="product-stage" ref={wrap}>
      <Canvas
        dpr={env.mobile ? 1 : [1, 1.5]}
        frameloop="demand"
        gl={{ antialias: false, alpha: true }}
        camera={{ fov: 30, position: [0, 0.4, files.length > 1 ? 6.2 : 4.4] }}
        shadows={false}
      >
        <ambientLight intensity={1.2} />
        <hemisphereLight args={['#ffffff', '#bcd6dc', 1]} />
        <directionalLight position={[-3, 4, 4]} intensity={2.2} />
        {files.map((m, i) => (
          <Model key={m.glb} file={m.glb!} x={(i - (files.length - 1) / 2) * gap} progress={progress} />
        ))}
        {env.fine && !env.reduced && <OrbitControls enableZoom={false} enablePan={false} minPolarAngle={Math.PI / 3} maxPolarAngle={(2 * Math.PI) / 3} />}
      </Canvas>
      <ul className="product-stage__names">
        {files.map((m) => (
          <li key={m.name} className="display">{m.name}</li>
        ))}
      </ul>
    </div>
  )
}

/** preload a category's models one section ahead */
export const preloadModels = (models: ModelDef[]) => models.forEach((m) => m.glb && useGLTF.preload(`/models/${m.glb}`))
