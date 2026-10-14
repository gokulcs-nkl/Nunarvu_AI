import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { Alert, Button, Card, EmptyState, PageHeader, Spinner } from '../components/ui'
import { api, apiList, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import { WEEKDAYS } from '../lib/types'
import type { ClassGroup, Period, Room, Subject, TeacherProfile, TimetableEntry } from '../lib/types'

const errorText = (error: unknown) => (error instanceof ApiError ? error.message : 'Something went wrong.')
const DAYS = [0, 1, 2, 3, 4, 5]

interface Slot {
  weekday: number
  period: number
  entry: TimetableEntry | null
}

function SlotForm({
  slot,
  classGroup,
  subjects,
  teachers,
  rooms,
  onDone,
}: {
  slot: Slot
  classGroup: number
  subjects: Subject[]
  teachers: TeacherProfile[]
  rooms: Room[]
  onDone: () => void
}) {
  const queryClient = useQueryClient()
  const [subject, setSubject] = useState(slot.entry ? String(slot.entry.subject) : '')
  const [teacher, setTeacher] = useState(slot.entry?.teacher ? String(slot.entry.teacher) : '')
  const [room, setRoom] = useState(slot.entry?.room ? String(slot.entry.room) : '')
  const done = () => {
    void queryClient.invalidateQueries({ queryKey: ['timetable'] })
    onDone()
  }

  const save = useMutation({
    mutationFn: () => {
      const body = {
        class_group: classGroup,
        subject: Number(subject),
        teacher: teacher ? Number(teacher) : null,
        room: room ? Number(room) : null,
        weekday: slot.weekday,
        period_number: slot.period,
      }
      return slot.entry
        ? api<TimetableEntry>(`/timetable/${slot.entry.id}/`, { method: 'PUT', body })
        : api<TimetableEntry>('/timetable/', { method: 'POST', body })
    },
    onSuccess: done,
  })
  const remove = useMutation({
    mutationFn: () => api<void>(`/timetable/${slot.entry!.id}/`, { method: 'DELETE' }),
    onSuccess: done,
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }
  const selectClass = 'h-9 w-full rounded-md border border-line bg-surface px-2 text-sm'
  const failure = save.error ?? remove.error

  return (
    <Card title={`${WEEKDAYS[slot.weekday]}, period ${slot.period}`}>
      <form onSubmit={handleSubmit} className="grid gap-3 sm:grid-cols-3">
        <div>
          <label htmlFor="slot-subject" className="mb-1 block text-xs text-muted">
            Subject
          </label>
          <select id="slot-subject" required className={selectClass} value={subject} onChange={(event) => setSubject(event.target.value)}>
            <option value="">Choose a subject</option>
            {subjects.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} · {item.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="slot-teacher" className="mb-1 block text-xs text-muted">
            Teacher (optional)
          </label>
          <select id="slot-teacher" className={selectClass} value={teacher} onChange={(event) => setTeacher(event.target.value)}>
            <option value="">No teacher</option>
            {teachers.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="slot-room" className="mb-1 block text-xs text-muted">
            Room (optional)
          </label>
          <select id="slot-room" className={selectClass} value={room} onChange={(event) => setRoom(event.target.value)}>
            <option value="">No room</option>
            {rooms.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>
        {failure && (
          <div className="sm:col-span-3">
            <Alert>{errorText(failure)}</Alert>
          </div>
        )}
        <div className="flex flex-wrap gap-2 sm:col-span-3">
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
          {slot.entry && (
            <Button variant="danger" disabled={remove.isPending} onClick={() => remove.mutate()}>
              Remove from timetable
            </Button>
          )}
          <Button variant="secondary" onClick={onDone}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  )
}

export function Timetable() {
  const { user } = useAuth()
  const editable = user?.role === 'admin'
  const queryClient = useQueryClient()
  const [classGroup, setClassGroup] = useState('')
  const [slot, setSlot] = useState<Slot | null>(null)

  const classes = useQuery({ queryKey: ['class-groups'], queryFn: () => apiList<ClassGroup>('/class-groups/') })
  const subjects = useQuery({ queryKey: ['subjects'], queryFn: () => apiList<Subject>('/subjects/') })
  const teachers = useQuery({ queryKey: ['teachers'], queryFn: () => apiList<TeacherProfile>('/teachers/') })
  const rooms = useQuery({ queryKey: ['rooms'], queryFn: () => apiList<Room>('/rooms/') })
  const periods = useQuery({ queryKey: ['periods'], queryFn: () => api<Period[]>('/periods/') })
  const chosen = classGroup || (classes.data?.[0] ? String(classes.data[0].id) : '')
  const entries = useQuery({
    queryKey: ['timetable', chosen],
    queryFn: () => apiList<TimetableEntry>(`/timetable/?class_group=${chosen}`),
    enabled: !!chosen,
  })

  const generate = useMutation({
    mutationFn: () => api<{ created: number }>('/sessions/generate/', { method: 'POST', body: {} }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sessions'] }),
  })

  // Rows are every period number that has timings on any day, plus any already on the timetable.
  const numbers = Array.from(
    new Set([...(periods.data ?? []).map((period) => period.number), ...(entries.data ?? []).map((entry) => entry.period_number)]),
  ).sort((a, b) => a - b)
  const find = (weekday: number, period: number) =>
    entries.data?.find((entry) => entry.weekday === weekday && entry.period_number === period) ?? null
  const subjectCode = (id: number) => subjects.data?.find((item) => item.id === id)?.code ?? '…'
  const teacherName = (id: number | null) => (id ? (teachers.data?.find((item) => item.id === id)?.name ?? '') : '')
  const roomName = (id: number | null) => (id ? (rooms.data?.find((item) => item.id === id)?.name ?? '') : '')

  return (
    <>
      <PageHeader
        title="Timetable"
        description="Which subject each class has in each period. While the camera worker is running, sessions are created, started and ended at the period times by themselves."
        action={
          editable ? (
            <Button variant="secondary" disabled={generate.isPending} onClick={() => generate.mutate()}>
              {generate.isPending ? 'Creating…' : "Create today's sessions now"}
            </Button>
          ) : undefined
        }
      />
      {generate.data && (
        <div className="mb-4">
          <Alert tone="ok">
            {generate.data.created === 0 ? "Today's sessions already exist, or nothing is timetabled today." : `${generate.data.created} session(s) created for today.`}
          </Alert>
        </div>
      )}
      {generate.error && (
        <div className="mb-4">
          <Alert>{errorText(generate.error)}</Alert>
        </div>
      )}

      {classes.data?.length === 0 ? (
        <Card>
          <EmptyState title="No classes yet" hint="Add a class on the Classes and rooms page first." />
        </Card>
      ) : (
        <>
          {slot && chosen && (
            <div className="mb-5">
              <SlotForm
                key={`${slot.weekday}-${slot.period}`}
                slot={slot}
                classGroup={Number(chosen)}
                subjects={subjects.data ?? []}
                teachers={teachers.data ?? []}
                rooms={rooms.data ?? []}
                onDone={() => setSlot(null)}
              />
            </div>
          )}
          <Card
            title="Weekly timetable"
            action={
              <select
                aria-label="Class"
                className="h-9 rounded-md border border-line bg-surface px-2 text-sm"
                value={chosen}
                onChange={(event) => {
                  setClassGroup(event.target.value)
                  setSlot(null)
                }}
              >
                {classes.data?.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name} ({group.academic_year})
                  </option>
                ))}
              </select>
            }
          >
            {(entries.isLoading || periods.isLoading) && <Spinner />}
            {entries.isError && <Alert>{errorText(entries.error)}</Alert>}
            {periods.data && numbers.length === 0 && (
              <EmptyState
                title="No period timings yet"
                hint="The timetable is built on periods. Set at least a default schedule first."
                action={
                  <Link to="/settings/periods" className="text-sm font-medium text-brand hover:underline">
                    Set period timings
                  </Link>
                }
              />
            )}
            {numbers.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[46rem] table-fixed border-separate border-spacing-1 text-sm">
                  <thead>
                    <tr className="text-xs text-muted">
                      <th className="w-16 pb-1 text-left font-medium">Period</th>
                      {DAYS.map((day) => (
                        <th key={day} className="pb-1 text-left font-medium">
                          {WEEKDAYS[day]}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {numbers.map((number) => (
                      <tr key={number}>
                        <th scope="row" className="text-left align-top font-medium tabular-nums">
                          {number}
                        </th>
                        {DAYS.map((day) => {
                          const entry = find(day, number)
                          const label = `${WEEKDAYS[day]} period ${number}`
                          if (!entry) {
                            return (
                              <td key={day} className="align-top">
                                {editable ? (
                                  <button
                                    type="button"
                                    aria-label={`Add a subject to ${label}`}
                                    className="flex h-14 w-full items-center justify-center rounded-md border border-dashed border-line text-muted hover:border-brand hover:text-brand"
                                    onClick={() => setSlot({ weekday: day, period: number, entry: null })}
                                  >
                                    <Plus size={16} aria-hidden="true" />
                                  </button>
                                ) : (
                                  <div className="h-14 rounded-md bg-canvas" />
                                )}
                              </td>
                            )
                          }
                          const body = (
                            <>
                              <span className="block font-medium text-ink">{subjectCode(entry.subject)}</span>
                              <span className="block truncate text-xs text-muted">
                                {[teacherName(entry.teacher), roomName(entry.room)].filter(Boolean).join(' · ') || 'No teacher or room'}
                              </span>
                            </>
                          )
                          return (
                            <td key={day} className="align-top">
                              {editable ? (
                                <button
                                  type="button"
                                  aria-label={`Edit ${label}`}
                                  className="h-14 w-full rounded-md bg-brand-soft px-2 text-left hover:ring-2 hover:ring-brand"
                                  onClick={() => setSlot({ weekday: day, period: number, entry })}
                                >
                                  {body}
                                </button>
                              ) : (
                                <div className="h-14 rounded-md bg-brand-soft px-2 py-1.5">{body}</div>
                              )}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </>
  )
}
