import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { Alert, Badge, Card, EmptyState, PageHeader, Spinner } from '../components/ui'
import { api } from '../lib/api'
import type { Page } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { ClassSession, Period } from '../lib/types'
import { HealthAlerts, useSystemHealth } from './Health'

const today = () => new Date().toLocaleDateString('en-CA')
const shortTime = (value: string) => value.slice(0, 5)
const clock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const STATUS_TONE = { scheduled: 'neutral', active: 'ok', closed: 'brand', cancelled: 'warn' } as const

function useCount(key: string, path: string, enabled = true) {
  return useQuery({
    queryKey: [key, 'count'],
    queryFn: () => api<Page<unknown>>(path),
    enabled,
    select: (page) => page.count,
  })
}

function Stat({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value ?? '–'}</p>
    </div>
  )
}

export function Overview() {
  const { user } = useAuth()
  const isStaff = user?.role !== 'viewer'
  const date = today()

  const classes = useCount('class-groups', '/class-groups/')
  const students = useCount('students', '/students/', isStaff)
  const cameras = useCount('cameras', '/cameras/', isStaff)
  const sessions = useQuery({
    queryKey: ['sessions', date],
    queryFn: () => api<Page<ClassSession>>(`/sessions/?date=${date}`),
  })
  const health = useSystemHealth(isStaff)
  const periods = useQuery({
    queryKey: ['periods', 'effective', date],
    queryFn: () => api<Period[]>(`/periods/effective/?date=${date}`),
  })

  return (
    <>
      <PageHeader title="Overview" description={new Date().toLocaleDateString(undefined, { dateStyle: 'full' })} />

      {health.data && health.data.alerts.length > 0 && (
        <div className="mb-4">
          <HealthAlerts health={health.data} />
        </div>
      )}
      {health.data && health.data.pending_attendance + health.data.unreviewed_observations > 0 && (
        <p className="mb-4 text-sm text-muted">
          Waiting for review:{' '}
          <Link to="/sessions" className="font-medium text-brand hover:underline">
            {health.data.pending_attendance} attendance
          </Link>{' '}
          and{' '}
          <Link to="/observations" className="font-medium text-brand hover:underline">
            {health.data.unreviewed_observations} observations
          </Link>
          .
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Classes" value={classes.data} />
        {isStaff && <Stat label="Students" value={students.data} />}
        {isStaff && <Stat label="Cameras" value={cameras.data} />}
        <Stat label="Sessions today" value={sessions.data?.count} />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card title="Today's sessions">
          {sessions.isLoading && <Spinner />}
          {sessions.isError && <Alert>{sessions.error.message}</Alert>}
          {sessions.data && sessions.data.results.length === 0 && (
            <EmptyState
              title="No sessions today"
              hint={
                user?.role === 'teacher'
                  ? 'You have no classes scheduled today.'
                  : 'Sessions appear here once a timetable is set up and generated, or when a teacher starts one manually.'
              }
            />
          )}
          {sessions.data && sessions.data.results.length > 0 && (
            <ul className="divide-y divide-line">
              {sessions.data.results.map((session) => (
                <li key={session.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                  <div>
                    <p className="font-medium">
                      {session.class_group_name} · {session.subject_code}
                    </p>
                    <p className="text-muted">
                      {session.period_number ? `Period ${session.period_number} · ` : ''}
                      {clock(session.starts_at)}
                      {session.ends_at ? `–${clock(session.ends_at)}` : ''}
                    </p>
                  </div>
                  <Badge tone={STATUS_TONE[session.status]}>{session.status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Today's period timings">
          {periods.isLoading && <Spinner />}
          {periods.isError && <Alert>{periods.error.message}</Alert>}
          {periods.data && periods.data.length === 0 && (
            <EmptyState
              title="No period timings set"
              hint="Timings are optional. Without them, teachers start and end sessions manually."
              action={
                <Link to="/settings/periods" className="text-sm font-medium text-brand hover:underline">
                  Set period timings
                </Link>
              }
            />
          )}
          {periods.data && periods.data.length > 0 && (
            <ul className="divide-y divide-line">
              {periods.data.map((period) => (
                <li key={period.id} className="flex items-center justify-between py-2 text-sm">
                  <span className="font-medium">{period.name || `Period ${period.number}`}</span>
                  <span className="tabular-nums text-muted">
                    {shortTime(period.start_time)}–{shortTime(period.end_time)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  )
}
