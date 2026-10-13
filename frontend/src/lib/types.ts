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
  room: number | null
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

export interface ClassGroup {
  id: number
  name: string
  academic_year: string
  student_count: number
}

export interface Subject {
  id: number
  code: string
  name: string
}

export interface Student {
  id: number
  roll_number: string
  full_name: string
  email: string
  phone_number: string
  is_active: boolean
  consent_given: boolean
  consent_recorded_at: string | null
  class_groups: number[]
  face_enrollment_count: number
}

export type AttendanceStatus = 'pending' | 'present' | 'late' | 'left_early' | 'absent'

export interface AttendanceRecord {
  id: number
  session: number
  student: number
  student_name: string
  roll_number: string
  status: AttendanceStatus
  source: 'auto' | 'manual'
  first_seen_at: string | null
  last_seen_at: string | null
  confidence: number | null
  note: string
}

export interface RecognizedFace {
  track?: number
  box: [number, number, number, number]
  band: 'confirmed' | 'review' | 'unknown'
  student: number | null
  student_name: string | null
  score: number
  reason: string
}

export interface RecognizeResult {
  faces: RecognizedFace[]
  enrolled_students: number
  changed: AttendanceRecord[]
}

export interface Room {
  id: number
  name: string
  capacity: number | null
}

export interface CameraDevice {
  id: number
  name: string
  source_type: 'webcam' | 'rtsp' | 'http' | 'file'
  source: string
  room: number | null
  is_enabled: boolean
  status: 'online' | 'offline' | 'error'
  last_error: string
  fps: number | null
  latency_ms: number | null
}

/** One update from a camera worker about the session it is serving. */
export interface LivePayload {
  camera: number
  camera_name: string
  status: 'online' | 'error'
  error: string
  session: number | null
  frame_size: [number, number]
  fps: number
  latency_ms: number
  faces: RecognizedFace[]
  changed: { student: number; status: AttendanceStatus; student_name: string | null }[]
}

export interface ReportRow {
  student: number
  roll_number: string
  full_name: string
  sessions: number
  present: number
  late: number
  left_early: number
  absent: number
  pending: number
  attendance_percent: number | null
}

export const STATUS_LABEL: Record<AttendanceStatus, string> = {
  pending: 'Pending review',
  present: 'Present',
  late: 'Late',
  left_early: 'Left early',
  absent: 'Absent',
}
