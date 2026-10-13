import type { ReactNode } from 'react'

import type { RecognizedFace } from '../lib/types'

// Colour is paired with a text label on every box, so it never carries meaning alone.
const BAND_STYLE = {
  confirmed: { border: '#17794a', label: 'Confirmed' },
  review: { border: '#8a5a00', label: 'Needs review' },
  unknown: { border: '#5b6676', label: 'Unrecognised' },
} as const

/** A video or image with a labelled box drawn over each face. Boxes are in source-frame pixels. */
export function FaceOverlay({
  faces,
  frameSize,
  children,
}: {
  faces: RecognizedFace[]
  frameSize: [number, number]
  children: ReactNode
}) {
  const [width, height] = frameSize
  return (
    <div className="relative overflow-hidden rounded-md bg-ink" style={{ aspectRatio: width && height ? `${width} / ${height}` : '16 / 9' }}>
      {children}
      {width > 0 &&
        faces.map((face, index) => {
          const [x1, y1, x2, y2] = face.box
          const style = BAND_STYLE[face.band]
          return (
            <div
              key={face.track ?? index}
              className="absolute border-2"
              style={{
                borderColor: style.border,
                left: `${(x1 / width) * 100}%`,
                top: `${(y1 / height) * 100}%`,
                width: `${((x2 - x1) / width) * 100}%`,
                height: `${((y2 - y1) / height) * 100}%`,
              }}
            >
              <span
                className="absolute -top-6 left-0 whitespace-nowrap rounded px-1.5 py-0.5 text-xs font-medium text-white"
                style={{ background: style.border }}
              >
                {face.student_name ? `${face.student_name} · ${style.label}` : style.label}
                {face.band !== 'unknown' ? ` · ${face.score.toFixed(2)}` : ''}
              </span>
            </div>
          )
        })}
    </div>
  )
}

export function faceCounts(faces: RecognizedFace[]) {
  const counts = { confirmed: 0, review: 0, unknown: 0 }
  for (const face of faces) counts[face.band] += 1
  return counts
}
