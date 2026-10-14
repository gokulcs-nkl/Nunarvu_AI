import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { EventList } from '../components/EventList'
import { Alert, Button, Card, EmptyState, Input, PageHeader, Spinner } from '../components/ui'
import { api, ApiError } from '../lib/api'
import type { Page } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { ClassroomEvent, ObservationSettings } from '../lib/types'

const KINDS = [
  { key: 'hand_raise', label: 'Hand raised', note: 'A wrist held above shoulder height.' },
  { key: 'head_down', label: 'Head-down posture', note: 'Head at or below shoulder level. Reported as a possible sleeping-like posture for the teacher to verify.' },
  { key: 'phone', label: 'Phone-like object', note: 'A phone-like object near a person. Small or hidden phones are often missed.' },
  { key: 'unusual_activity', label: 'Unusual activity', note: 'Two or more people moving fast close together. Cannot tell play from a disturbance.' },
] as const

function SettingsCard() {
  const { user } = useAuth()
  const editable = user?.role === 'admin'
  const queryClient = useQueryClient()
  const settings = useQuery({ queryKey: ['observation-settings'], queryFn: () => api<ObservationSettings>('/settings/observations/') })
  const [draft, setDraft] = useState<Partial<ObservationSettings>>({})
  const current = { ...settings.data, ...draft } as ObservationSettings
  const dirty = Object.keys(draft).length > 0

  const save = useMutation({
    mutationFn: () => api<ObservationSettings>('/settings/observations/', { method: 'PUT', body: draft }),
    onSuccess: (saved) => {
      queryClient.setQueryData(['observation-settings'], saved)
      setDraft({})
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }

  return (
    <Card title="What the camera reports">
      {settings.isLoading && <Spinner />}
      {settings.isError && <Alert>Could not load the settings.</Alert>}
      {settings.data && (
        <form onSubmit={handleSubmit}>
          <ul className="divide-y divide-line">
            {KINDS.map(({ key, label, note }) => {
              const enabledKey = `${key}_enabled` as const
              const secondsKey = `${key}_seconds` as const
              return (
                <li key={key} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
                  <label className="flex min-w-0 flex-1 items-start gap-2">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={current[enabledKey]}
                      disabled={!editable}
                      onChange={(event) => setDraft({ ...draft, [enabledKey]: event.target.checked })}
                    />
                    <span>
                      <span className="font-medium">{label}</span>
                      <span className="block text-muted">{note}</span>
                    </span>
                  </label>
                  <label className="flex items-center gap-2 text-muted">
                    Report after
                    <Input
                      type="number"
                      min={0.5}
                      max={3600}
                      step={0.5}
                      className="w-24"
                      aria-label={`Seconds before ${label} is reported`}
                      value={current[secondsKey]}
                      disabled={!editable || !current[enabledKey]}
                      onChange={(event) => setDraft({ ...draft, [secondsKey]: Number(event.target.value) })}
                    />
                    seconds
                  </label>
                </li>
              )
            })}
          </ul>
          {save.error && <Alert>{save.error instanceof ApiError ? save.error.message : 'Could not save.'}</Alert>}
          {editable ? (
            <div className="mt-3 flex items-center gap-3">
              <Button type="submit" disabled={!dirty || save.isPending}>
                {save.isPending ? 'Saving…' : 'Save'}
              </Button>
              <span className="text-xs text-muted">A running worker picks up changes within about 30 seconds.</span>
            </div>
          ) : (
            <p className="mt-3 text-xs text-muted">Only administrators can change these settings.</p>
          )}
        </form>
      )}
    </Card>
  )
}

export function Observations() {
  const [kind, setKind] = useState('')
  const [status, setStatus] = useState('unreviewed')
  const [page, setPage] = useState(1)
  const params = new URLSearchParams({ page: String(page) })
  if (kind) params.set('kind', kind)
  if (status) params.set('review_status', status)

  const events = useQuery({
    queryKey: ['events', 'all', params.toString()],
    queryFn: () => api<Page<ClassroomEvent>>(`/events/?${params.toString()}`),
    placeholderData: (previous) => previous,
  })
  const pages = events.data ? Math.max(1, Math.ceil(events.data.count / 20)) : 1
  const selectClass = 'h-9 rounded-lg border border-line bg-canvas px-2 text-sm'

  return (
    <>
      <PageHeader
        title="Observations"
        description="What the camera noticed during sessions. Each item describes something visible and how it was measured; none of them is a conclusion about a student. A teacher confirms or dismisses each one."
      />
      <div className="space-y-5">
        <Card
          title="Recorded observations"
          action={
            <div className="flex flex-wrap gap-2">
              <select
                aria-label="Type"
                className={selectClass}
                value={kind}
                onChange={(event) => {
                  setKind(event.target.value)
                  setPage(1)
                }}
              >
                <option value="">All types</option>
                {KINDS.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.label}
                  </option>
                ))}
              </select>
              <select
                aria-label="Review status"
                className={selectClass}
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value)
                  setPage(1)
                }}
              >
                <option value="unreviewed">Not reviewed</option>
                <option value="confirmed">Confirmed</option>
                <option value="dismissed">Dismissed</option>
                <option value="">Any status</option>
              </select>
            </div>
          }
        >
          {events.isLoading && <Spinner />}
          {events.isError && <Alert>Could not load observations.</Alert>}
          {events.data?.results.length === 0 && (
            <EmptyState title="Nothing here" hint="Observations appear while the camera worker is running during an active session." />
          )}
          {events.data && events.data.results.length > 0 && <EventList events={events.data.results} canReview showDate />}
          {events.data && pages > 1 && (
            <div className="mt-3 flex items-center justify-between text-sm text-muted">
              <span>
                Page {page} of {pages} · {events.data.count} observations
              </span>
              <div className="flex gap-2">
                <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                  Previous
                </Button>
                <Button variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
        <SettingsCard />
      </div>
    </>
  )
}
