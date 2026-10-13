import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { Alert, Button, Card, EmptyState, Input, PageHeader, Spinner } from '../components/ui'
import { api, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import { WEEKDAYS } from '../lib/types'
import type { Period } from '../lib/types'

/** Which set of timings is being edited: the default, one weekday, or one calendar date. */
type Scope = { kind: 'default' } | { kind: 'weekday'; weekday: number } | { kind: 'date'; date: string }

const shortTime = (value: string) => value.slice(0, 5)

function inScope(period: Period, scope: Scope): boolean {
  if (scope.kind === 'default') return period.weekday === null && period.specific_date === null
  if (scope.kind === 'weekday') return period.weekday === scope.weekday
  return period.specific_date === scope.date
}

function scopeFields(scope: Scope): Pick<Period, 'weekday' | 'specific_date'> {
  return {
    weekday: scope.kind === 'weekday' ? scope.weekday : null,
    specific_date: scope.kind === 'date' ? scope.date : null,
  }
}

function errorText(error: unknown): string {
  return error instanceof ApiError ? error.message : 'Something went wrong.'
}

function PeriodRow({ period, editable }: { period: Period; editable: boolean }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(period.name)
  const [start, setStart] = useState(shortTime(period.start_time))
  const [end, setEnd] = useState(shortTime(period.end_time))
  const dirty = name !== period.name || start !== shortTime(period.start_time) || end !== shortTime(period.end_time)

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['periods'] })
  const save = useMutation({
    mutationFn: () =>
      api<Period>(`/periods/${period.id}/`, { method: 'PATCH', body: { name, start_time: start, end_time: end } }),
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: () => api<void>(`/periods/${period.id}/`, { method: 'DELETE' }),
    onSuccess: refresh,
  })
  const failure = save.error ?? remove.error

  return (
    <>
      <tr className="border-t border-line">
        <td className="py-2 pr-3 text-sm font-medium tabular-nums">{period.number}</td>
        <td className="py-2 pr-3">
          <Input
            aria-label={`Name of period ${period.number}`}
            value={name}
            placeholder={`Period ${period.number}`}
            disabled={!editable}
            onChange={(event) => setName(event.target.value)}
          />
        </td>
        <td className="py-2 pr-3">
          <Input
            type="time"
            aria-label={`Start of period ${period.number}`}
            value={start}
            disabled={!editable}
            onChange={(event) => setStart(event.target.value)}
          />
        </td>
        <td className="py-2 pr-3">
          <Input
            type="time"
            aria-label={`End of period ${period.number}`}
            value={end}
            disabled={!editable}
            onChange={(event) => setEnd(event.target.value)}
          />
        </td>
        {editable && (
          <td className="py-2">
            <div className="flex justify-end gap-2">
              <Button variant="secondary" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
                {save.isPending ? 'Saving…' : 'Save'}
              </Button>
              <Button
                variant="danger"
                aria-label={`Delete period ${period.number}`}
                disabled={remove.isPending}
                onClick={() => remove.mutate()}
              >
                <Trash2 size={16} aria-hidden="true" />
              </Button>
            </div>
          </td>
        )}
      </tr>
      {failure && (
        <tr>
          <td colSpan={5} className="pb-2">
            <Alert>{errorText(failure)}</Alert>
          </td>
        </tr>
      )}
    </>
  )
}

function AddPeriodForm({ scope, nextNumber }: { scope: Scope; nextNumber: number }) {
  const queryClient = useQueryClient()
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')

  const create = useMutation({
    mutationFn: () =>
      api<Period>('/periods/', {
        method: 'POST',
        body: { number: nextNumber, start_time: start, end_time: end, ...scopeFields(scope) },
      }),
    onSuccess: () => {
      setStart('')
      setEnd('')
      return queryClient.invalidateQueries({ queryKey: ['periods'] })
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    create.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 border-t border-line pt-4">
      <p className="mb-2 text-sm font-medium">Add period {nextNumber}</p>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="new-start" className="mb-1 block text-xs text-muted">
            Start
          </label>
          <Input id="new-start" type="time" required value={start} onChange={(event) => setStart(event.target.value)} />
        </div>
        <div>
          <label htmlFor="new-end" className="mb-1 block text-xs text-muted">
            End
          </label>
          <Input id="new-end" type="time" required value={end} onChange={(event) => setEnd(event.target.value)} />
        </div>
        <Button type="submit" disabled={create.isPending}>
          <Plus size={16} aria-hidden="true" />
          {create.isPending ? 'Adding…' : 'Add period'}
        </Button>
      </div>
      {create.error && (
        <div className="mt-3">
          <Alert>{errorText(create.error)}</Alert>
        </div>
      )}
    </form>
  )
}

export function PeriodSettings() {
  const { user } = useAuth()
  const editable = user?.role === 'admin'
  const queryClient = useQueryClient()
  const [scope, setScope] = useState<Scope>({ kind: 'default' })
  const [copyFrom, setCopyFrom] = useState('default')

  const periods = useQuery({ queryKey: ['periods'], queryFn: () => api<Period[]>('/periods/') })
  const all = periods.data ?? []
  const current = all.filter((period) => inScope(period, scope)).sort((a, b) => a.number - b.number)
  const defaults = all.filter((period) => inScope(period, { kind: 'default' }))
  const overriddenDays = new Set(all.filter((period) => period.weekday !== null).map((period) => period.weekday))
  const nextNumber = current.reduce((highest, period) => Math.max(highest, period.number), 0) + 1

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['periods'] })
  const copyDay = useMutation({
    mutationFn: (weekday: number) =>
      api<Period[]>('/periods/copy-day/', {
        method: 'POST',
        body: { to_weekday: weekday, ...(copyFrom === 'default' ? {} : { from_weekday: Number(copyFrom) }) },
      }),
    onSuccess: refresh,
  })
  const clearScope = useMutation({
    mutationFn: () => Promise.all(current.map((period) => api<void>(`/periods/${period.id}/`, { method: 'DELETE' }))),
    onSettled: refresh,
  })

  const usesDefault = scope.kind !== 'default' && current.length === 0
  const scopeLabel =
    scope.kind === 'default' ? 'Default timings' : scope.kind === 'weekday' ? WEEKDAYS[scope.weekday] : scope.date

  const tab = (active: boolean) =>
    `whitespace-nowrap rounded-md px-3 py-1.5 text-sm ${
      active ? 'bg-brand-soft font-medium text-brand-strong' : 'text-muted hover:bg-canvas hover:text-ink'
    }`

  return (
    <>
      <PageHeader
        title="Period timings"
        description="Timings are optional. Set one default schedule, and override it for any weekday or a single date only where the day differs. Days without their own timings use the default."
      />

      {!editable && (
        <div className="mb-4">
          <Alert tone="warn">Only administrators can change period timings. You can view them here.</Alert>
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-1" role="tablist" aria-label="Schedule to edit">
        <button
          type="button"
          role="tab"
          aria-selected={scope.kind === 'default'}
          className={tab(scope.kind === 'default')}
          onClick={() => setScope({ kind: 'default' })}
        >
          Default
        </button>
        {WEEKDAYS.map((day, index) => (
          <button
            key={day}
            type="button"
            role="tab"
            aria-selected={scope.kind === 'weekday' && scope.weekday === index}
            className={tab(scope.kind === 'weekday' && scope.weekday === index)}
            onClick={() => setScope({ kind: 'weekday', weekday: index })}
          >
            {day.slice(0, 3)}
            {overriddenDays.has(index) && <span className="ml-1 text-brand" aria-label="has its own timings">•</span>}
          </button>
        ))}
        <label className="ml-auto flex items-center gap-2 whitespace-nowrap text-sm text-muted">
          One date
          <Input
            type="date"
            className="w-40"
            value={scope.kind === 'date' ? scope.date : ''}
            onChange={(event) =>
              setScope(event.target.value ? { kind: 'date', date: event.target.value } : { kind: 'default' })
            }
          />
        </label>
      </div>

      <Card
        title={scopeLabel}
        action={
          editable && scope.kind !== 'default' && current.length > 0 ? (
            <Button variant="secondary" disabled={clearScope.isPending} onClick={() => clearScope.mutate()}>
              Use default timings
            </Button>
          ) : undefined
        }
      >
        {periods.isLoading && <Spinner />}
        {periods.isError && <Alert>{errorText(periods.error)}</Alert>}

        {periods.data && usesDefault && (
          <EmptyState
            title={`${scopeLabel} uses the default timings`}
            hint={
              defaults.length === 0
                ? 'No default timings are set either, so sessions on this day are started manually.'
                : 'Add a period below to give this day its own timings.'
            }
            action={
              editable && scope.kind === 'weekday' ? (
                <div className="flex flex-wrap items-center justify-center gap-2">
                  <label htmlFor="copy-from" className="text-sm text-muted">
                    Copy from
                  </label>
                  <select
                    id="copy-from"
                    className="h-9 rounded-md border border-line bg-surface px-2 text-sm"
                    value={copyFrom}
                    onChange={(event) => setCopyFrom(event.target.value)}
                  >
                    <option value="default">Default</option>
                    {WEEKDAYS.map((day, index) =>
                      overriddenDays.has(index) && index !== scope.weekday ? (
                        <option key={day} value={index}>
                          {day}
                        </option>
                      ) : null,
                    )}
                  </select>
                  <Button
                    variant="secondary"
                    disabled={copyDay.isPending}
                    onClick={() => copyDay.mutate(scope.weekday)}
                  >
                    Copy timings
                  </Button>
                </div>
              ) : undefined
            }
          />
        )}
        {copyDay.error && <Alert>{errorText(copyDay.error)}</Alert>}

        {periods.data && scope.kind === 'default' && current.length === 0 && (
          <EmptyState
            title="No default timings yet"
            hint="Without timings the system still works: teachers start and end each session manually."
          />
        )}

        {current.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] text-left">
              <thead>
                <tr className="text-xs text-muted">
                  <th className="pb-2 pr-3 font-medium">No.</th>
                  <th className="pb-2 pr-3 font-medium">Name (optional)</th>
                  <th className="pb-2 pr-3 font-medium">Start</th>
                  <th className="pb-2 pr-3 font-medium">End</th>
                  {editable && <th className="pb-2 text-right font-medium">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {current.map((period) => (
                  <PeriodRow key={`${period.id}-${period.start_time}-${period.end_time}-${period.name}`} period={period} editable={editable} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {editable && periods.data && <AddPeriodForm key={JSON.stringify(scope)} scope={scope} nextNumber={nextNumber} />}
      </Card>
    </>
  )
}
