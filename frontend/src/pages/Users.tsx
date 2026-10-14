import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { Alert, Badge, Button, Card, Input, PageHeader, Spinner } from '../components/ui'
import { api, apiList, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import { ROLE_LABEL } from '../lib/types'
import type { Role, User } from '../lib/types'

const ROLE_NOTE: Record<Role, string> = {
  admin: 'Everything, including users, students, cameras and settings.',
  teacher: 'Own classes and students; runs sessions, marks and corrects attendance, reviews observations.',
  viewer: 'Reads classes, timetable, sessions and attendance. No student personal data.',
}

function fieldErrors(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Something went wrong.'
  const parts = Object.entries(error.fields).map(([field, messages]) => `${field.replace('_', ' ')}: ${messages.join(' ')}`)
  return parts.length > 0 ? parts.join(' ') : error.message
}

function UserForm({ account, onDone }: { account: User | null; onDone: () => void }) {
  const queryClient = useQueryClient()
  const [username, setUsername] = useState(account?.username ?? '')
  const [firstName, setFirstName] = useState(account?.first_name ?? '')
  const [lastName, setLastName] = useState(account?.last_name ?? '')
  const [role, setRole] = useState<Role>(account?.role ?? 'teacher')
  const [active, setActive] = useState(account?.is_active ?? true)
  const [password, setPassword] = useState('')

  const save = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = { username, first_name: firstName, last_name: lastName, role, is_active: active }
      if (password) body.password = password
      return account
        ? api<User>(`/users/${account.id}/`, { method: 'PATCH', body })
        : api<User>('/users/', { method: 'POST', body })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['users'] })
      void queryClient.invalidateQueries({ queryKey: ['teachers'] })
      onDone()
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }

  return (
    <Card
      title={account ? `Edit ${account.username}` : 'Add user'}
      action={
        <Button variant="ghost" aria-label="Close form" onClick={onDone}>
          <X size={16} aria-hidden="true" />
        </Button>
      }
    >
      <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="user-username" className="mb-1 block text-sm font-medium">
            Username
          </label>
          <Input id="user-username" required autoComplete="off" value={username} onChange={(event) => setUsername(event.target.value)} />
        </div>
        <div>
          <label htmlFor="user-password" className="mb-1 block text-sm font-medium">
            {account ? 'New password (leave empty to keep)' : 'Password'}
          </label>
          <Input
            id="user-password"
            type="password"
            required={!account}
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <p className="mt-1 text-xs text-muted">At least 8 characters, not only numbers, not a common password.</p>
        </div>
        <div>
          <label htmlFor="user-first" className="mb-1 block text-sm font-medium">
            First name
          </label>
          <Input id="user-first" value={firstName} onChange={(event) => setFirstName(event.target.value)} />
        </div>
        <div>
          <label htmlFor="user-last" className="mb-1 block text-sm font-medium">
            Last name
          </label>
          <Input id="user-last" value={lastName} onChange={(event) => setLastName(event.target.value)} />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="user-role" className="mb-1 block text-sm font-medium">
            Role
          </label>
          <select
            id="user-role"
            className="h-9 w-full max-w-xs rounded-md border border-line bg-surface px-2 text-sm"
            value={role}
            onChange={(event) => setRole(event.target.value as Role)}
          >
            {(Object.keys(ROLE_LABEL) as Role[]).map((value) => (
              <option key={value} value={value}>
                {ROLE_LABEL[value]}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-muted">{ROLE_NOTE[role]}</p>
        </div>
        <label className="flex items-center gap-2 text-sm sm:col-span-2">
          <input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} />
          Active (can sign in)
        </label>
        {save.error && (
          <div className="sm:col-span-2">
            <Alert>{fieldErrors(save.error)}</Alert>
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

export function Users() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState<User | 'new' | null>(null)
  const users = useQuery({ queryKey: ['users'], queryFn: () => apiList<User>('/users/') })
  const remove = useMutation({
    mutationFn: (id: number) => api<void>(`/users/${id}/`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  return (
    <>
      <PageHeader
        title="Users"
        description="Who can sign in and what they can do."
        action={
          !editing ? (
            <Button onClick={() => setEditing('new')}>
              <Plus size={16} aria-hidden="true" />
              Add user
            </Button>
          ) : undefined
        }
      />
      {editing && (
        <div className="mb-5">
          <UserForm key={editing === 'new' ? 'new' : editing.id} account={editing === 'new' ? null : editing} onDone={() => setEditing(null)} />
        </div>
      )}
      <Card>
        {users.isLoading && <Spinner />}
        {users.isError && <Alert>Could not load users.</Alert>}
        {remove.error && <Alert>{fieldErrors(remove.error)}</Alert>}
        {users.data && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[34rem] text-left text-sm">
              <thead>
                <tr className="text-xs text-muted">
                  <th className="pb-2 pr-3 font-medium">Username</th>
                  <th className="pb-2 pr-3 font-medium">Name</th>
                  <th className="pb-2 pr-3 font-medium">Role</th>
                  <th className="pb-2 pr-3 font-medium">Status</th>
                  <th className="pb-2 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.data.map((account) => (
                  <tr key={account.id} className="border-t border-line">
                    <td className="py-2 pr-3 font-medium">
                      {account.username}
                      {account.id === user?.id && <span className="ml-2 font-normal text-muted">(you)</span>}
                    </td>
                    <td className="py-2 pr-3 text-muted">{[account.first_name, account.last_name].filter(Boolean).join(' ') || '–'}</td>
                    <td className="py-2 pr-3">{ROLE_LABEL[account.role]}</td>
                    <td className="py-2 pr-3">{account.is_active ? <Badge tone="ok">Active</Badge> : <Badge>Inactive</Badge>}</td>
                    <td className="py-2">
                      <div className="flex justify-end gap-2">
                        <Button variant="secondary" aria-label={`Edit ${account.username}`} onClick={() => setEditing(account)}>
                          <Pencil size={16} aria-hidden="true" />
                        </Button>
                        <Button
                          variant="danger"
                          aria-label={`Delete ${account.username}`}
                          disabled={account.id === user?.id || remove.isPending}
                          onClick={() => {
                            if (window.confirm(`Delete the account ${account.username}?`)) remove.mutate(account.id)
                          }}
                        >
                          <Trash2 size={16} aria-hidden="true" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
