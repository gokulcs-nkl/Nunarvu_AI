import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Alert, Badge, Button, Card, EmptyState, Input, PageHeader, Spinner } from '../components/ui'
import { api, apiList, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { ClassGroup, ClassSession, Subject } from '../lib/types'

const today = () => new Date().toLocaleDateString('en-CA')
const clock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const errorText = (error: unknown) => (error instanceof ApiError ? error.message : 'Something went wrong.')
export const STATUS_TONE = { scheduled: 'neutral', active: 'ok', closed: 'brand', cancelled: 'warn' } as const

function NewSessionForm({ onDone }: { onDone: () => void }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [classGroup, setClassGroup] = useState('')
  const [subject, setSubject] = useState('')
  const classes = useQuery({ queryKey: ['class-groups'], queryFn: () => apiList<ClassGroup>('/class-groups/') })
  const subjects = useQuery({ queryKey: ['subjects'], queryFn: () => apiList<Subject>('/subjects/') })

  const create = useMutation({
    mutationFn: async () => {
      const session = await api<ClassSession>('/sessions/', {
        method: 'POST',
        body: { class_group: Number(classGroup), subject: Number(subject), date: today(), starts_at: new Date().toISOString() },
      })
      return api<ClassSession>(`/sessions/${session.id}/start/`, { method: 'POST' })
    },
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: ['sessions'] })
      navigate(`/sessions/${session.id}`)
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    create.mutate()
  }
  const selectClass = 'h-9 w-full rounded-md border border-line bg-surface px-2 text-sm'

  return (
    <Card title="Start a session now">
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <div className="min-w-40 flex-1">
          <label htmlFor="session-class" className="mb-1 block text-xs text-muted">
            Class
          </label>
          <select id="session-class" required className={selectClass} value={classGroup} onChange={(event) => setClassGroup(event.target.value)}>
            <option value="">Choose a class</option>
            {classes.data?.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name} ({group.academic_year})
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-40 flex-1">
          <label htmlFor="session-subject" className="mb-1 block text-xs text-muted">
            Subject
          </label>
          <select id="session-subject" required className={selectClass} value={subject} onChange={(event) => setSubject(event.target.value)}>
            <option value="">Choose a subject</option>
            {subjects.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} · {item.name}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? 'Starting…' : 'Start session'}
        </Button>
        <Button variant="secondary" onClick={onDone}>
          Cancel
        </Button>
      </form>
      {create.error && (
        <div className="mt-3">
          <Alert>{errorText(create.error)}</Alert>
        </div>
      )}
    </Card>
  )
}

export function Sessions() {
  const { user } = useAuth()
  const canRun = user?.role !== 'viewer'
  const [date, setDate] = useState(today())
  const [creating, setCreating] = useState(false)
  const sessions = useQuery({
    queryKey: ['sessions', date],
    queryFn: () => apiList<ClassSession>(`/sessions/?date=${date}`),
  })

  return (
    <>
      <PageHeader
        title="Sessions"
        description="Each session is one taught period for one class. Attendance is recorded per session."
        action={
          canRun && !creating ? (
            <Button onClick={() => setCreating(true)}>
              <Plus size={16} aria-hidden="true" />
              Start a session
            </Button>
          ) : undefined
        }
      />
      {creating && (
        <div className="mb-5">
          <NewSessionForm onDone={() => setCreating(false)} />
        </div>
      )}
      <Card
        title="Sessions"
        action={<Input type="date" aria-label="Date" className="w-40" value={date} onChange={(event) => setDate(event.target.value || today())} />}
      >
        {sessions.isLoading && <Spinner />}
        {sessions.isError && <Alert>{errorText(sessions.error)}</Alert>}
        {sessions.data?.length === 0 && (
          <EmptyState
            title="No sessions on this date"
            hint={canRun ? 'Start one manually, or generate sessions from the timetable.' : undefined}
          />
        )}
        {sessions.data && sessions.data.length > 0 && (
          <ul className="divide-y divide-line">
            {sessions.data.map((session) => (
              <li key={session.id}>
                <Link to={`/sessions/${session.id}`} className="flex items-center justify-between gap-3 py-3 text-sm hover:bg-canvas">
                  <div>
                    <p className="font-medium">
                      {session.class_group_name} · {session.subject_code}
                    </p>
                    <p className="text-muted">
                      {session.period_number ? `Period ${session.period_number} · ` : 'Manual · '}
                      {clock(session.starts_at)}
                      {session.ends_at ? `–${clock(session.ends_at)}` : ''}
                    </p>
                  </div>
                  <Badge tone={STATUS_TONE[session.status]}>{session.status}</Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}
