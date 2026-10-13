import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { Alert, Button, Card, EmptyState, Input, PageHeader, Spinner } from '../components/ui'
import { api, apiList, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { ClassGroup, Room, Subject } from '../lib/types'

interface FieldSpec {
  name: string
  label: string
  placeholder: string
  optional?: boolean
}

function SimpleList<T extends { id: number }>({
  title,
  path,
  queryKey,
  fields,
  describe,
  editable,
}: {
  title: string
  path: string
  queryKey: string
  fields: [FieldSpec, FieldSpec]
  describe: (item: T) => { primary: string; secondary: string }
  editable: boolean
}) {
  const queryClient = useQueryClient()
  const [values, setValues] = useState<Record<string, string>>({})
  const list = useQuery({ queryKey: [queryKey], queryFn: () => apiList<T>(path) })
  const refresh = () => queryClient.invalidateQueries({ queryKey: [queryKey] })

  const create = useMutation({
    // Empty optional fields are left out so the server stores them as blank.
    mutationFn: () =>
      api<T>(path, { method: 'POST', body: Object.fromEntries(Object.entries(values).filter(([, value]) => value !== '')) }),
    onSuccess: () => {
      setValues({})
      return refresh()
    },
  })
  const remove = useMutation({
    mutationFn: (id: number) => api<void>(`${path}${id}/`, { method: 'DELETE' }),
    onSuccess: refresh,
  })
  const failure = create.error ?? remove.error

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    create.mutate()
  }

  return (
    <Card title={title}>
      {list.isLoading && <Spinner />}
      {list.isError && <Alert>{list.error.message}</Alert>}
      {list.data?.length === 0 && <EmptyState title={`No ${title.toLowerCase()} yet`} />}
      {list.data && list.data.length > 0 && (
        <ul className="divide-y divide-line">
          {list.data.map((item) => {
            const { primary, secondary } = describe(item)
            return (
              <li key={item.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <div>
                  <p className="font-medium">{primary}</p>
                  <p className="text-muted">{secondary}</p>
                </div>
                {editable && (
                  <Button
                    variant="danger"
                    aria-label={`Delete ${primary}`}
                    disabled={remove.isPending}
                    onClick={() => {
                      if (window.confirm(`Delete ${primary}? Anything that depends on it may be deleted too.`)) remove.mutate(item.id)
                    }}
                  >
                    <Trash2 size={16} aria-hidden="true" />
                  </Button>
                )}
              </li>
            )
          })}
        </ul>
      )}
      {editable && (
        <form onSubmit={handleSubmit} className="mt-4 flex flex-wrap items-end gap-3 border-t border-line pt-4">
          {fields.map((field) => (
            <div key={field.name} className="min-w-32 flex-1">
              <label htmlFor={`${queryKey}-${field.name}`} className="mb-1 block text-xs text-muted">
                {field.label}
              </label>
              <Input
                id={`${queryKey}-${field.name}`}
                required={!field.optional}
                placeholder={field.placeholder}
                value={values[field.name] ?? ''}
                onChange={(event) => setValues({ ...values, [field.name]: event.target.value })}
              />
            </div>
          ))}
          <Button type="submit" disabled={create.isPending}>
            Add
          </Button>
        </form>
      )}
      {failure && (
        <div className="mt-3">
          <Alert>{failure instanceof ApiError ? failure.message : 'Something went wrong.'}</Alert>
        </div>
      )}
    </Card>
  )
}

export function Setup() {
  const { user } = useAuth()
  const editable = user?.role === 'admin'

  return (
    <>
      <PageHeader title="Classes, subjects and rooms" description="The class groups students belong to, the subjects taught to them, and the rooms cameras are placed in." />
      <div className="grid gap-5 lg:grid-cols-3">
        <SimpleList<ClassGroup>
          title="Classes"
          path="/class-groups/"
          queryKey="class-groups"
          editable={editable}
          fields={[
            { name: 'name', label: 'Class name', placeholder: 'CSE-A' },
            { name: 'academic_year', label: 'Academic year', placeholder: '2026-27' },
          ]}
          describe={(item) => ({
            primary: item.name,
            secondary: `${item.academic_year} · ${item.student_count} student${item.student_count === 1 ? '' : 's'}`,
          })}
        />
        <SimpleList<Subject>
          title="Subjects"
          path="/subjects/"
          queryKey="subjects"
          editable={editable}
          fields={[
            { name: 'code', label: 'Code', placeholder: 'MA101' },
            { name: 'name', label: 'Name', placeholder: 'Mathematics' },
          ]}
          describe={(item) => ({ primary: item.code, secondary: item.name })}
        />
        <SimpleList<Room>
          title="Rooms"
          path="/rooms/"
          queryKey="rooms"
          editable={editable}
          fields={[
            { name: 'name', label: 'Room name', placeholder: 'Room 101' },
            { name: 'capacity', label: 'Seats (optional)', placeholder: '30', optional: true },
          ]}
          describe={(item) => ({ primary: item.name, secondary: item.capacity ? `${item.capacity} seats` : 'Capacity not set' })}
        />
      </div>
    </>
  )
}
