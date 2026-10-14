import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Mail, Send } from 'lucide-react'
import { useState } from 'react'

import { api, apiList, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { ClassGroup, GuardianNotices, RiskResult } from '../lib/types'
import { Alert, Badge, Button, Card, EmptyState, Spinner } from './ui'

const BAND = {
  high: { label: 'Needs attention', tone: 'danger' as const },
  medium: { label: 'Worth watching', tone: 'warn' as const },
  low: { label: 'Minor signs', tone: 'neutral' as const },
}

/** A bar showing the score out of 100. The number is beside it, so colour is never the only cue. */
function ScoreBar({ score, band }: { score: number; band: keyof typeof BAND }) {
  const colour = { high: 'var(--color-danger)', medium: 'var(--color-warn)', low: 'var(--color-muted)' }[band]
  return (
    <span className="flex items-center gap-2">
      <span className="h-1.5 w-20 overflow-hidden rounded-full bg-line" aria-hidden="true">
        <span className="block h-full rounded-full" style={{ width: `${score}%`, background: colour }} />
      </span>
      <span className="tabular-nums font-semibold">{score}</span>
    </span>
  )
}

export function RiskSection() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [classGroup, setClassGroup] = useState('')
  const [band, setBand] = useState('')
  const queryClient = useQueryClient()
  const classes = useQuery({ queryKey: ['class-groups'], queryFn: () => apiList<ClassGroup>('/class-groups/') })

  const params = new URLSearchParams()
  if (classGroup) params.set('class_group', classGroup)
  if (band) params.set('band', band)
  const risk = useQuery({ queryKey: ['risk', params.toString()], queryFn: () => api<RiskResult>(`/reports/risk/?${params.toString()}`) })
  const notices = useQuery({ queryKey: ['guardian-notices'], queryFn: () => api<GuardianNotices>('/notices/guardian/') })

  const send = useMutation({
    mutationFn: () => api<{ sent: number; failed: number; disabled: boolean }>('/notices/guardian/', { method: 'POST', body: {} }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['guardian-notices'] }),
  })

  const selectClass = 'h-9 rounded-lg border border-line bg-canvas px-2 text-sm'
  const data = risk.data

  return (
    <>
      <Card
        title="Early warning"
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
            <select aria-label="Level" className={selectClass} value={band} onChange={(e) => setBand(e.target.value)}>
              <option value="">All levels</option>
              <option value="high">Needs attention</option>
              <option value="medium">Worth watching</option>
              <option value="low">Minor signs</option>
            </select>
          </div>
        }
      >
        <p className="mb-3 text-xs text-muted">
          Students whose attendance pattern suggests they may be disengaging. Each score is the sum of named signals,
          shown below, so you can see exactly why a student appears here. It is a prompt for a conversation, not a
          judgement or a prediction.
        </p>
        {risk.isLoading && <Spinner />}
        {risk.isError && <Alert>Could not load the early warning list.</Alert>}
        {data && !data.term && <EmptyState title="No term set" hint={data.detail} />}
        {data && data.term && data.rows.length === 0 && (
          <EmptyState title="Nothing to flag" hint="No student in this group shows a warning sign." />
        )}
        {data && data.term && data.rows.length > 0 && (
          <>
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3">
                <p className="text-xs text-danger">Needs attention</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-danger">{data.counts?.high ?? 0}</p>
              </div>
              <div className="rounded-xl border border-warn/30 bg-warn-soft px-4 py-3">
                <p className="text-xs text-warn">Worth watching</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-warn">{data.counts?.medium ?? 0}</p>
              </div>
              <div className="rounded-xl border border-line bg-canvas px-4 py-3">
                <p className="text-xs text-muted">Flagged in total</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">{data.counts?.total ?? 0}</p>
              </div>
            </div>
            <ul className="divide-y divide-line">
              {data.rows.map((row) => (
                <li key={row.student} className="py-3 text-sm">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2 font-medium">
                        {row.full_name}
                        <span className="font-normal text-muted">{row.roll_number}</span>
                        <Badge tone={BAND[row.band].tone}>{BAND[row.band].label}</Badge>
                      </p>
                      <p className="mt-0.5 text-xs tabular-nums text-muted">
                        {row.attended} of {row.held} attended
                        {row.percent === null ? '' : ` · ${row.percent}%`}
                        {row.consecutive_absences > 0 ? ` · ${row.consecutive_absences} in a row missed` : ''}
                        {row.guardian_contact ? ' · guardian on record' : ' · no guardian contact'}
                      </p>
                      <ul className="mt-1 space-y-0.5 text-xs text-muted">
                        {row.signals.map((signal) => (
                          <li key={signal.name}>
                            {signal.detail} <span className="tabular-nums">(+{signal.points})</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <ScoreBar score={row.score} band={row.band} />
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>

      <Card
        title="Guardian notices"
        action={
          <Mail size={16} aria-hidden="true" className="text-muted" />
        }
      >
        {notices.isLoading && <Spinner />}
        {notices.data && !notices.data.enabled && (
          <Alert tone="warn">
            Guardian notices are switched off. An administrator can turn them on from the Privacy page, after checking
            that guardian contacts are correct.
          </Alert>
        )}
        {notices.data && notices.data.enabled && (
          <>
            <p className="mb-3 text-xs text-muted">
              An email goes to the guardian of a student who needs attention and has a guardian email on record. The
              same warning is not repeated within two weeks.
            </p>
            {notices.data.pending.length === 0 ? (
              <EmptyState title="Nobody to notify" hint="No guardian needs to hear from us right now." />
            ) : (
              <ul className="mb-3 divide-y divide-line text-sm">
                {notices.data.pending.map((item) => (
                  <li key={item.student} className="flex items-center justify-between gap-3 py-2">
                    <span>
                      <span className="font-medium">{item.full_name}</span>{' '}
                      <span className="text-muted">{item.roll_number}</span>
                      <span className="block text-xs text-muted">{item.to}</span>
                    </span>
                    <span className="tabular-nums text-muted">{item.percent === null ? '–' : `${item.percent}%`}</span>
                  </li>
                ))}
              </ul>
            )}
            {send.error && <Alert>{send.error instanceof ApiError ? send.error.message : 'Could not send.'}</Alert>}
            {send.data && <Alert tone="ok">{`Sent ${send.data.sent}, failed ${send.data.failed}.`}</Alert>}
            {isAdmin && notices.data.pending.length > 0 && (
              <Button
                className="mt-3"
                disabled={send.isPending}
                onClick={() => {
                  if (window.confirm(`Email ${notices.data?.pending.length} guardian(s) now?`)) send.mutate()
                }}
              >
                <Send size={16} aria-hidden="true" />
                {send.isPending ? 'Sending…' : 'Send notices'}
              </Button>
            )}
            {notices.data.sent.length > 0 && (
              <details className="mt-4 text-sm">
                <summary className="cursor-pointer select-none text-muted">Already sent ({notices.data.sent.length})</summary>
                <ul className="mt-2 divide-y divide-line">
                  {notices.data.sent.map((item) => (
                    <li key={item.id} className="flex items-center justify-between gap-3 py-2 text-xs">
                      <span>
                        {item.roll_number} · {item.to}
                      </span>
                      <span className="text-muted">{new Date(item.sent_at).toLocaleDateString(undefined, { dateStyle: 'medium' })}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </>
        )}
      </Card>
    </>
  )
}
