import {
  Activity,
  BarChart3,
  CalendarClock,
  CalendarDays,
  Eye,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  School,
  Search,
  UserCog,
  Users,
  Video,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useAuth } from '../lib/auth'
import { ROLE_LABEL } from '../lib/types'
import type { Role } from '../lib/types'
import { useSystemHealth } from '../pages/Health'
import { Logo } from './Logo'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  roles: Role[]
}

const EVERYONE: Role[] = ['admin', 'teacher', 'viewer']
const STAFF: Role[] = ['admin', 'teacher']

const NAV: { heading: string; items: NavItem[] }[] = [
  { heading: 'Overview', items: [{ to: '/', label: 'Dashboard', icon: LayoutDashboard, roles: EVERYONE }] },
  {
    heading: 'Teaching',
    items: [
      { to: '/sessions', label: 'Sessions', icon: School, roles: EVERYONE },
      { to: '/students', label: 'Students', icon: Users, roles: STAFF },
      { to: '/observations', label: 'Observations', icon: Eye, roles: STAFF },
      { to: '/reports', label: 'Reports', icon: BarChart3, roles: STAFF },
    ],
  },
  {
    heading: 'School setup',
    items: [
      { to: '/timetable', label: 'Timetable', icon: CalendarDays, roles: EVERYONE },
      { to: '/settings/periods', label: 'Period timings', icon: CalendarClock, roles: EVERYONE },
      { to: '/setup', label: 'Classes and rooms', icon: GraduationCap, roles: EVERYONE },
    ],
  },
  {
    heading: 'System',
    items: [
      { to: '/cameras', label: 'Cameras', icon: Video, roles: STAFF },
      { to: '/health', label: 'System health', icon: Activity, roles: STAFF },
      { to: '/users', label: 'Users', icon: UserCog, roles: ['admin'] },
    ],
  },
]

/** Live camera status in the sidebar, so a stopped worker is noticed from any page. */
function CameraStatusCard() {
  const health = useSystemHealth()
  if (!health.data) return null
  const enabled = health.data.cameras.filter((camera) => camera.is_enabled)
  const online = enabled.filter((camera) => camera.status === 'online').length
  const failing = enabled.some((camera) => camera.status === 'error')
  const state = failing ? 'error' : online > 0 ? 'online' : 'offline'
  const dot = { online: 'bg-ok', offline: 'bg-muted', error: 'bg-danger' }[state]
  const text = { online: 'Camera worker running', offline: 'Camera worker not running', error: 'Camera problem' }[state]

  return (
    <Link to="/cameras" className="panel mx-3 mb-3 hidden rounded-xl px-3.5 py-3 text-sm hover:border-muted/50 md:block">
      <p className="flex items-center gap-2 font-semibold">
        <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" />
        {text}
      </p>
      <p className="mt-0.5 text-xs text-muted">
        {online} of {enabled.length} camera{enabled.length === 1 ? '' : 's'} online
      </p>
    </Link>
  )
}

function StudentSearch() {
  const navigate = useNavigate()
  const [term, setTerm] = useState('')

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    navigate(`/students?search=${encodeURIComponent(term.trim())}`)
  }

  return (
    <form onSubmit={handleSubmit} role="search" className="relative min-w-0 max-w-md flex-1">
      <Search size={16} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
      <input
        type="search"
        aria-label="Search students"
        placeholder="Search students"
        value={term}
        onChange={(event) => setTerm(event.target.value)}
        className="h-10 w-full rounded-xl border border-line bg-canvas pl-9 pr-3 text-sm text-ink shadow-[inset_0_1px_2px_rgb(0_0_0/0.5)] placeholder:text-muted"
      />
    </form>
  )
}

export function Layout() {
  const { user, logout } = useAuth()
  if (!user) return null
  const isStaff = user.role !== 'viewer'
  const displayName = user.first_name || user.username
  const initials = (user.first_name && user.last_name ? user.first_name[0] + user.last_name[0] : user.username.slice(0, 2)).toUpperCase()
  const groups = NAV.map((group) => ({ ...group, items: group.items.filter((item) => item.roles.includes(user.role)) })).filter(
    (group) => group.items.length > 0,
  )

  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <aside className="flex flex-col border-b border-line bg-[linear-gradient(180deg,var(--color-surface),var(--color-canvas))] md:sticky md:top-0 md:h-screen md:w-64 md:shrink-0 md:border-b-0 md:border-r">
        <div className="px-5 py-5">
          <NavLink to="/about" aria-label="About Nunarvu AI">
            <Logo size={30} />
          </NavLink>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col md:gap-0 md:overflow-y-auto">
          {groups.map((group) => (
            <div key={group.heading} className="flex gap-1 md:mb-4 md:flex-col md:gap-0.5">
              <p className="hidden px-3 pb-1.5 text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted md:block">{group.heading}</p>
              {group.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `relative flex items-center gap-3 whitespace-nowrap rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-raised text-ink shadow-[inset_0_1px_0_rgb(255_255_255/0.06),0_6px_14px_-8px_rgb(0_0_0/0.8)] before:absolute before:-left-3 before:top-2 before:hidden before:h-5 before:w-1 before:rounded-r before:bg-brand md:before:block'
                        : 'text-muted hover:bg-raised/60 hover:text-ink'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon size={17} aria-hidden="true" className={isActive ? 'text-brand' : ''} />
                      {label}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        {isStaff && <CameraStatusCard />}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-canvas/85 px-4 py-3 backdrop-blur md:px-8">
          {isStaff ? <StudentSearch /> : <div className="flex-1" />}
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden rounded-xl bg-brand-soft px-3 py-2 text-xs font-semibold tabular-nums text-brand-strong sm:block">
              {new Date().toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-raised text-xs font-bold text-brand-strong shadow-[inset_0_1px_0_rgb(255_255_255/0.08)]" aria-hidden="true">
                {initials}
              </span>
              <div className="hidden leading-tight sm:block">
                <p className="text-sm font-semibold">{displayName}</p>
                <p className="text-xs text-muted">{ROLE_LABEL[user.role]}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => void logout()}
              className="inline-flex h-9 items-center gap-2 rounded-xl px-3 text-sm font-medium text-muted hover:bg-raised hover:text-ink"
            >
              <LogOut size={16} aria-hidden="true" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </header>
        <main className="mx-auto w-full min-w-0 max-w-7xl flex-1 px-4 py-7 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
