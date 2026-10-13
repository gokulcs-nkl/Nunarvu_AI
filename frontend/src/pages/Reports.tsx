import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { useState } from 'react'

import { Alert, Card, EmptyState, Input, PageHeader, Spinner } from '../components/ui'
import { api, apiList, ApiError } from '../lib/api'
import type { ClassGroup, ReportRow, Subject } from '../lib/types'

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

  const report = useQuery({
    queryKey: ['report', query],
    queryFn: () => api<ReportRow[]>(`/reports/attendance/?${query}`),
  })
  const selectClass = 'h-9 w-full rounded-md border border-line bg-surface px-2 text-sm'
  const pendingTotal = report.data?.reduce((sum, row) => sum + row.pending, 0) ?? 0

  return (
    <>
      <PageHeader
        title="Attendance report"
        description="Totals per student from recorded sessions. Late and left-early count as attended; records still pending review are left out of the percentage."
        action={
          <a
            href={`/api/v1/reports/attendance/?${query}${query ? '&' : ''}export=csv`}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-surface px-3 text-sm font-medium hover:bg-canvas"
          >
            <Download size={16} aria-hidden="true" />
            Download CSV
          </a>
        }
      />

      <Card>
        <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
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

        {report.isLoading && <Spinner />}
        {report.isError && <Alert>{report.error instanceof ApiError ? report.error.message : 'Could not load the report.'}</Alert>}
        {report.data?.length === 0 && (
          <EmptyState title="No attendance recorded for these filters" hint="Records appear once sessions have been run." />
        )}
        {pendingTotal > 0 && (
          <div className="mb-3">
            <Alert tone="warn">
              {pendingTotal} record{pendingTotal === 1 ? ' is' : 's are'} still pending teacher review and not counted in the
              percentages.
            </Alert>
          </div>
        )}
        {report.data && report.data.length > 0 && (
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
                {report.data.map((row) => (
                  <tr key={row.student} className="border-t border-line">
                    <td className="py-2 pr-3">{row.roll_number}</td>
                    <td className="py-2 pr-3 font-medium">{row.full_name}</td>
                    <td className="py-2 pr-3 text-right">{row.sessions}</td>
                    <td className="py-2 pr-3 text-right">{row.present}</td>
                    <td className="py-2 pr-3 text-right">{row.late}</td>
                    <td className="py-2 pr-3 text-right">{row.left_early}</td>
                    <td className="py-2 pr-3 text-right">{row.absent}</td>
                    <td className="py-2 pr-3 text-right">{row.pending}</td>
                    <td className="py-2 text-right font-medium">
                      {row.attendance_percent === null ? '–' : `${row.attendance_percent}%`}
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
