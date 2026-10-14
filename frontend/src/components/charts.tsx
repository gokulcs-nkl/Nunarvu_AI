import { Bar, BarChart, CartesianGrid, LabelList, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

// One series per chart, so one colour: a blue checked against the dark surface with the
// palette validator (lightness band, chroma and 3:1 contrast all pass).
const SERIES = '#5b8cf5'
const GRID = '#263039'
const SURFACE = '#141b22'
const AXIS_TEXT = { fontSize: 12, fill: '#94a3ae' }
const PERCENT_TICKS = [0, 25, 50, 75, 100]

export interface TrendPoint {
  date: string
  percent: number | null
  attended: number
  decided: number
}

export interface BarPoint {
  name: string
  percent: number | null
  attended: number
  decided: number
}

const shortDate = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })

function TooltipBox({ title, percent, attended, decided }: { title: string; percent: number | null; attended: number; decided: number }) {
  return (
    <div className="rounded-xl border border-line bg-raised px-3 py-2 text-xs shadow-[0_12px_30px_-10px_rgb(0_0_0/0.8)]">
      <p className="text-sm font-semibold tabular-nums text-ink">{percent === null ? 'No decided records' : `${percent}%`}</p>
      <p className="text-muted">{title}</p>
      <p className="tabular-nums text-muted">
        {attended} attended of {decided}
      </p>
    </div>
  )
}

/** Attendance percentage per day. A single series, so the card title names it and there is no legend. */
export function AttendanceTrend({ points }: { points: TrendPoint[] }) {
  return (
    <div className="h-64 w-full" role="img" aria-label="Line chart of attendance percentage by date. The same figures are in the table below.">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 12, right: 16, bottom: 0, left: -8 }}>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="date" tickFormatter={shortDate} tick={AXIS_TEXT} tickLine={false} axisLine={{ stroke: GRID }} minTickGap={24} />
          <YAxis domain={[0, 100]} ticks={PERCENT_TICKS} tickFormatter={(value: number) => `${value}%`} tick={AXIS_TEXT} tickLine={false} axisLine={false} width={48} />
          <Tooltip
            cursor={{ stroke: '#94a3ae', strokeWidth: 1 }}
            content={({ active, payload }) => {
              const point = active && payload?.[0] ? (payload[0].payload as TrendPoint) : null
              return point ? <TooltipBox title={shortDate(point.date)} {...point} /> : null
            }}
          />
          <Line
            type="linear"
            dataKey="percent"
            stroke={SERIES}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            connectNulls={false}
            dot={{ r: 4, fill: SERIES, stroke: SURFACE, strokeWidth: 2 }}
            activeDot={{ r: 6, fill: SERIES, stroke: SURFACE, strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Attendance percentage for each class or subject, as thin horizontal bars labelled at the tip. */
export function AttendanceBars({ points, label }: { points: BarPoint[]; label: string }) {
  const height = Math.max(96, points.length * 44 + 24)
  return (
    <div style={{ height }} className="w-full" role="img" aria-label={`Bar chart of attendance percentage by ${label}. The same figures are in the table below.`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} layout="vertical" margin={{ top: 4, right: 48, bottom: 0, left: 8 }} barCategoryGap={12}>
          <CartesianGrid horizontal={false} stroke={GRID} />
          <XAxis type="number" domain={[0, 100]} ticks={PERCENT_TICKS} tickFormatter={(value: number) => `${value}%`} tick={AXIS_TEXT} tickLine={false} axisLine={false} />
          <YAxis type="category" dataKey="name" tick={AXIS_TEXT} tickLine={false} axisLine={{ stroke: GRID }} width={132} />
          <Tooltip
            cursor={{ fill: '#1b242d' }}
            content={({ active, payload }) => {
              const point = active && payload?.[0] ? (payload[0].payload as BarPoint) : null
              return point ? <TooltipBox title={point.name} {...point} /> : null
            }}
          />
          <Bar dataKey="percent" fill={SERIES} maxBarSize={20} radius={[0, 4, 4, 0]} isAnimationActive={false}>
            <LabelList dataKey="percent" position="right" formatter={(value: unknown) => (value === null || value === undefined ? '' : `${String(value)}%`)} style={{ fontSize: 12, fill: '#eaf0f4' }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
