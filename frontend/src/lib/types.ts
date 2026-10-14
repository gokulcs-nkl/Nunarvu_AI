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
  people: number
  events: { id: number; kind: string; student: number | null; summary: string }[]
}

export interface ClassroomEvent {
  id: number
  session: number
  kind: 'hand_raise' | 'head_down' | 'phone' | 'unusual_activity'
  kind_label: string
  student: number | null
  student_name: string | null
  started_at: string
  ended_at: string | null
  confidence: number
  summary: string
  signals: { signal: string; value: number; threshold: number }[]
  review_status: 'unreviewed' | 'confirmed' | 'dismissed'
  reviewed_by_username: string | null
}

export interface ObservationSettings {
  hand_raise_enabled: boolean
  head_down_enabled: boolean
  phone_enabled: boolean
  unusual_activity_enabled: boolean
  hand_raise_seconds: number
  head_down_seconds: number
  phone_seconds: number
  unusual_activity_seconds: number
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

export interface TeacherProfile {
  id: number
  user: number
  name: string
  employee_code: string
}

export interface TimetableEntry {
  id: number
  class_group: number
  subject: number
  teacher: number | null
  room: number | null
  weekday: number
  period_number: number
}

interface BreakdownRow {
  id: number
  name: string
  sessions: number
  attended: number
  decided: number
  percent: number | null
}

export interface ReportSummary {
  totals: {
    records: number
    sessions: number
    students: number
    present: number
    late: number
    left_early: number
    absent: number
    pending: number
    attendance_percent: number | null
  }
  by_date: { date: string; attended: number; decided: number; percent: number | null }[]
  by_class: BreakdownRow[]
  by_subject: BreakdownRow[]
}

export interface ObservationSummaryRow {
  kind: string
  label: string
  total: number
  unreviewed: number
  confirmed: number
  dismissed: number
}

export interface SystemHealth {
  window_hours: number
  cameras: {
    id: number
    name: string
    room: string | null
    is_enabled: boolean
    status: 'online' | 'offline' | 'error'
    last_error: string
    fps: number | null
    latency_ms: number | null
    uptime_percent: number
    last_change: { status: 'online' | 'offline' | 'error'; detail: string; at: string } | null
  }[]
  alerts: { camera: number; message: string }[]
  pending_attendance: number
  unreviewed_observations: number
  students: { active: number; with_consent: number; enrolled_faces: number }
  models: { face: string; pose: string; objects: string }
}

export interface Term {
  id: number
  name: string
  start_date: string
  end_date: string
  minimum_attendance: number
}

export interface ForecastRow {
  student: number
  roll_number: string
  full_name: string
  class_group: number
  subject: number
  subject_code: string
  attended: number
  held: number
  percent: number | null
  remaining: number
  must_attend: number
  can_miss: number
  best_possible: number | null
  status: 'safe' | 'at_risk' | 'cannot_reach' | 'no_classes'
}

export interface ForecastResult {
  term: { id: number; name: string; start_date: string; end_date: string; minimum_attendance: number } | null
  detail?: string
  as_of?: string
  counts?: { at_risk: number; cannot_reach: number; total: number }
  rows?: ForecastRow[]
}

export interface Heatmap {
  kind: string
  grid: number
  total: number
  peak: number
  cells: number[][]
}
