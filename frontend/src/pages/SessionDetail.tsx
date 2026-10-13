import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Camera, CameraOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Alert, Badge, Button, Card, EmptyState, PageHeader, Spinner } from '../components/ui'
import { api, apiList, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCamera } from '../lib/camera'
import { STATUS_LABEL } from '../lib/types'
import type { AttendanceRecord, AttendanceStatus, ClassSession, RecognizedFace, RecognizeResult, Student } from '../lib/types'
import { STATUS_TONE } from './Sessions'

const SCAN_INTERVAL_MS = 2000
const errorText = (error: unknown) => (error instanceof ApiError ? error.message : 'Something went wrong.')
const clock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const RECORD_TONE = { pending: 'warn', present: 'ok', late: 'ok', left_early: 'warn', absent: 'danger' } as const
// Colour is paired with a text label on every box, so it never carries meaning alone.
const BAND_STYLE = {
  confirmed: { border: '#17794a', label: 'Confirmed' },
  review: { border: '#8a5a00', label: 'Needs review' },
  unknown: { border: '#5b6676', label: 'Unrecognised' },
} as const

function LiveCapture({ sessionId, onChanged }: { sessionId: number; onChanged: () => void }) {
  const camera = useCamera()
  const [faces, setFaces] = useState<RecognizedFace[]>([])
  const [frameSize, setFrameSize] = useState<[number, number]>([1, 1])
  const [enrolled, setEnrolled] = useState<number | null>(null)
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
        setEnrolled(result.enrolled_students)
        setError(null)
        if (result.changed.length > 0) notifyChanged.current()
      } catch (caught) {
        setError(errorText(caught))
      } finally {
        busy.current = false
      }
    }, SCAN_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [active, capture, videoRef, sessionId])

  const counts = { confirmed: 0, review: 0, unknown: 0 }
  for (const face of faces) counts[face.band] += 1

  return (
    <Card
      title="Live capture"
      action={
        camera.active ? (
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
        )
      }
    >
      <div className="relative aspect-video overflow-hidden rounded-md bg-ink">
        <video ref={camera.videoRef} muted playsInline className="h-full w-full object-fill" />
        {camera.active &&
          faces.map((face, index) => {
            const [x1, y1, x2, y2] = face.box
            const style = BAND_STYLE[face.band]
            return (
              <div
                key={index}
                className="absolute border-2"
                style={{
                  borderColor: style.border,
                  left: `${(x1 / frameSize[0]) * 100}%`,
                  top: `${(y1 / frameSize[1]) * 100}%`,
                  width: `${((x2 - x1) / frameSize[0]) * 100}%`,
                  height: `${((y2 - y1) / frameSize[1]) * 100}%`,
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
        {!camera.active && (
          <p className="absolute inset-0 flex items-center justify-center px-4 text-center text-sm text-white/80">
            Camera is off. Frames are analysed and discarded; no video is stored.
          </p>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm" aria-live="polite">
        <Badge tone="ok">{counts.confirmed} confirmed</Badge>
        <Badge tone="warn">{counts.review} need review</Badge>
        <Badge>{counts.unknown} unrecognised</Badge>
        {enrolled !== null && <span className="text-muted">{enrolled} enrolled in this class</span>}
      </div>
      {enrolled === 0 && (
        <div className="mt-3">
          <Alert tone="warn">No student in this class has an enrolled face yet, so nobody can be recognised.</Alert>
        </div>
      )}
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
    </Card>
  )
}

export function SessionDetail() {
  const { id } = useParams()
  const sessionId = Number(id)
  const { user } = useAuth()
  const canEdit = user?.role !== 'viewer'
  const queryClient = useQueryClient()

  const session = useQuery({ queryKey: ['session', sessionId], queryFn: () => api<ClassSession>(`/sessions/${sessionId}/`) })
  const records = useQuery({
    queryKey: ['attendance', sessionId],
    queryFn: () => apiList<AttendanceRecord>(`/attendance/?session=${sessionId}`),
  })
  const roster = useQuery({
    queryKey: ['roster', session.data?.class_group],
    queryFn: () => apiList<Student>(`/students/?class_group=${session.data!.class_group}`),
    enabled: canEdit && !!session.data,
  })

  const refreshRecords = () => queryClient.invalidateQueries({ queryKey: ['attendance', sessionId] })
  const refreshSession = () => {
    void queryClient.invalidateQueries({ queryKey: ['session', sessionId] })
    void queryClient.invalidateQueries({ queryKey: ['sessions'] })
    void refreshRecords()
  }
  const transition = useMutation({
    mutationFn: (action: 'start' | 'close') => api<ClassSession>(`/sessions/${sessionId}/${action}/`, { method: 'POST' }),
    onSuccess: refreshSession,
  })
  const mark = useMutation({
    mutationFn: ({ student, record, status }: { student: number; record?: AttendanceRecord; status: AttendanceStatus }) =>
      record
        ? api<AttendanceRecord>(`/attendance/${record.id}/`, { method: 'PATCH', body: { status } })
        : api<AttendanceRecord>('/attendance/', { method: 'POST', body: { session: sessionId, student, status } }),
    onSuccess: refreshRecords,
  })

  if (session.isLoading) return <Spinner />
  if (session.isError || !session.data) {
    return (
      <EmptyState
        title="Session not found"
        hint="It may belong to another teacher."
        action={
          <Link to="/sessions" className="text-sm font-medium text-brand hover:underline">
            Back to sessions
          </Link>
        }
      />
    )
  }

  const data = session.data
  const byStudent = new Map((records.data ?? []).map((record) => [record.student, record]))
  // Teachers and administrators see the full roster; viewers see only recorded rows.
  const rows = roster.data
    ? roster.data.map((student) => ({
        student: student.id,
        roll: student.roll_number,
        name: student.full_name,
        record: byStudent.get(student.id),
      }))
    : (records.data ?? []).map((record) => ({
        student: record.student,
        roll: record.roll_number,
        name: record.student_name,
        record,
      }))
  const pending = rows.filter((row) => row.record?.status === 'pending')
  const tally = (status: AttendanceStatus) => rows.filter((row) => row.record?.status === status).length

  return (
    <>
      <PageHeader
        title={`${data.class_group_name} · ${data.subject_code}`}
        description={`${new Date(data.starts_at).toLocaleDateString(undefined, { dateStyle: 'medium' })} · ${
          data.period_number ? `Period ${data.period_number}` : 'Manual session'
        } · ${clock(data.starts_at)}${data.ends_at ? `–${clock(data.ends_at)}` : ''}`}
        action={
          <div className="flex items-center gap-2">
            <Badge tone={STATUS_TONE[data.status]}>{data.status}</Badge>
            {canEdit && data.status === 'scheduled' && (
              <Button disabled={transition.isPending} onClick={() => transition.mutate('start')}>
                Start session
              </Button>
            )}
            {canEdit && data.status === 'active' && (
              <Button
                variant="secondary"
                disabled={transition.isPending}
                onClick={() => {
                  if (window.confirm('End this session? Students without a record will be marked absent.')) transition.mutate('close')
                }}
              >
                End session
              </Button>
            )}
          </div>
        }
      />
      {transition.error && (
        <div className="mb-4">
          <Alert>{errorText(transition.error)}</Alert>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        {canEdit && data.status === 'active' && <LiveCapture sessionId={sessionId} onChanged={refreshRecords} />}

        <div className="space-y-5">
          {pending.length > 0 && (
            <Card title={`Needs your review (${pending.length})`}>
              <ul className="divide-y divide-line">
                {pending.map((row) => (
                  <li key={row.student} className="flex flex-wrap items-center justify-between gap-3 py-2 text-sm">
                    <div>
                      <p className="font-medium">
                        {row.name} <span className="font-normal text-muted">{row.roll}</span>
                      </p>
                      <p className="text-muted">
                        {row.record?.note || 'Uncertain match.'}
                        {row.record?.confidence != null ? ` Score ${row.record.confidence.toFixed(2)}.` : ''}
                      </p>
                    </div>
                    {canEdit && (
                      <div className="flex gap-2">
                        <Button
                          variant="secondary"
                          disabled={mark.isPending}
                          onClick={() => mark.mutate({ student: row.student, record: row.record, status: 'present' })}
                        >
                          Mark present
                        </Button>
                        <Button
                          variant="secondary"
                          disabled={mark.isPending}
                          onClick={() => mark.mutate({ student: row.student, record: row.record, status: 'absent' })}
                        >
                          Mark absent
                        </Button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card title="Attendance">
            <div className="mb-3 flex flex-wrap gap-2 text-sm">
              <Badge tone="ok">{tally('present')} present</Badge>
              <Badge tone="ok">{tally('late')} late</Badge>
              <Badge tone="warn">{tally('left_early')} left early</Badge>
              <Badge tone="danger">{tally('absent')} absent</Badge>
              <Badge tone="warn">{tally('pending')} pending</Badge>
              <Badge>{rows.filter((row) => !row.record).length} not yet seen</Badge>
            </div>
            {(records.isLoading || roster.isLoading) && <Spinner />}
            {mark.error && <Alert>{errorText(mark.error)}</Alert>}
            {!records.isLoading && !roster.isLoading && rows.length === 0 && (
              <EmptyState title="No students in this class" hint="Add students to the class on the Students page." />
            )}
            {rows.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[30rem] text-left text-sm">
                  <thead>
                    <tr className="text-xs text-muted">
                      <th className="pb-2 pr-3 font-medium">Roll no.</th>
                      <th className="pb-2 pr-3 font-medium">Name</th>
                      <th className="pb-2 pr-3 font-medium">Status</th>
                      <th className="pb-2 pr-3 font-medium">Marked by</th>
                      {canEdit && <th className="pb-2 font-medium">Change</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.student} className="border-t border-line">
                        <td className="py-2 pr-3 tabular-nums">{row.roll}</td>
                        <td className="py-2 pr-3 font-medium">{row.name}</td>
                        <td className="py-2 pr-3">
                          {row.record ? (
                            <Badge tone={RECORD_TONE[row.record.status]}>{STATUS_LABEL[row.record.status]}</Badge>
                          ) : (
                            <Badge>Not yet seen</Badge>
                          )}
                        </td>
                        <td className="py-2 pr-3 text-muted">
                          {row.record ? (row.record.source === 'auto' ? 'Camera' : 'Teacher') : '–'}
                        </td>
                        {canEdit && (
                          <td className="py-2">
                            <select
                              aria-label={`Set status for ${row.name}`}
                              className="h-9 rounded-md border border-line bg-surface px-2 text-sm"
                              value={row.record?.status ?? ''}
                              disabled={mark.isPending}
                              onChange={(event) =>
                                mark.mutate({ student: row.student, record: row.record, status: event.target.value as AttendanceStatus })
                              }
                            >
                              {!row.record && <option value="">Set status</option>}
                              {(['present', 'late', 'left_early', 'absent'] as const).map((status) => (
                                <option key={status} value={status}>
                                  {STATUS_LABEL[status]}
                                </option>
                              ))}
                              {row.record?.status === 'pending' && <option value="pending">Pending review</option>}
                            </select>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  )
}
