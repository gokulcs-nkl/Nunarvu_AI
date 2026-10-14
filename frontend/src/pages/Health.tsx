import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { Alert, Badge, Card, EmptyState, PageHeader, Spinner } from '../components/ui'
import { api } from '../lib/api'
import type { SystemHealth } from '../lib/types'

const STATUS_TONE = { online: 'ok', offline: 'neutral', error: 'danger' } as const
const STATUS_LABEL = { online: 'Online', offline: 'Offline', error: 'Camera error' } as const

export function useSystemHealth(enabled = true) {
  return useQuery({
    queryKey: ['system-health'],
    queryFn: () => api<SystemHealth>('/system/health/'),
    refetchInterval: 10000,
    enabled,
  })
}

/** Problems that need someone's attention now. Shown on the overview and the health page. */
export function HealthAlerts({ health }: { health: SystemHealth }) {
  if (health.alerts.length === 0) return null
  return (
    <div className="space-y-2">
      {health.alerts.map((alert) => (
        <Alert key={`${alert.camera}-${alert.message}`} tone="warn">
          {alert.message}
        </Alert>
      ))}
    </div>
  )
}

function Stat({ label, value, to }: { label: string; value: number; to?: string }) {
  const body = (
    <>
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
    </>
  )
  const className = 'block rounded-lg border border-line bg-surface px-4 py-3'
  return to ? (
    <Link to={to} className={`${className} hover:border-brand`}>
      {body}
    </Link>
  ) : (
    <div className={className}>{body}</div>
  )
}

export function Health() {
  const health = useSystemHealth()

  return (
    <>
      <PageHeader title="System health" description="Cameras, processing speed and what is waiting for a person. Refreshes every ten seconds." />
      {health.isLoading && <Spinner />}
      {health.isError && <Alert>Could not load system health.</Alert>}
      {health.data && (
        <div className="space-y-5">
          <HealthAlerts health={health.data} />

          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <Stat label="Attendance pending review" value={health.data.pending_attendance} to="/sessions" />
            <Stat label="Observations not reviewed" value={health.data.unreviewed_observations} to="/observations" />
            <Stat label="Active students" value={health.data.students.active} />
            <Stat label="With consent recorded" value={health.data.students.with_consent} />
            <Stat label="With an enrolled face" value={health.data.students.enrolled_faces} />
          </div>

          <Card title={`Cameras, last ${health.data.window_hours} hours`}>
            {health.data.cameras.length === 0 && <EmptyState title="No cameras yet" />}
            {health.data.cameras.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[40rem] text-left text-sm">
                  <thead>
                    <tr className="text-xs text-muted">
                      <th className="pb-2 pr-3 font-medium">Camera</th>
                      <th className="pb-2 pr-3 font-medium">Status</th>
                      <th className="pb-2 pr-3 text-right font-medium">Uptime</th>
                      <th className="pb-2 pr-3 text-right font-medium">Frames/s</th>
                      <th className="pb-2 pr-3 text-right font-medium">ms per frame</th>
                      <th className="pb-2 font-medium">Last change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {health.data.cameras.map((camera) => (
                      <tr key={camera.id} className="border-t border-line">
                        <td className="py-2 pr-3">
                          <span className="font-medium">{camera.name}</span>
                          <span className="block text-xs text-muted">
                            {camera.room ?? 'No room'}
                            {camera.is_enabled ? '' : ' · disabled'}
                          </span>
                        </td>
                        <td className="py-2 pr-3">
                          <Badge tone={STATUS_TONE[camera.status]}>{STATUS_LABEL[camera.status]}</Badge>
                        </td>
                        <td className="py-2 pr-3 text-right tabular-nums">{camera.uptime_percent}%</td>
                        <td className="py-2 pr-3 text-right tabular-nums">{camera.fps ?? '–'}</td>
                        <td className="py-2 pr-3 text-right tabular-nums">{camera.latency_ms === null ? '–' : Math.round(camera.latency_ms)}</td>
                        <td className="py-2 text-muted">
                          {camera.last_change
                            ? `${STATUS_LABEL[camera.last_change.status]} at ${new Date(camera.last_change.at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}${camera.last_change.detail ? `: ${camera.last_change.detail}` : ''}`
                            : 'Never run'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="mt-3 text-xs text-muted">Uptime is the share of the period in which the camera worker reported the camera as online.</p>
          </Card>

          <Card title="Models in use">
            <dl className="grid gap-3 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-xs text-muted">Face detection and recognition</dt>
                <dd className="font-medium">{health.data.models.face}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Body pose</dt>
                <dd className="font-medium">{health.data.models.pose}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Phone-like objects</dt>
                <dd className="font-medium">{health.data.models.objects}</dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-muted">All are pretrained models used as published. Their accuracy in this room has to be measured; see the README.</p>
          </Card>
        </div>
      )}
    </>
  )
}
