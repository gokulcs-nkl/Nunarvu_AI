import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Camera, Pencil, Plus, X } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { Alert, Badge, Button, Card, EmptyState, Input, PageHeader, Spinner } from '../components/ui'
import { api, apiList, ApiError } from '../lib/api'
import type { Page } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCamera } from '../lib/camera'
import type { ClassGroup, Student } from '../lib/types'

const TARGET_CAPTURES = 5
const errorText = (error: unknown) => (error instanceof ApiError ? error.message : 'Something went wrong.')

type Draft = Pick<Student, 'roll_number' | 'full_name' | 'email' | 'phone_number' | 'consent_given' | 'class_groups'>
const EMPTY: Draft = { roll_number: '', full_name: '', email: '', phone_number: '', consent_given: false, class_groups: [] }

function StudentForm({ student, classes, onDone }: { student: Student | null; classes: ClassGroup[]; onDone: () => void }) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<Draft>(student ?? EMPTY)
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft({ ...draft, [key]: value })

  const save = useMutation({
    mutationFn: () =>
      student
        ? api<Student>(`/students/${student.id}/`, { method: 'PATCH', body: draft })
        : api<Student>('/students/', { method: 'POST', body: draft }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['students'] })
      onDone()
    },
  })
  const withdrawing = !!student?.consent_given && !draft.consent_given && student.face_enrollment_count > 0

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }

  return (
    <Card
      title={student ? `Edit ${student.full_name}` : 'Add student'}
      action={
        <Button variant="ghost" aria-label="Close form" onClick={onDone}>
          <X size={16} aria-hidden="true" />
        </Button>
      }
    >
      <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="roll" className="mb-1 block text-sm font-medium">
            Roll number
          </label>
          <Input id="roll" required value={draft.roll_number} onChange={(event) => set('roll_number', event.target.value)} />
        </div>
        <div>
          <label htmlFor="name" className="mb-1 block text-sm font-medium">
            Full name
          </label>
          <Input id="name" required value={draft.full_name} onChange={(event) => set('full_name', event.target.value)} />
        </div>
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium">
            Email (optional)
          </label>
          <Input id="email" type="email" value={draft.email} onChange={(event) => set('email', event.target.value)} />
        </div>
        <div>
          <label htmlFor="phone" className="mb-1 block text-sm font-medium">
            Phone (optional)
          </label>
          <Input id="phone" value={draft.phone_number} onChange={(event) => set('phone_number', event.target.value)} />
        </div>
        <fieldset className="sm:col-span-2">
          <legend className="mb-1 text-sm font-medium">Classes</legend>
          {classes.length === 0 && <p className="text-sm text-muted">No classes yet. Add one under Classes and subjects.</p>}
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {classes.map((group) => (
              <label key={group.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={draft.class_groups.includes(group.id)}
                  onChange={(event) =>
                    set(
                      'class_groups',
                      event.target.checked
                        ? [...draft.class_groups, group.id]
                        : draft.class_groups.filter((id) => id !== group.id),
                    )
                  }
                />
                {group.name} ({group.academic_year})
              </label>
            ))}
          </div>
        </fieldset>
        <div className="sm:col-span-2">
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={draft.consent_given}
              onChange={(event) => set('consent_given', event.target.checked)}
            />
            <span>
              <span className="font-medium">Consent recorded for face recognition</span>
              <span className="block text-muted">
                Tick only when the student (or guardian, for a minor) has given informed consent. Face enrolment is
                blocked without it.
              </span>
            </span>
          </label>
          {withdrawing && (
            <div className="mt-2">
              <Alert tone="warn">Saving will permanently delete this student's stored face data.</Alert>
            </div>
          )}
        </div>
        {save.error && (
          <div className="sm:col-span-2">
            <Alert>{errorText(save.error)}</Alert>
          </div>
        )}
        <div className="flex gap-2 sm:col-span-2">
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
          <Button variant="secondary" onClick={onDone}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  )
}

function EnrollPanel({ student, onDone }: { student: Student; onDone: () => void }) {
  const queryClient = useQueryClient()
  const camera = useCamera()
  const [count, setCount] = useState(student.face_enrollment_count)
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['students'] })

  const enroll = useMutation({
    mutationFn: async () => {
      const frame = await camera.capture()
      if (!frame) throw new ApiError(0, 'The camera is not ready yet.')
      const form = new FormData()
      form.append('image', frame, 'capture.jpg')
      return api<{ count: number }>(`/students/${student.id}/face-enrollments/`, { method: 'POST', body: form })
    },
    onSuccess: (result) => {
      setCount(result.count)
      void refresh()
    },
  })
  const clear = useMutation({
    mutationFn: () => api<void>(`/students/${student.id}/face-enrollments/`, { method: 'DELETE' }),
    onSuccess: () => {
      setCount(0)
      void refresh()
    },
  })

  return (
    <Card
      title={`Face enrolment: ${student.full_name}`}
      action={
        <Button
          variant="ghost"
          aria-label="Close enrolment"
          onClick={() => {
            camera.stop()
            onDone()
          }}
        >
          <X size={16} aria-hidden="true" />
        </Button>
      }
    >
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <div className="aspect-video overflow-hidden rounded-md bg-ink">
            <video ref={camera.videoRef} muted playsInline className="h-full w-full object-cover" />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {!camera.active ? (
              <Button onClick={() => void camera.start()}>
                <Camera size={16} aria-hidden="true" />
                Start camera
              </Button>
            ) : (
              <>
                <Button disabled={enroll.isPending} onClick={() => enroll.mutate()}>
                  {enroll.isPending ? 'Checking…' : 'Capture'}
                </Button>
                <Button variant="secondary" onClick={camera.stop}>
                  Stop camera
                </Button>
              </>
            )}
          </div>
        </div>
        <div className="space-y-3 text-sm">
          <p>
            <span className="text-2xl font-semibold tabular-nums">{count}</span>
            <span className="text-muted"> of {TARGET_CAPTURES} recommended captures</span>
          </p>
          <ul className="list-disc space-y-1 pl-5 text-muted">
            <li>Only this student in view, face well lit.</li>
            <li>Take captures looking straight, slightly left, slightly right, and with glasses if worn.</li>
            <li>Photos are not saved. Only an encrypted numeric template is kept.</li>
          </ul>
          {camera.error && <Alert>{camera.error}</Alert>}
          {enroll.error && <Alert>{errorText(enroll.error)}</Alert>}
          {enroll.isSuccess && !enroll.error && <Alert tone="ok">Capture saved.</Alert>}
          {count > 0 && (
            <Button
              variant="danger"
              disabled={clear.isPending}
              onClick={() => {
                if (window.confirm(`Delete all face data for ${student.full_name}?`)) clear.mutate()
              }}
            >
              Delete face data
            </Button>
          )}
        </div>
      </div>
    </Card>
  )
}

export function Students() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Student | 'new' | null>(null)
  const [enrolling, setEnrolling] = useState<Student | null>(null)

  const classes = useQuery({ queryKey: ['class-groups'], queryFn: () => apiList<ClassGroup>('/class-groups/') })
  const students = useQuery({
    queryKey: ['students', search, page],
    queryFn: () => api<Page<Student>>(`/students/?page=${page}&search=${encodeURIComponent(search)}`),
    placeholderData: (previous) => previous,
  })
  const className = (id: number) => classes.data?.find((group) => group.id === id)?.name ?? '…'
  const pages = students.data ? Math.max(1, Math.ceil(students.data.count / 20)) : 1

  return (
    <>
      <PageHeader
        title="Students"
        description="Profiles, class membership, consent and face enrolment."
        action={
          isAdmin ? (
            <Button
              onClick={() => {
                setEnrolling(null)
                setEditing('new')
              }}
            >
              <Plus size={16} aria-hidden="true" />
              Add student
            </Button>
          ) : undefined
        }
      />

      {editing && (
        <div className="mb-5">
          <StudentForm
            key={editing === 'new' ? 'new' : editing.id}
            student={editing === 'new' ? null : editing}
            classes={classes.data ?? []}
            onDone={() => setEditing(null)}
          />
        </div>
      )}
      {enrolling && (
        <div className="mb-5">
          <EnrollPanel key={enrolling.id} student={enrolling} onDone={() => setEnrolling(null)} />
        </div>
      )}

      <Card>
        <div className="mb-3 max-w-xs">
          <Input
            type="search"
            aria-label="Search students"
            placeholder="Search by name or roll number"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
          />
        </div>
        {students.isLoading && <Spinner />}
        {students.isError && <Alert>{errorText(students.error)}</Alert>}
        {students.data?.results.length === 0 && (
          <EmptyState
            title={search ? 'No students match that search' : 'No students yet'}
            hint={search ? undefined : isAdmin ? 'Add a student to get started.' : 'You have no students in your classes yet.'}
          />
        )}
        {students.data && students.data.results.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] text-left text-sm">
              <thead>
                <tr className="text-xs text-muted">
                  <th className="pb-2 pr-3 font-medium">Roll no.</th>
                  <th className="pb-2 pr-3 font-medium">Name</th>
                  <th className="pb-2 pr-3 font-medium">Classes</th>
                  <th className="pb-2 pr-3 font-medium">Consent</th>
                  <th className="pb-2 pr-3 font-medium">Face data</th>
                  <th className="pb-2 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {students.data.results.map((student) => (
                  <tr key={student.id} className="border-t border-line">
                    <td className="py-2 pr-3 tabular-nums">{student.roll_number}</td>
                    <td className="py-2 pr-3 font-medium">{student.full_name}</td>
                    <td className="py-2 pr-3 text-muted">{student.class_groups.map(className).join(', ') || '–'}</td>
                    <td className="py-2 pr-3">
                      {student.consent_given ? <Badge tone="ok">Recorded</Badge> : <Badge tone="warn">Not recorded</Badge>}
                    </td>
                    <td className="py-2 pr-3">
                      {student.face_enrollment_count > 0 ? (
                        <Badge tone="brand">{student.face_enrollment_count} captures</Badge>
                      ) : (
                        <Badge>Not enrolled</Badge>
                      )}
                    </td>
                    <td className="py-2">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="secondary"
                          disabled={!student.consent_given}
                          title={student.consent_given ? undefined : 'Record consent first'}
                          onClick={() => {
                            setEditing(null)
                            setEnrolling(student)
                          }}
                        >
                          <Camera size={16} aria-hidden="true" />
                          Enrol face
                        </Button>
                        {isAdmin && (
                          <Button
                            variant="secondary"
                            aria-label={`Edit ${student.full_name}`}
                            onClick={() => {
                              setEnrolling(null)
                              setEditing(student)
                            }}
                          >
                            <Pencil size={16} aria-hidden="true" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {students.data && pages > 1 && (
          <div className="mt-3 flex items-center justify-between text-sm text-muted">
            <span>
              Page {page} of {pages} · {students.data.count} students
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
    </>
  )
}
