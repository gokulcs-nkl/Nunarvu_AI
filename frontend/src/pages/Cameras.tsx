import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { Alert, Badge, Button, Card, EmptyState, Input, PageHeader, Spinner } from '../components/ui'
import { api, apiList, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { CameraDevice, Room } from '../lib/types'

const errorText = (error: unknown) => (error instanceof ApiError ? error.message : 'Something went wrong.')

const SOURCE_TYPES: Record<CameraDevice['source_type'], { label: string; hint: string; placeholder: string }> = {
  webcam: { label: 'Built-in or USB webcam', hint: 'Device number. The first webcam is 0.', placeholder: '0' },
  rtsp: { label: 'IP camera (RTSP)', hint: 'Stream address from the camera or a phone camera app.', placeholder: 'rtsp://192.168.1.20:554/stream' },
  http: { label: 'IP camera (HTTP stream)', hint: 'MJPEG or similar stream address.', placeholder: 'http://192.168.1.20:8080/video' },
  file: { label: 'Recorded video file', hint: 'Path on the computer that runs the worker. Plays in a loop.', placeholder: 'C:\\videos\\classroom.mp4' },
}
const STATUS_TONE = { online: 'ok', offline: 'neutral', error: 'danger' } as const
const STATUS_LABEL = { online: 'Online', offline: 'Offline', error: 'Camera error' } as const

type Draft = Pick<CameraDevice, 'name' | 'source_type' | 'source' | 'room' | 'is_enabled'>
const EMPTY: Draft = { name: '', source_type: 'webcam', source: '0', room: null, is_enabled: true }

/** Hide any password embedded in a stream address. */
function maskSource(source: string): string {
  return source.replace(/(:\/\/[^:/@]+):[^@/]+@/, '$1:••••@')
}

function CameraForm({ camera, rooms, onDone }: { camera: CameraDevice | null; rooms: Room[]; onDone: () => void }) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<Draft>(
    camera
      ? { name: camera.name, source_type: camera.source_type, source: camera.source, room: camera.room, is_enabled: camera.is_enabled }
      : EMPTY,
  )
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft({ ...draft, [key]: value })
  const spec = SOURCE_TYPES[draft.source_type]

  const save = useMutation({
    mutationFn: () =>
      camera
        ? api<CameraDevice>(`/cameras/${camera.id}/`, { method: 'PATCH', body: draft })
        : api<CameraDevice>('/cameras/', { method: 'POST', body: draft }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['cameras'] })
      onDone()
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }
  const selectClass = 'h-9 w-full rounded-md border border-line bg-surface px-2 text-sm'

  return (
    <Card
      title={camera ? `Edit ${camera.name}` : 'Add camera'}
      action={
        <Button variant="ghost" aria-label="Close form" onClick={onDone}>
          <X size={16} aria-hidden="true" />
        </Button>
      }
    >
      <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="camera-name" className="mb-1 block text-sm font-medium">
            Name
          </label>
          <Input id="camera-name" required value={draft.name} onChange={(event) => set('name', event.target.value)} />
        </div>
        <div>
          <label htmlFor="camera-type" className="mb-1 block text-sm font-medium">
            Type
          </label>
          <select
            id="camera-type"
            className={selectClass}
            value={draft.source_type}
            onChange={(event) => {
              const type = event.target.value as CameraDevice['source_type']
              setDraft({ ...draft, source_type: type, source: type === 'webcam' ? '0' : '' })
            }}
          >
            {Object.entries(SOURCE_TYPES).map(([value, item]) => (
              <option key={value} value={value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="camera-source" className="mb-1 block text-sm font-medium">
            Source
          </label>
          <Input
            id="camera-source"
            required
            placeholder={spec.placeholder}
            aria-describedby="camera-source-hint"
            value={draft.source}
            onChange={(event) => set('source', event.target.value)}
          />
          <p id="camera-source-hint" className="mt-1 text-xs text-muted">
            {spec.hint}
          </p>
        </div>
        <div>
          <label htmlFor="camera-room" className="mb-1 block text-sm font-medium">
            Room (optional)
          </label>
          <select
            id="camera-room"
            className={selectClass}
            value={draft.room ?? ''}
            onChange={(event) => set('room', event.target.value ? Number(event.target.value) : null)}
          >
            <option value="">No room</option>
            {rooms.map((room) => (
              <option key={room.id} value={room.id}>
                {room.name}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-muted">The camera serves the active session in this room.</p>
        </div>
        <label className="flex items-center gap-2 self-center text-sm">
          <input type="checkbox" checked={draft.is_enabled} onChange={(event) => set('is_enabled', event.target.checked)} />
          Enabled (the worker runs this camera)
        </label>
        {save.error && (
          <div className="sm:col-span-2">
            <Alert>{errorText(save.error)}</Alert>
          </div>
        )}
        <div className="flex gap-2 sm:col-span-2">
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
          <Button variant="secondary" onClick={onDone}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  )
}

interface TestResult {
  ok: boolean
  detail: string
}

function CameraRow({ camera, roomName, isAdmin, onEdit }: { camera: CameraDevice; roomName: string; isAdmin: boolean; onEdit: () => void }) {
  const queryClient = useQueryClient()
  const [preview, setPreview] = useState<string | null>(null)
  const test = useMutation({
    mutationFn: () => api<TestResult>(`/cameras/${camera.id}/test/`, { method: 'POST' }),
    onSuccess: (result) => setPreview(result.ok ? `/api/v1/cameras/${camera.id}/snapshot/?t=${Date.now()}` : null),
  })
  const remove = useMutation({
    mutationFn: () => api<void>(`/cameras/${camera.id}/`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cameras'] }),
  })

  return (
    <li className="py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 text-sm">
          <p className="flex flex-wrap items-center gap-2 font-medium">
            {camera.name}
            <Badge tone={STATUS_TONE[camera.status]}>{STATUS_LABEL[camera.status]}</Badge>
            {!camera.is_enabled && <Badge tone="warn">Disabled</Badge>}
          </p>
          <p className="truncate text-muted">
            {SOURCE_TYPES[camera.source_type].label} · {maskSource(camera.source)} · {roomName}
          </p>
          {camera.status === 'online' && camera.fps !== null && (
            <p className="tabular-nums text-muted">
              {camera.fps} frames/s · {Math.round(camera.latency_ms ?? 0)} ms per frame
            </p>
          )}
          {camera.status === 'error' && camera.last_error && <p className="text-danger">{camera.last_error}</p>}
        </div>
        {isAdmin && (
          <div className="flex gap-2">
            <Button variant="secondary" disabled={test.isPending} onClick={() => test.mutate()}>
              {test.isPending ? 'Testing…' : 'Test connection'}
            </Button>
            <Button variant="secondary" aria-label={`Edit ${camera.name}`} onClick={onEdit}>
              <Pencil size={16} aria-hidden="true" />
            </Button>
            <Button
              variant="danger"
              aria-label={`Delete ${camera.name}`}
              disabled={remove.isPending}
              onClick={() => {
                if (window.confirm(`Delete camera ${camera.name}?`)) remove.mutate()
              }}
            >
              <Trash2 size={16} aria-hidden="true" />
            </Button>
          </div>
        )}
      </div>
      {(test.data || test.error || remove.error) && (
        <div className="mt-2 max-w-xl space-y-2">
          {test.data && <Alert tone={test.data.ok ? 'ok' : 'danger'}>{test.data.detail}</Alert>}
          {test.error && <Alert>{errorText(test.error)}</Alert>}
          {remove.error && <Alert>{errorText(remove.error)}</Alert>}
          {preview && test.data?.ok && <img src={preview} alt={`Test frame from ${camera.name}`} className="max-h-56 rounded-md" />}
        </div>
      )}
    </li>
  )
}

export function Cameras() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [editing, setEditing] = useState<CameraDevice | 'new' | null>(null)
  // Status comes from the worker's heartbeat, so refresh it regularly.
  const cameras = useQuery({ queryKey: ['cameras'], queryFn: () => apiList<CameraDevice>('/cameras/'), refetchInterval: 5000 })
  const rooms = useQuery({ queryKey: ['rooms'], queryFn: () => apiList<Room>('/rooms/') })
  const roomName = (id: number | null) => (id === null ? 'No room' : (rooms.data?.find((room) => room.id === id)?.name ?? '…'))
  const anyOnline = cameras.data?.some((camera) => camera.status === 'online')

  return (
    <>
      <PageHeader
        title="Cameras"
        description="A background worker reads each enabled camera and records attendance for the session in its room."
        action={
          isAdmin && !editing ? (
            <Button onClick={() => setEditing('new')}>
              <Plus size={16} aria-hidden="true" />
              Add camera
            </Button>
          ) : undefined
        }
      />
      {editing && (
        <div className="mb-5">
          <CameraForm
            key={editing === 'new' ? 'new' : editing.id}
            camera={editing === 'new' ? null : editing}
            rooms={rooms.data ?? []}
            onDone={() => setEditing(null)}
          />
        </div>
      )}
      {cameras.data && cameras.data.length > 0 && !anyOnline && (
        <div className="mb-4">
          <Alert tone="warn">
            No camera worker is running. Start it on the computer that has the cameras with{' '}
            <code className="rounded bg-surface px-1">python manage.py run_camera_worker</code>.
          </Alert>
        </div>
      )}
      <Card>
        {cameras.isLoading && <Spinner />}
        {cameras.isError && <Alert>{errorText(cameras.error)}</Alert>}
        {cameras.data?.length === 0 && <EmptyState title="No cameras yet" hint={isAdmin ? 'Add a webcam or an IP camera.' : undefined} />}
        {cameras.data && cameras.data.length > 0 && (
          <ul className="divide-y divide-line">
            {cameras.data.map((camera) => (
              <CameraRow
                key={camera.id}
                camera={camera}
                roomName={roomName(camera.room)}
                isAdmin={isAdmin}
                onEdit={() => setEditing(camera)}
              />
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}
