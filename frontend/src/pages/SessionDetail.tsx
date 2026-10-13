import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { LivePanel } from '../components/LivePanel'
import { Alert, Badge, Button, Card, EmptyState, PageHeader, Spinner } from '../components/ui'
import { api, apiList, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import { STATUS_LABEL } from '../lib/types'
import type { AttendanceRecord, AttendanceStatus, ClassSession, Student } from '../lib/types'
import { STATUS_TONE } from './Sessions'

const errorText = (error: unknown) => (error instanceof ApiError ? error.message : 'Something went wrong.')
const clock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const RECORD_TONE = { pending: 'warn', present: 'ok', late: 'ok', left_early: 'warn', absent: 'danger' } as const

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
        {canEdit && data.status === 'active' && <LivePanel sessionId={sessionId} onChanged={refreshRecords} />}

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
