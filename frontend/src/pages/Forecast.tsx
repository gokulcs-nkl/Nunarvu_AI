import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CircleCheck, TriangleAlert } from 'lucide-react'
import { useState } from 'react'

import { Heatmap } from '../components/Heatmap'
import { RiskSection } from '../components/RiskSection'
import { Alert, Badge, Card, EmptyState, IconTile, PageHeader, Spinner } from '../components/ui'
import { api, apiList } from '../lib/api'
import type { ClassGroup, ForecastResult, Heatmap as HeatmapData } from '../lib/types'

const STATUS: Record<string, { label: string; tone: 'ok' | 'warn' | 'danger' | 'neutral' }> = {
  safe: { label: 'On track', tone: 'ok' },
  at_risk: { label: 'At risk', tone: 'warn' },
  cannot_reach: { label: 'Cannot reach', tone: 'danger' },
  no_classes: { label: 'No classes', tone: 'neutral' },
}

const HEATMAP_KINDS = [
  { key: 'hand_raise', label: 'Hand raised' },
  { key: 'phone', label: 'Phone-like object' },
  { key: 'head_down', label: 'Head-down posture' },
]

function ForecastSection() {
  const [classGroup, setClassGroup] = useState('')
  const [status, setStatus] = useState('at_risk')
  const classes = useQuery({ queryKey: ['class-groups'], queryFn: () => apiList<ClassGroup>('/class-groups/') })

  const params = new URLSearchParams()
  if (classGroup) params.set('class_group', classGroup)
  if (status) params.set('status', status)
  const forecast = useQuery({
    queryKey: ['forecast', params.toString()],
    queryFn: () => api<ForecastResult>(`/reports/forecast/?${params.toString()}`),
  })

  const selectClass = 'h-9 rounded-lg border border-line bg-canvas px-2 text-sm'
  const data = forecast.data

  return (
    <Card
      title="Attendance forecast"
      action={
        <div className="flex flex-wrap gap-2">
          <select aria-label="Class" className={selectClass} value={classGroup} onChange={(e) => setClassGroup(e.target.value)}>
            <option value="">All classes</option>
            {classes.data?.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>
          <select aria-label="Status" className={selectClass} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="at_risk">At risk</option>
            <option value="cannot_reach">Cannot reach</option>
            <option value="safe">On track</option>
            <option value="">Everyone</option>
          </select>
        </div>
      }
    >
      {forecast.isLoading && <Spinner />}
      {forecast.isError && <Alert>Could not load the forecast.</Alert>}
      {data && !data.term && (
        <EmptyState
          title="No term set"
          hint={data.detail ?? 'Create a term on the Classes and rooms page to see the forecast.'}
        />
      )}
      {data && data.term && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-line bg-canvas px-4 py-3">
              <p className="text-xs text-muted">Term</p>
              <p className="mt-1 font-semibold">{data.term.name}</p>
              <p className="text-xs text-muted">Minimum {data.term.minimum_attendance}%</p>
            </div>
            <div className="rounded-xl border border-warn/30 bg-warn-soft px-4 py-3">
              <p className="text-xs text-warn">At risk</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-warn">{data.counts?.at_risk ?? 0}</p>
            </div>
            <div className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3">
              <p className="text-xs text-danger">Cannot reach</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-danger">{data.counts?.cannot_reach ?? 0}</p>
            </div>
          </div>

          {data.rows && data.rows.length === 0 ? (
            <EmptyState title="Nobody in this group" hint="No student matches the chosen status." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[46rem] text-left text-sm">
                <thead>
                  <tr className="text-xs text-muted">
                    <th className="pb-2 pr-3 font-medium">Roll no.</th>
                    <th className="pb-2 pr-3 font-medium">Name</th>
                    <th className="pb-2 pr-3 font-medium">Subject</th>
                    <th className="pb-2 pr-3 text-right font-medium">So far</th>
                    <th className="pb-2 pr-3 text-right font-medium">Now</th>
                    <th className="pb-2 pr-3 text-right font-medium">Left</th>
                    <th className="pb-2 pr-3 text-right font-medium">Must attend</th>
                    <th className="pb-2 pr-3 text-right font-medium">Can miss</th>
                    <th className="pb-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  {data.rows?.map((row) => (
                    <tr key={`${row.student}-${row.subject}`} className="border-t border-line">
                      <td className="py-2 pr-3">{row.roll_number}</td>
                      <td className="py-2 pr-3 font-medium">{row.full_name}</td>
                      <td className="py-2 pr-3">{row.subject_code}</td>
                      <td className="py-2 pr-3 text-right text-muted">
                        {row.attended}/{row.held}
                      </td>
                      <td className="py-2 pr-3 text-right">{row.percent === null ? '–' : `${row.percent}%`}</td>
                      <td className="py-2 pr-3 text-right">{row.remaining}</td>
                      <td className="py-2 pr-3 text-right font-semibold">
                        {row.status === 'cannot_reach' ? '—' : row.must_attend}
                      </td>
                      <td className="py-2 pr-3 text-right">{row.status === 'cannot_reach' ? '0' : row.can_miss}</td>
                      <td className="py-2">
                        <Badge tone={STATUS[row.status].tone}>{STATUS[row.status].label}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="mt-3 text-xs text-muted">
            "Must attend" is how many of the remaining classes this student has to attend to finish the term at or above
            the minimum. Pending records are left out until a teacher decides them.
          </p>
        </>
      )}
    </Card>
  )
}

function ParticipationSection() {
  const [kind, setKind] = useState('hand_raise')
  const [classGroup, setClassGroup] = useState('')
  const classes = useQuery({ queryKey: ['class-groups'], queryFn: () => apiList<ClassGroup>('/class-groups/') })

  const params = new URLSearchParams({ kind })
  if (classGroup) params.set('class_group', classGroup)
  const heatmap = useQuery({
    queryKey: ['participation', params.toString()],
    queryFn: () => api<HeatmapData>(`/reports/participation/?${params.toString()}`),
  })
  const selectClass = 'h-9 rounded-lg border border-line bg-canvas px-2 text-sm'

  return (
    <Card
      title="Participation map"
      action={
        <div className="flex flex-wrap gap-2">
          <select aria-label="Observation type" className={selectClass} value={kind} onChange={(e) => setKind(e.target.value)}>
            {HEATMAP_KINDS.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
          <select aria-label="Class" className={selectClass} value={classGroup} onChange={(e) => setClassGroup(e.target.value)}>
            <option value="">All classes</option>
            {classes.data?.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>
        </div>
      }
    >
      <p className="mb-3 text-xs text-muted">
        Where in the room this observation happened, across all matching sessions. It describes the room, not any one
        student, so it can show, for example, that the back rows rarely take part.
      </p>
      {heatmap.isLoading && <Spinner />}
      {heatmap.isError && <Alert>Could not load the map.</Alert>}
      {heatmap.data && heatmap.data.total === 0 && (
        <EmptyState title="Nothing recorded yet" hint="This map fills in as the camera worker records observations with a position." />
      )}
      {heatmap.data && heatmap.data.total > 0 && (
        <div className="mx-auto max-w-md">
          <Heatmap cells={heatmap.data.cells} peak={heatmap.data.peak} />
          <p className="mt-2 text-center text-sm text-muted">{heatmap.data.total} in total</p>
        </div>
      )}
    </Card>
  )
}

export function Forecast() {
  return (
    <>
      <PageHeader
        title="Insights"
        description="Looks ahead from the timetable and the attendance so far, and shows where in the room students take part. Both are built only from recorded data."
      />
      <div className="mb-4 flex flex-wrap gap-3">
        <span className="inline-flex items-center gap-2 text-sm text-muted">
          <IconTile tone="warn">
            <TriangleAlert size={16} />
          </IconTile>
          Catch up before it's too late
        </span>
        <span className="inline-flex items-center gap-2 text-sm text-muted">
          <IconTile tone="danger">
            <AlertTriangle size={16} />
          </IconTile>
          Cannot reach the minimum
        </span>
        <span className="inline-flex items-center gap-2 text-sm text-muted">
          <IconTile tone="ok">
            <CircleCheck size={16} />
          </IconTile>
          On track
        </span>
      </div>
      <div className="space-y-6">
        <RiskSection />
        <ForecastSection />
        <ParticipationSection />
      </div>
    </>
  )
}
