import { useCallback, useEffect, useRef, useState } from 'react'

/** Browser webcam access: a <video> ref, start/stop controls, and a frame grabber. */
export function useCamera() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [active, setActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setActive(false)
  }, [])

  const start = useCallback(async () => {
    setError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('This browser cannot access a camera.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setActive(true)
    } catch (caught) {
      const name = caught instanceof DOMException ? caught.name : ''
      if (name === 'NotAllowedError') setError('Camera permission was denied. Allow it in the browser and try again.')
      else if (name === 'NotFoundError') setError('No camera was found on this device.')
      else if (name === 'NotReadableError') setError('The camera is in use by another program.')
      else setError('The camera could not be started.')
    }
  }, [])

  /** Current frame as a JPEG, or null if the camera is not delivering frames yet. */
  const capture = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return null
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d')?.drawImage(video, 0, 0)
    return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9))
  }, [])

  useEffect(() => stop, [stop])

  return { videoRef, active, error, start, stop, capture }
}
