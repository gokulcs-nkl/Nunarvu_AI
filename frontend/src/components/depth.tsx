import { useRef } from 'react'
import type { PointerEvent, ReactNode } from 'react'

const MAX_TILT_DEGREES = 5

/**
 * Leans its content towards the pointer and moves a soft highlight with it, so a card
 * feels like a physical object. Does nothing for touch input or when the user has asked
 * for reduced motion (the CSS removes the transform in that case).
 */
export function Tilt({ children, className = '' }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)

  function handleMove(event: PointerEvent<HTMLDivElement>) {
    const element = ref.current
    if (!element || event.pointerType !== 'mouse') return
    const box = element.getBoundingClientRect()
    const x = (event.clientX - box.left) / box.width
    const y = (event.clientY - box.top) / box.height
    element.style.setProperty('--tilt-x', `${((0.5 - y) * 2 * MAX_TILT_DEGREES).toFixed(2)}deg`)
    element.style.setProperty('--tilt-y', `${((x - 0.5) * 2 * MAX_TILT_DEGREES).toFixed(2)}deg`)
    element.style.setProperty('--glare-x', `${(x * 100).toFixed(1)}%`)
    element.style.setProperty('--glare-y', `${(y * 100).toFixed(1)}%`)
    element.style.setProperty('--glare-on', '1')
  }

  function handleLeave() {
    const element = ref.current
    if (!element) return
    for (const name of ['--tilt-x', '--tilt-y', '--glare-on']) element.style.removeProperty(name)
  }

  return (
    <div ref={ref} className={`tilt relative ${className}`} onPointerMove={handleMove} onPointerLeave={handleLeave}>
      {children}
      <div className="tilt-glare pointer-events-none absolute inset-0 rounded-[inherit]" aria-hidden="true" />
    </div>
  )
}

/**
 * Decorative 3D object: three layers floating above each other, standing for the camera
 * frame, the faces found in it, and the attendance record that results.
 */
export function Stack3D({ size = 180 }: { size?: number }) {
  return (
    <div style={{ width: size, height: size, perspective: 900 }} aria-hidden="true" className="shrink-0">
      <div className="stack3d relative h-full w-full">
        <div
          style={{ ['--z' as string]: '0px' }}
          className="border border-white/10 bg-[linear-gradient(135deg,rgb(111_155_255/0.25),rgb(111_155_255/0.05))] shadow-[0_30px_60px_-10px_rgb(0_0_0/0.8)]"
        >
          <div className="absolute inset-3 rounded-lg bg-[linear-gradient(rgb(255_255_255/0.08)_1px,transparent_1px),linear-gradient(90deg,rgb(255_255_255/0.08)_1px,transparent_1px)] bg-[size:18px_18px]" />
        </div>
        <div style={{ ['--z' as string]: '38px' }} className="border border-white/15 bg-white/[0.06] backdrop-blur-[2px]">
          <div className="absolute left-[18%] top-[22%] h-[26%] w-[26%] rounded-md border-2 border-ok" />
          <div className="absolute left-[58%] top-[30%] h-[22%] w-[22%] rounded-md border-2 border-warn" />
          <div className="absolute bottom-[16%] left-[18%] h-1.5 w-[40%] rounded-full bg-white/25" />
        </div>
        <div style={{ ['--z' as string]: '76px' }} className="border border-white/20 bg-[linear-gradient(135deg,rgb(74_210_149/0.3),rgb(111_155_255/0.18))]">
          <div className="absolute left-[14%] top-[20%] flex h-[24%] w-[24%] items-center justify-center rounded-full bg-ok text-night">
            <svg viewBox="0 0 24 24" className="h-2/3 w-2/3" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12.5l4.5 4.5L19 7.5" />
            </svg>
          </div>
          <div className="absolute left-[46%] top-[24%] h-1.5 w-[38%] rounded-full bg-white/40" />
          <div className="absolute left-[46%] top-[36%] h-1.5 w-[24%] rounded-full bg-white/25" />
          <div className="absolute bottom-[20%] left-[14%] h-1.5 w-[70%] rounded-full bg-white/20" />
        </div>
      </div>
    </div>
  )
}
