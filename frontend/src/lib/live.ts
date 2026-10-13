import { useEffect, useRef, useState } from 'react'

import type { LivePayload } from './types'

const RECONNECT_MS = 3000
/** A worker that has been silent this long is treated as not running. */
export const LIVE_TIMEOUT_MS = 6000

/**
 * Live worker updates for one session over a WebSocket. Reconnects by itself, and
 * reports `live: false` when no update has arrived recently.
 */
export function useSessionLive(sessionId: number, enabled: boolean) {
  const [payload, setPayload] = useState<LivePayload | null>(null)
  const [live, setLive] = useState(false)
  const lastMessage = useRef(0)

  useEffect(() => {
    if (!enabled) return
    let socket: WebSocket | null = null
    let retry: number | undefined
    let closed = false

    const connect = () => {
      const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
      socket = new WebSocket(`${scheme}://${window.location.host}/ws/sessions/${sessionId}/`)
      socket.onmessage = (event) => {
        lastMessage.current = Date.now()
        setPayload(JSON.parse(event.data as string) as LivePayload)
        setLive(true)
      }
      socket.onclose = (event) => {
        // 4401 and 4403 mean the server refused us; retrying would not help.
        if (!closed && event.code !== 4401 && event.code !== 4403) retry = window.setTimeout(connect, RECONNECT_MS)
      }
    }
    connect()

    const watchdog = window.setInterval(() => {
      if (Date.now() - lastMessage.current > LIVE_TIMEOUT_MS) setLive(false)
    }, 1000)

    return () => {
      closed = true
      window.clearTimeout(retry)
      window.clearInterval(watchdog)
      socket?.close()
      setLive(false)
      setPayload(null)
    }
  }, [sessionId, enabled])

  return { payload, live }
}

/** Latest preview frame of a worker-run camera, refreshed without flicker. */
export function useCameraPreview(cameraId: number | null, intervalMs = 500) {
  const [src, setSrc] = useState<string | null>(null)

  useEffect(() => {
    if (cameraId === null) return
    let cancelled = false
    const refresh = () => {
      const image = new Image()
      image.onload = () => {
        if (!cancelled) setSrc(image.src)
      }
      image.src = `/api/v1/cameras/${cameraId}/snapshot/?t=${Date.now()}`
    }
    refresh()
    const timer = window.setInterval(refresh, intervalMs)
    return () => {
      cancelled = true
      window.clearInterval(timer)
      setSrc(null)
    }
  }, [cameraId, intervalMs])

  return src
}
