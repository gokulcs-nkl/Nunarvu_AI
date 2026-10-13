import { Camera, CameraOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { api, ApiError } from '../lib/api'
import { useCamera } from '../lib/camera'
import { useCameraPreview, useSessionLive } from '../lib/live'
import type { RecognizedFace, RecognizeResult } from '../lib/types'
import { FaceOverlay, faceCounts } from './FaceOverlay'
import { Alert, Badge, Button, Card } from './ui'

const SCAN_INTERVAL_MS = 2000

function Counts({ faces }: { faces: RecognizedFace[] }) {
  const counts = faceCounts(faces)
  return (
    <>
      <Badge tone="ok">{counts.confirmed} confirmed</Badge>
      <Badge tone="warn">{counts.review} need review</Badge>
      <Badge>{counts.unknown} unrecognised</Badge>
    </>
  )
}

/** Fallback: this browser's webcam sends a frame every two seconds while the page is open. */
function BrowserCapture({ sessionId, onChanged }: { sessionId: number; onChanged: () => void }) {
  const camera = useCamera()
  const [faces, setFaces] = useState<RecognizedFace[]>([])
  const [frameSize, setFrameSize] = useState<[number, number]>([16, 9])
  const [error, setError] = useState<string | null>(null)
  const busy = useRef(false)
  const notifyChanged = useRef(onChanged)
  useEffect(() => {
    notifyChanged.current = onChanged
  }, [onChanged])
  const { active, capture, videoRef } = camera

  useEffect(() => {
    if (!active) return
    const timer = window.setInterval(async () => {
      if (busy.current) return // skip a tick rather than queue frames behind a slow one
      busy.current = true
      try {
        const frame = await capture()
        const video = videoRef.current
        if (!frame || !video) return
        const form = new FormData()
        form.append('image', frame, 'frame.jpg')
        const result = await api<RecognizeResult>(`/sessions/${sessionId}/recognize/`, { method: 'POST', body: form })
        setFrameSize([video.videoWidth, video.videoHeight])
        setFaces(result.faces)
        setError(null)
        if (result.changed.length > 0) notifyChanged.current()
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : 'Recognition failed.')
      } finally {
        busy.current = false
      }
    }, SCAN_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [active, capture, videoRef, sessionId])

  return (
    <>
      <FaceOverlay faces={active ? faces : []} frameSize={frameSize}>
        <video ref={videoRef} muted playsInline className="h-full w-full object-fill" />
      </FaceOverlay>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm" aria-live="polite">
        {active ? (
          <Button
            variant="secondary"
            onClick={() => {
              camera.stop()
              setFaces([])
            }}
          >
            <CameraOff size={16} aria-hidden="true" />
            Stop camera
          </Button>
        ) : (
          <Button onClick={() => void camera.start()}>
            <Camera size={16} aria-hidden="true" />
            Start camera
          </Button>
        )}
        <Counts faces={faces} />
      </div>
      {camera.error && (
        <div className="mt-3">
          <Alert>{camera.error}</Alert>
        </div>
      )}
      {error && (
        <div className="mt-3">
          <Alert>{error}</Alert>
        </div>
      )}
    </>
  )
}

/**
 * Live view for an active session. When a camera worker is serving the session its feed is
 * shown automatically; otherwise the teacher can fall back to this browser's webcam.
 */
export function LivePanel({ sessionId, onChanged }: { sessionId: number; onChanged: () => void }) {
  const { payload, live } = useSessionLive(sessionId, true)
  const [useBrowser, setUseBrowser] = useState(false)
  const preview = useCameraPreview(live && payload ? payload.camera : null)

  const notifyChanged = useRef(onChanged)
  useEffect(() => {
    notifyChanged.current = onChanged
  }, [onChanged])
  useEffect(() => {
    if (payload && payload.changed.length > 0) notifyChanged.current()
  }, [payload])

  if (live && payload) {
    const failing = payload.status === 'error'
    return (
      <Card
        title={`Live: ${payload.camera_name}`}
        action={failing ? <Badge tone="danger">Camera error</Badge> : <Badge tone="ok">Online</Badge>}
      >
        <FaceOverlay faces={failing ? [] : payload.faces} frameSize={failing ? [16, 9] : payload.frame_size}>
          {preview && !failing ? (
            <img src={preview} alt="Live camera view" className="h-full w-full object-fill" />
          ) : (
            <p className="absolute inset-0 flex items-center justify-center px-4 text-center text-sm text-white/80">
              {failing ? 'No picture from the camera.' : 'Waiting for the first frame…'}
            </p>
          )}
        </FaceOverlay>
        {failing ? (
          <div className="mt-3">
            <Alert>{payload.error || 'The camera is not responding.'} The worker keeps retrying.</Alert>
          </div>
        ) : (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm" aria-live="polite">
            <Counts faces={payload.faces} />
            <span className="tabular-nums text-muted">
              {payload.fps} frames/s · {Math.round(payload.latency_ms)} ms per frame
            </span>
          </div>
        )}
        <p className="mt-2 text-xs text-muted">Frames are analysed and discarded; no video is stored.</p>
      </Card>
    )
  }

  return (
    <Card title="Live capture">
      {useBrowser ? (
        <BrowserCapture sessionId={sessionId} onChanged={onChanged} />
      ) : (
        <div className="space-y-3 text-sm">
          <Alert tone="warn">No camera worker is sending updates for this session.</Alert>
          <p className="text-muted">
            Start the worker on the computer that has the camera, and this view will switch to it automatically:
          </p>
          <pre className="overflow-x-auto rounded-md bg-canvas px-3 py-2 text-xs">python manage.py run_camera_worker</pre>
          <p className="text-muted">
            The worker serves the active session in its camera's room. A camera with no room serves sessions with no room.
          </p>
          <Button variant="secondary" onClick={() => setUseBrowser(true)}>
            <Camera size={16} aria-hidden="true" />
            Use this browser's camera instead
          </Button>
        </div>
      )}
    </Card>
  )
}
