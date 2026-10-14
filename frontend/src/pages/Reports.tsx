import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { useState } from 'react'

import { AttendanceBars, AttendanceTrend } from '../components/charts'
import { Alert, Card, EmptyState, Input, PageHeader, Spinner } from '../components/ui'
import { api, apiList } from '../lib/api'
import type { ClassGroup, ObservationSummaryRow, ReportRow, ReportSummary, Subject } from '../lib/types'

function Tile({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className="panel rounded-2xl px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {note && <p className="text-xs text-muted">{note}</p>}
    </div>
  )
}

function BreakdownTable({ rows, heading }: { rows: ReportSummary['by_class']; heading: string }) {
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer select-none text-muted">Show as table</summary>
      <table className="mt-2 w-full text-left tabular-nums">
        <thead>
          <tr className="text-xs text-muted">
            <th className="pb-1 pr-3 font-medium">{heading}</th>
            <th className="pb-1 pr-3 text-right font-medium">Sessions</th>
            <th className="pb-1 pr-3 text-right font-medium">Attended</th>
            <th className="pb-1 pr-3 text-right font-medium">Decided</th>
            <th className="pb-1 text-right font-medium">Attendance</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-t border-line">
              <td className="py-1 pr-3">{row.name}</td>
              <td className="py-1 pr-3 text-right">{row.sessions}</td>
              <td className="py-1 pr-3 text-right">{row.attended}</td>
              <td className="py-1 pr-3 text-right">{row.decided}</td>
              <td className="py-1 text-right">{row.percent === null ? '–' : `${row.percent}%`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  )
}

export function Reports() {
  const [classGroup, setClassGroup] = useState('')
  const [subject, setSubject] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const classes = useQuery({ queryKey: ['class-groups'], queryFn: () => apiList<ClassGroup>('/class-groups/') })
  const subjects = useQuery({ queryKey: ['subjects'], queryFn: () => apiList<Subject>('/subjects/') })

  const params = new URLSearchParams()
  if (classGroup) params.set('class_group', classGroup)
  if (subject) params.set('subject', subject)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  const query = params.toString()

  const summary = useQuery({ queryKey: ['report', 'summary', query], queryFn: () => api<ReportSummary>(`/reports/summary/?${query}`) })
  const students = useQuery({ queryKey: ['report', 'students', query], queryFn: () => api<ReportRow[]>(`/reports/attendance/?${query}`) })
  const observations = useQuery({
    queryKey: ['report', 'observations', query],
    queryFn: () => api<ObservationSummaryRow[]>(`/reports/observations/?${query}`),
  })

  const selectClass = 'h-9 w-full rounded-lg border border-line bg-canvas px-2 text-sm'
  const exportLink = (format: string) => `/api/v1/reports/attendance/?${query}${query ? '&' : ''}export=${format}`
  const linkClass = 'inline-flex h-9 items-center gap-2 key rounded-lg border border-line bg-raised px-3.5 text-sm font-semibold hover:border-muted/60'
  const totals = summary.data?.totals
  const observed = observations.data?.reduce((sum, row) => sum + row.total, 0) ?? 0

  return (
    <>
      <PageHeader
        title="Reports"
        description="Built from recorded attendance and observations. Late and left-early count as attended; records still pending review are left out of every percentage."
        action={
          <div className="flex gap-2">
            <a href={exportLink('csv')} className={linkClass}>
              <Download size={16} aria-hidden="true" />
              CSV
            </a>
            <a href={exportLink('pdf')} className={linkClass}>
              <Download size={16} aria-hidden="true" />
              PDF
            </a>
          </div>
        }
      />

      {/* One filter row above everything it scopes. */}
      <div className="mb-5 grid gap-3 panel rounded-2xl p-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor="report-class" className="mb-1 block text-xs text-muted">
            Class
          </label>
          <select id="report-class" className={selectClass} value={classGroup} onChange={(event) => setClassGroup(event.target.value)}>
            <option value="">All classes</option>
            {classes.data?.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name} ({group.academic_year})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="report-subject" className="mb-1 block text-xs text-muted">
            Subject
          </label>
          <select id="report-subject" className={selectClass} value={subject} onChange={(event) => setSubject(event.target.value)}>
            <option value="">All subjects</option>
            {subjects.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} · {item.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="report-from" className="mb-1 block text-xs text-muted">
            From
          </label>
          <Input id="report-from" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        </div>
        <div>
          <label htmlFor="report-to" className="mb-1 block text-xs text-muted">
            To
          </label>
          <Input id="report-to" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </div>
      </div>

      {summary.isLoading && <Spinner />}
      {summary.isError && <Alert>Could not load the report.</Alert>}

      {totals && totals.records === 0 && (
        <Card>
          <EmptyState title="No attendance recorded for these filters" hint="Reports fill in once sessions have been run." />
        </Card>
      )}

      {totals && summary.data && totals.records > 0 && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <Tile label="Attendance" value={totals.attendance_percent === null ? '–' : `${totals.attendance_percent}%`} />
            <Tile label="Sessions" value={totals.sessions} />
            <Tile label="Students" value={totals.students} />
            <Tile label="Absences" value={totals.absent} />
            <Tile label="Pending review" value={totals.pending} note={totals.pending > 0 ? 'Not in the percentage' : undefined} />
          </div>

          <Card title="Attendance by date">
            <AttendanceTrend points={summary.data.by_date} />
            <details className="mt-3 text-sm">
              <summary className="cursor-pointer select-none text-muted">Show as table</summary>
              <table className="mt-2 w-full max-w-md text-left tabular-nums">
                <thead>
                  <tr className="text-xs text-muted">
                    <th className="pb-1 pr-3 font-medium">Date</th>
                    <th className="pb-1 pr-3 text-right font-medium">Attended</th>
                    <th className="pb-1 pr-3 text-right font-medium">Decided</th>
                    <th className="pb-1 text-right font-medium">Attendance</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.data.by_date.map((row) => (
                    <tr key={row.date} className="border-t border-line">
                      <td className="py-1 pr-3">{row.date}</td>
                      <td className="py-1 pr-3 text-right">{row.attended}</td>
                      <td className="py-1 pr-3 text-right">{row.decided}</td>
                      <td className="py-1 text-right">{row.percent === null ? '–' : `${row.percent}%`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Attendance by class">
              <AttendanceBars points={summary.data.by_class} label="class" />
              <BreakdownTable rows={summary.data.by_class} heading="Class" />
            </Card>
            <Card title="Attendance by subject">
              <AttendanceBars points={summary.data.by_subject} label="subject" />
              <BreakdownTable rows={summary.data.by_subject} heading="Subject" />
            </Card>
          </div>

          <Card title="By student">
            {students.isLoading && <Spinner />}
            {students.data && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[44rem] text-left text-sm">
                  <thead>
                    <tr className="text-xs text-muted">
                      <th className="pb-2 pr-3 font-medium">Roll no.</th>
                      <th className="pb-2 pr-3 font-medium">Name</th>
                      <th className="pb-2 pr-3 text-right font-medium">Sessions</th>
                      <th className="pb-2 pr-3 text-right font-medium">Present</th>
                      <th className="pb-2 pr-3 text-right font-medium">Late</th>
                      <th className="pb-2 pr-3 text-right font-medium">Left early</th>
                      <th className="pb-2 pr-3 text-right font-medium">Absent</th>
                      <th className="pb-2 pr-3 text-right font-medium">Pending</th>
                      <th className="pb-2 text-right font-medium">Attendance</th>
                    </tr>
                  </thead>
                  <tbody className="tabular-nums">
                    {students.data.map((row) => (
                      <tr key={row.student} className="border-t border-line">
                        <td className="py-2 pr-3">{row.roll_number}</td>
                        <td className="py-2 pr-3 font-medium">{row.full_name}</td>
                        <td className="py-2 pr-3 text-right">{row.sessions}</td>
                        <td className="py-2 pr-3 text-right">{row.present}</td>
                        <td className="py-2 pr-3 text-right">{row.late}</td>
                        <td className="py-2 pr-3 text-right">{row.left_early}</td>
                        <td className="py-2 pr-3 text-right">{row.absent}</td>
                        <td className="py-2 pr-3 text-right">{row.pending}</td>
                        <td className="py-2 text-right font-medium">{row.attendance_percent === null ? '–' : `${row.attendance_percent}%`}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}

      {observations.data && observed > 0 && (
        <div className="mt-5">
          <Card title="Classroom observations">
            <p className="mb-2 text-xs text-muted">
              Counts of what the camera reported, and what teachers decided. An unreviewed or dismissed observation is not a finding.
            </p>
            <table className="w-full max-w-xl text-left text-sm tabular-nums">
              <thead>
                <tr className="text-xs text-muted">
                  <th className="pb-2 pr-3 font-medium">Observation</th>
                  <th className="pb-2 pr-3 text-right font-medium">Reported</th>
                  <th className="pb-2 pr-3 text-right font-medium">Confirmed</th>
                  <th className="pb-2 pr-3 text-right font-medium">Dismissed</th>
                  <th className="pb-2 text-right font-medium">Not reviewed</th>
                </tr>
              </thead>
              <tbody>
                {observations.data.map((row) => (
                  <tr key={row.kind} className="border-t border-line">
                    <td className="py-2 pr-3">{row.label}</td>
                    <td className="py-2 pr-3 text-right">{row.total}</td>
                    <td className="py-2 pr-3 text-right">{row.confirmed}</td>
                    <td className="py-2 pr-3 text-right">{row.dismissed}</td>
                    <td className="py-2 text-right">{row.unreviewed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}
    </>
  )
}
