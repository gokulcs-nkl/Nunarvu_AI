import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ShieldCheck, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { Alert, Badge, Button, Card, EmptyState, Input, PageHeader, Spinner } from '../components/ui'
import { api, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { Compliance, PrivacySettings } from '../lib/types'

const RETENTION = [
  { key: 'face_retention_days', label: 'Face data', note: 'Encrypted face features of enrolled students.' },
  { key: 'attendance_retention_days', label: 'Attendance records', note: 'The register of who attended each session.' },
  { key: 'event_retention_days', label: 'Observations', note: 'Hand raises, phone-like objects and so on.' },
] as const

function ComplianceCards({ data }: { data: Compliance }) {
  const coverage = data.active_students ? Math.round((100 * data.with_consent) / data.active_students) : 0
  const tiles = [
    { label: 'Active students', value: data.active_students },
    { label: 'Consent on record', value: `${data.with_consent} (${coverage}%)` },
    { label: 'Consent withdrawn', value: data.consent_withdrawn },
    { label: 'Minors', value: data.minors },
  ]
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {tiles.map((tile) => (
        <div key={tile.label} className="rounded-2xl border border-line bg-canvas px-4 py-3">
          <p className="text-xs text-muted">{tile.label}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{tile.value}</p>
        </div>
      ))}
    </div>
  )
}

function Warnings({ data }: { data: Compliance }) {
  const issues: string[] = []
  if (data.face_data_without_consent.length > 0)
    issues.push(
      `Face data is held for ${data.face_data_without_consent.length} student(s) without consent on record: ${data.face_data_without_consent.join(', ')}. Record consent or erase their face data.`,
    )
  if (data.minors_missing_guardian_contact.length > 0)
    issues.push(
      `${data.minors_missing_guardian_contact.length} minor(s) have consent but no guardian contact: ${data.minors_missing_guardian_contact.join(', ')}. The DPDP Act needs verifiable guardian consent for a minor.`,
    )
  if (issues.length === 0)
    return (
      <Alert tone="ok">
        <span className="inline-flex items-center gap-2">
          <ShieldCheck size={16} aria-hidden="true" /> Nothing needs attention right now.
        </span>
      </Alert>
    )
  return (
    <div className="space-y-2">
      {issues.map((issue) => (
        <Alert key={issue} tone="warn">
          {issue}
        </Alert>
      ))}
    </div>
  )
}

function RetentionForm({ settings, editable }: { settings: PrivacySettings; editable: boolean }) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<Partial<PrivacySettings>>({})
  const current = { ...settings, ...draft }
  const dirty = Object.keys(draft).length > 0

  const save = useMutation({
    mutationFn: () => api<PrivacySettings>('/settings/privacy/', { method: 'PUT', body: draft }),
    onSuccess: (saved) => {
      queryClient.setQueryData(['privacy-settings'], saved)
      setDraft({})
    },
  })
  const cleanup = useMutation({
    mutationFn: () => api<{ removed: Record<string, number> }>('/settings/privacy/', { method: 'POST', body: {} }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['compliance'] }),
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }

  return (
    <form onSubmit={submit}>
      <ul className="divide-y divide-line">
        {RETENTION.map(({ key, label, note }) => (
          <li key={key} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
            <span className="min-w-0">
              <span className="font-medium">{label}</span>
              <span className="block text-muted">{note}</span>
            </span>
            <label className="flex items-center gap-2 text-muted">
              Keep for
              <Input
                type="number"
                min={0}
                max={36500}
                className="w-28"
                aria-label={`Days to keep ${label}`}
                value={current[key]}
                disabled={!editable}
                onChange={(e) => setDraft({ ...draft, [key]: Number(e.target.value) })}
              />
              days
            </label>
          </li>
        ))}
        <li className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
          <span className="min-w-0">
            <span className="font-medium">Hide faces without consent</span>
            <span className="block text-muted">Blur people who are not enrolled with consent in the live view and snapshots.</span>
          </span>
          <input
            type="checkbox"
            checked={current.blur_unconsented}
            disabled={!editable}
            onChange={(e) => setDraft({ ...draft, blur_unconsented: e.target.checked })}
          />
        </li>
      </ul>
      <p className="mt-2 text-xs text-muted">0 days means the data is kept indefinitely.</p>
      {save.error && <Alert>{save.error instanceof ApiError ? save.error.message : 'Could not save.'}</Alert>}
      {editable ? (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={!dirty || save.isPending}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
          <Button variant="secondary" disabled={cleanup.isPending} onClick={() => cleanup.mutate()}>
            {cleanup.isPending ? 'Cleaning…' : 'Delete old data now'}
          </Button>
          {cleanup.data && (
            <span className="text-xs text-muted">
              Removed {cleanup.data.removed.face_enrollments} face enrolments, {cleanup.data.removed.attendance_records}{' '}
              attendance records, {cleanup.data.removed.observations} observations.
            </span>
          )}
        </div>
      ) : (
        <p className="mt-3 text-xs text-muted">Only administrators can change these settings.</p>
      )}
    </form>
  )
}

export function Privacy() {
  const { user } = useAuth()
  const editable = user?.role === 'admin'
  const compliance = useQuery({ queryKey: ['compliance'], queryFn: () => api<Compliance>('/compliance/') })
  const settings = useQuery({ queryKey: ['privacy-settings'], queryFn: () => api<PrivacySettings>('/settings/privacy/') })

  return (
    <>
      <PageHeader
        title="Privacy and compliance"
        description="Built around India's Digital Personal Data Protection Act, 2023. Consent is recorded and can be withdrawn, data is kept only as long as set here, and a student's data can be exported or erased from their page on the Students list."
      />
      <div className="space-y-6">
        <Card
          title="At a glance"
          action={
            <Badge tone="brand">
              <span className="inline-flex items-center gap-1">
                <ShieldCheck size={13} aria-hidden="true" /> DPDP
              </span>
            </Badge>
          }
        >
          {compliance.isLoading && <Spinner />}
          {compliance.isError && <Alert>Could not load the compliance summary.</Alert>}
          {compliance.data && (
            <div className="space-y-4">
              <ComplianceCards data={compliance.data} />
              <Warnings data={compliance.data} />
            </div>
          )}
        </Card>

        <Card
          title="How long data is kept"
          action={
            <TriangleAlert size={16} aria-hidden="true" className="text-muted" />
          }
        >
          {settings.isLoading && <Spinner />}
          {settings.isError && <Alert>Could not load the settings.</Alert>}
          {settings.data && <RetentionForm settings={settings.data} editable={editable} />}
        </Card>

        <Card title="A student's own data">
          <EmptyState
            title="Managed per student"
            hint="Open a student on the Students page to record or withdraw consent, download everything held about them, or erase them. Every such action is written to the audit log."
          />
        </Card>
      </div>
    </>
  )
}
