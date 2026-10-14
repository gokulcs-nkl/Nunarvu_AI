import { useQuery } from '@tanstack/react-query'
import { ArrowRight, BarChart3, Check, Circle, ClipboardCheck, GraduationCap, Play, School, UserPlus, Users, Video } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { Stack3D, Tilt } from '../components/depth'
import { Alert, Badge, Card, EmptyState, IconTile, Spinner } from '../components/ui'
import { api, apiList } from '../lib/api'
import type { Page } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { ClassSession, Period, ReportSummary } from '../lib/types'
import { HealthAlerts, useSystemHealth } from './Health'

const today = () => new Date().toLocaleDateString('en-CA')
const shortTime = (value: string) => value.slice(0, 5)
const clock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

function useCount(key: string, path: string, enabled = true) {
  return useQuery({
    queryKey: [key, 'count'],
    queryFn: () => api<Page<unknown>>(path),
    enabled,
    select: (page) => page.count,
  })
}

const linkButton =
  'key inline-flex h-10 items-center gap-2 rounded-xl px-4 text-sm font-semibold'

function StatTile({ icon, label, value, note, to }: { icon: ReactNode; label: string; value: ReactNode; note?: string; to: string }) {
  return (
    <Tilt className="rounded-2xl">
      <Link to={to} className="panel block h-full rounded-2xl p-5 hover:border-muted/50">
        <div className="flex items-center gap-3">
          <IconTile>{icon}</IconTile>
          <p className="text-sm font-medium text-muted">{label}</p>
        </div>
        <p className="mt-4 text-3xl font-semibold tabular-nums tracking-tight">{value}</p>
        {note && <p className="mt-1 text-xs text-muted">{note}</p>}
      </Link>
    </Tilt>
  )
}

const RING = [
  { key: 'present', label: 'Present', color: 'var(--color-ok)' },
  { key: 'late', label: 'Late', color: 'var(--color-warn)' },
  { key: 'left_early', label: 'Left early', color: 'var(--color-brand)' },
  { key: 'absent', label: 'Absent', color: 'var(--color-danger)' },
  { key: 'pending', label: 'Pending review', color: 'var(--color-muted)' },
] as const

/** Today's attendance as a ring. Every segment is also listed with its label and count beside it. */
function AttendanceRing({ totals }: { totals: ReportSummary['totals'] }) {
  const radius = 54
  const circumference = 2 * Math.PI * radius
  const gap = 3
  let offset = 0
  const segments = RING.map((item) => ({ ...item, count: totals[item.key] })).filter((item) => item.count > 0)

  return (
    <div className="flex flex-wrap items-center gap-6">
      <div className="relative h-36 w-36 shrink-0">
        <svg viewBox="0 0 128 128" className="h-full w-full -rotate-90" role="img" aria-label="Ring chart of today's attendance; the figures are listed beside it">
          <circle cx="64" cy="64" r={radius} fill="none" stroke="var(--color-line)" strokeWidth="11" />
          {segments.map((segment) => {
            const length = (segment.count / totals.records) * circumference
            const dash = Math.max(length - gap, 1)
            const element = (
              <circle
                key={segment.key}
                cx="64"
                cy="64"
                r={radius}
                fill="none"
                stroke={segment.color}
                strokeWidth="11"
                strokeLinecap="butt"
                strokeDasharray={`${dash} ${circumference - dash}`}
                strokeDashoffset={-offset}
              />
            )
            offset += length
            return element
          })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-semibold tabular-nums">{totals.attendance_percent === null ? '–' : `${totals.attendance_percent}%`}</span>
          <span className="text-xs text-muted">attended</span>
        </div>
      </div>
      <ul className="min-w-40 flex-1 space-y-1.5 text-sm">
        {RING.map((item) => (
          <li key={item.key} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: item.color }} aria-hidden="true" />
              {item.label}
            </span>
            <span className="font-semibold tabular-nums">{totals[item.key]}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function SessionTimeline({ sessions }: { sessions: ClassSession[] }) {
  const ordered = [...sessions].sort((a, b) => a.starts_at.localeCompare(b.starts_at))
  const nextId = ordered.find((session) => session.status === 'scheduled')?.id

  return (
    <ol className="relative space-y-2 before:absolute before:bottom-3 before:left-[4.6rem] before:top-3 before:w-px before:bg-line">
      {ordered.map((session) => {
        const now = session.status === 'active'
        const done = session.status === 'closed'
        const next = session.id === nextId
        return (
          <li key={session.id} className="relative flex min-w-0 items-stretch gap-3 sm:gap-4">
            <div className="w-14 shrink-0 pt-3 text-right text-xs tabular-nums text-muted">
              <span className="block font-semibold text-ink">{clock(session.starts_at)}</span>
              {session.ends_at && <span>{clock(session.ends_at)}</span>}
            </div>
            <span
              className={`relative z-10 mt-3.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
                now ? 'border-brand bg-brand-soft' : done ? 'border-ok bg-ok-soft text-ok' : 'border-line bg-surface text-muted'
              }`}
              aria-hidden="true"
            >
              {done ? <Check size={11} strokeWidth={3.5} /> : now ? <Circle size={7} fill="currentColor" className="text-brand" /> : null}
            </span>
            <Link
              to={`/sessions/${session.id}`}
              className={`flex min-w-0 flex-1 items-center justify-between gap-3 rounded-xl border px-4 py-3 transition-colors ${
                now
                  ? 'border-brand/50 bg-brand-soft shadow-[0_10px_30px_-12px_rgb(111_155_255/0.5)]'
                  : 'border-transparent hover:border-line hover:bg-raised/60'
              } ${done ? 'opacity-70' : ''}`}
            >
              <div className="min-w-0">
                <p className="truncate font-semibold">
                  {session.subject_code} · {session.class_group_name}
                </p>
                <p className="text-xs text-muted">{session.period_number ? `Period ${session.period_number}` : 'Started by hand'}</p>
              </div>
              {now ? (
                <Badge tone="brand">Now</Badge>
              ) : done ? (
                <Badge>Done</Badge>
              ) : next ? (
                <Badge tone="ok">Up next</Badge>
              ) : session.status === 'cancelled' ? (
                <Badge tone="warn">Cancelled</Badge>
              ) : (
                <Badge>Later</Badge>
              )}
            </Link>
          </li>
        )
      })}
    </ol>
  )
}

export function Overview() {
  const { user } = useAuth()
  const isStaff = user?.role !== 'viewer'
  const isAdmin = user?.role === 'admin'
  const date = today()

  const classes = useCount('class-groups', '/class-groups/')
  const students = useCount('students', '/students/', isStaff)
  const health = useSystemHealth(isStaff)
  const sessions = useQuery({ queryKey: ['sessions', date], queryFn: () => apiList<ClassSession>(`/sessions/?date=${date}`) })
  const periods = useQuery({
    queryKey: ['periods', 'effective', date],
    queryFn: () => api<Period[]>(`/periods/effective/?date=${date}`),
  })
  const summary = useQuery({
    queryKey: ['report', 'summary', 'today', date],
    queryFn: () => api<ReportSummary>(`/reports/summary/?date_from=${date}&date_to=${date}`),
    enabled: isStaff,
  })

  const active = sessions.data?.find((session) => session.status === 'active')
  const upNext = sessions.data
    ?.filter((session) => session.status === 'scheduled')
    .sort((a, b) => a.starts_at.localeCompare(b.starts_at))[0]
  const waiting = health.data ? health.data.pending_attendance + health.data.unreviewed_observations : 0
  const camerasEnabled = health.data?.cameras.filter((camera) => camera.is_enabled) ?? []
  const camerasOnline = camerasEnabled.filter((camera) => camera.status === 'online').length
  const sessionCount = sessions.data?.length ?? 0

  return (
    <div className="min-w-0 space-y-6">
      {health.data && <HealthAlerts health={health.data} />}

      {/* Greeting banner */}
      <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-[linear-gradient(135deg,#2a3f8f_0%,#1c2a5c_45%,#141b22_100%)] p-6 shadow-[inset_0_1px_0_rgb(255_255_255/0.12),0_30px_60px_-30px_rgb(0_0_0/0.9)] md:p-8">
        <div className="pointer-events-none absolute -right-6 top-1/2 hidden -translate-y-1/2 lg:block">
          <Stack3D size={230} />
        </div>
        <div className="relative lg:pr-64">
          <p className="text-sm font-medium text-white/70">{new Date().toLocaleDateString(undefined, { dateStyle: 'full' })}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white md:text-4xl">
            {greeting()}, {user?.first_name || user?.username}
          </h1>
          <p className="mt-2 max-w-xl text-white/75">
            {sessionCount === 0
              ? 'No sessions yet today.'
              : `${sessionCount} session${sessionCount === 1 ? '' : 's'} today${active ? `, and ${active.subject_code} with ${active.class_group_name} is running now` : ''}.`}{' '}
            {isStaff && (waiting > 0 ? `${waiting} item${waiting === 1 ? ' is' : 's are'} waiting for your review.` : 'Nothing is waiting for review.')}
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            {active ? (
              <Link to={`/sessions/${active.id}`} className={`${linkButton} bg-white text-night hover:bg-white/90`}>
                <Play size={16} aria-hidden="true" />
                Open the running session
              </Link>
            ) : (
              isStaff && (
                <Link to="/sessions" className={`${linkButton} bg-white text-night hover:bg-white/90`}>
                  <Play size={16} aria-hidden="true" />
                  Start a session
                </Link>
              )
            )}
            {isAdmin && (
              <Link to="/students" className={`${linkButton} border border-white/25 bg-white/10 text-white hover:bg-white/15`}>
                <UserPlus size={16} aria-hidden="true" />
                Add a student
              </Link>
            )}
            {isStaff && (
              <Link to="/reports" className={`${linkButton} border border-white/25 bg-white/10 text-white hover:bg-white/15`}>
                <BarChart3 size={16} aria-hidden="true" />
                View reports
              </Link>
            )}
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {[
              { label: active ? 'Now' : 'Up next', value: active ? active.subject_code : upNext ? upNext.subject_code : 'Nothing scheduled', note: active ? active.class_group_name : upNext ? `${clock(upNext.starts_at)} · ${upNext.class_group_name}` : 'Start one by hand' },
              ...(isStaff
                ? [
                    { label: 'Waiting for review', value: String(waiting), note: health.data ? `${health.data.pending_attendance} attendance · ${health.data.unreviewed_observations} observations` : '' },
                    { label: 'Cameras', value: `${camerasOnline} of ${camerasEnabled.length} online`, note: camerasOnline === 0 ? 'Start the camera worker' : 'Recording attendance' },
                  ]
                : []),
            ].map((item) => (
              <div key={item.label} className="rounded-2xl border border-white/15 bg-white/[0.07] px-4 py-3 shadow-[inset_0_1px_0_rgb(255_255_255/0.08)] backdrop-blur-sm">
                <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-white/60">{item.label}</p>
                <p className="mt-1 truncate text-lg font-semibold text-white">{item.value}</p>
                <p className="truncate text-xs text-white/65">{item.note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Headline numbers */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile icon={<School size={18} />} label="Sessions today" value={sessions.data ? sessionCount : '–'} note={active ? '1 running now' : undefined} to="/sessions" />
        <StatTile icon={<GraduationCap size={18} />} label="Classes" value={classes.data ?? '–'} to="/setup" />
        {isStaff && <StatTile icon={<Users size={18} />} label="Students" value={students.data ?? '–'} note={health.data ? `${health.data.students.enrolled_faces} with an enrolled face` : undefined} to="/students" />}
        {isStaff && <StatTile icon={<Video size={18} />} label="Cameras online" value={health.data ? `${camerasOnline}/${camerasEnabled.length}` : '–'} to="/cameras" />}
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="min-w-0 lg:col-span-3">
          <Card
            title="Today's sessions"
            action={
              <Link to="/sessions" className="inline-flex items-center gap-1 text-sm font-semibold text-brand hover:text-brand-strong">
                All sessions
                <ArrowRight size={14} aria-hidden="true" />
              </Link>
            }
          >
            {sessions.isLoading && <Spinner />}
            {sessions.isError && <Alert>{sessions.error.message}</Alert>}
            {sessions.data && sessions.data.length === 0 && (
              <EmptyState
                title="No sessions today"
                hint={
                  user?.role === 'teacher'
                    ? 'You have no classes scheduled today.'
                    : 'Sessions appear here from the timetable, or when a teacher starts one by hand.'
                }
              />
            )}
            {sessions.data && sessions.data.length > 0 && <SessionTimeline sessions={sessions.data} />}
          </Card>
        </div>

        <div className="min-w-0 space-y-6 lg:col-span-2">
          {isStaff && (
            <Card
              title="Attendance today"
              action={
                <IconTile tone="ok">
                  <ClipboardCheck size={18} />
                </IconTile>
              }
            >
              {summary.isLoading && <Spinner />}
              {summary.data && summary.data.totals.records === 0 && <EmptyState title="No attendance recorded yet today" />}
              {summary.data && summary.data.totals.records > 0 && <AttendanceRing totals={summary.data.totals} />}
            </Card>
          )}

          <Card title="Today's period timings">
            {periods.isLoading && <Spinner />}
            {periods.isError && <Alert>{periods.error.message}</Alert>}
            {periods.data && periods.data.length === 0 && (
              <EmptyState
                title="No period timings set"
                hint="Timings are optional. Without them, teachers start and end sessions by hand."
                action={
                  <Link to="/settings/periods" className="text-sm font-semibold text-brand hover:text-brand-strong">
                    Set period timings
                  </Link>
                }
              />
            )}
            {periods.data && periods.data.length > 0 && (
              <ul className="divide-y divide-line">
                {periods.data.map((period) => (
                  <li key={period.id} className="flex items-center justify-between py-2.5 text-sm">
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
      </div>
    </div>
  )
}
