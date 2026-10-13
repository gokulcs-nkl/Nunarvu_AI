import { BarChart3, CalendarClock, GraduationCap, LayoutDashboard, LogOut, School, Users, Video } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../lib/auth'
import { Logo } from './Logo'
import { ROLE_LABEL } from '../lib/types'
import type { Role } from '../lib/types'
import { Button } from './ui'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  roles: Role[]
}

const NAV: NavItem[] = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, roles: ['admin', 'teacher', 'viewer'] },
  { to: '/sessions', label: 'Sessions', icon: School, roles: ['admin', 'teacher', 'viewer'] },
  { to: '/students', label: 'Students', icon: Users, roles: ['admin', 'teacher'] },
  { to: '/reports', label: 'Reports', icon: BarChart3, roles: ['admin', 'teacher'] },
  { to: '/cameras', label: 'Cameras', icon: Video, roles: ['admin', 'teacher'] },
  { to: '/setup', label: 'Classes and rooms', icon: GraduationCap, roles: ['admin', 'teacher', 'viewer'] },
  { to: '/settings/periods', label: 'Period timings', icon: CalendarClock, roles: ['admin', 'teacher', 'viewer'] },
]

export function Layout() {
  const { user, logout } = useAuth()
  if (!user) return null
  const items = NAV.filter((item) => item.roles.includes(user.role))

  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <aside className="border-b border-line bg-surface md:w-60 md:shrink-0 md:border-r md:border-b-0">
        <div className="px-4 py-4">
          <NavLink to="/about" aria-label="About Nunarvu AI">
            <Logo size={28} />
          </NavLink>
          <p className="mt-1 text-xs text-muted">Classroom monitoring</p>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:pb-4">
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm ${
                  isActive ? 'bg-brand-soft font-medium text-brand-strong' : 'text-muted hover:bg-canvas hover:text-ink'
                }`
              }
            >
              <Icon size={16} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-end gap-3 border-b border-line bg-surface px-4 py-2">
          <div className="text-right">
            <p className="text-sm font-medium">{user.first_name || user.username}</p>
            <p className="text-xs text-muted">{ROLE_LABEL[user.role]}</p>
          </div>
          <Button variant="ghost" onClick={() => void logout()}>
            <LogOut size={16} aria-hidden="true" />
            Sign out
          </Button>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
