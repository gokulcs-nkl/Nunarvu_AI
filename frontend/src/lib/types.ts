export type Role = 'admin' | 'teacher' | 'viewer'

export interface User {
  id: number
  username: string
  first_name: string
  last_name: string
  email: string
  is_active: boolean
  role: Role
}

export interface Period {
  id: number
  number: number
  name: string
  weekday: number | null
  specific_date: string | null
  start_time: string
  end_time: string
}

export interface ClassSession {
  id: number
  class_group: number
  class_group_name: string
  subject: number
  subject_code: string
  date: string
  period_number: number | null
  starts_at: string
  ends_at: string | null
  status: 'scheduled' | 'active' | 'closed' | 'cancelled'
  source: 'timetable' | 'manual'
}

export const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] as const

export const ROLE_LABEL: Record<Role, string> = {
  admin: 'Administrator',
  teacher: 'Teacher',
  viewer: 'Viewer',
}
