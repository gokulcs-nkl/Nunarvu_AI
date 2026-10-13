import { ArrowRight, ArrowUpRight, Cpu, ScanFace } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { Logo } from '../components/Logo'
import { useAuth } from '../lib/auth'

const REPO_URL = 'https://github.com/gokulcs-nkl/Nunarvu_AI'

/* ----------------------------------------------------------------------------
 * Illustrations. These are drawings of the product's screens, not screenshots,
 * and the people in them are abstract shapes.
 * ------------------------------------------------------------------------- */

function Person({ x, tone }: { x: number; tone: string }) {
  return (
    <g transform={`translate(${x} 0)`} fill={tone}>
      <circle cx="40" cy="46" r="20" />
      <path d="M4 130c0-28 16-44 36-44s36 16 36 44z" />
    </g>
  )
}

function FaceTag({ x, y, label, color }: { x: number; y: number; label: string; color: string }) {
  return (
    <g>
      <rect x={x} y={y} width="52" height="52" fill="none" stroke={color} strokeWidth="2.5" />
      <rect x={x - 1} y={y - 19} width={label.length * 5.6 + 12} height="17" rx="2" fill={color} />
      <text x={x + 5} y={y - 7} fontSize="9.5" fontWeight="600" fill="#fff">
        {label}
      </text>
    </g>
  )
}

function LiveScene() {
  return (
    <svg viewBox="0 0 400 225" className="block h-auto w-full" role="img" aria-label="Illustration of the live classroom view with labelled faces">
      <rect width="400" height="225" fill="#1a1f2b" />
      <rect y="150" width="400" height="75" fill="#141821" />
      <g transform="translate(0 78)">
        <Person x={40} tone="#3c4658" />
        <Person x={160} tone="#465168" />
        <Person x={280} tone="#3c4658" />
      </g>
      <FaceTag x={54} y={98} label="Asha · Confirmed" color="#17794a" />
      <FaceTag x={174} y={98} label="Needs review" color="#8a5a00" />
      <FaceTag x={294} y={98} label="Unrecognised" color="#5b6676" />
    </svg>
  )
}

const ROSTER = [
  { name: 'Asha R', status: 'Present', tone: 'bg-ok-soft text-ok' },
  { name: 'Bala K', status: 'Late', tone: 'bg-ok-soft text-ok' },
  { name: 'Chitra M', status: 'Pending review', tone: 'bg-warn-soft text-warn' },
  { name: 'Devi S', status: 'Absent', tone: 'bg-danger-soft text-danger' },
]

function Roster({ rows = ROSTER }: { rows?: typeof ROSTER }) {
  return (
    <ul className="divide-y divide-line text-[11px] leading-tight text-ink">
      {rows.map((row) => (
        <li key={row.name} className="flex items-center justify-between gap-2 px-3 py-2">
          <span className="truncate font-medium">{row.name}</span>
          <span className={`shrink-0 rounded-full px-2 py-0.5 font-medium ${row.tone}`}>{row.status}</span>
        </li>
      ))}
    </ul>
  )
}

function Browser({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`overflow-hidden rounded-lg border border-black/10 bg-surface shadow-2xl ${className}`}>
      <div className="flex items-center gap-1.5 border-b border-line bg-canvas px-3 py-2" aria-hidden="true">
        <span className="h-2 w-2 rounded-full bg-line" />
        <span className="h-2 w-2 rounded-full bg-line" />
        <span className="h-2 w-2 rounded-full bg-line" />
      </div>
      {children}
    </div>
  )
}

function Phone({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`overflow-hidden rounded-[1.6rem] border-[5px] border-night bg-surface shadow-2xl ${className}`}>
      <div className="mx-auto mt-1.5 h-1 w-10 rounded-full bg-line" aria-hidden="true" />
      {children}
    </div>
  )
}

function SessionMock() {
  return (
    <Browser>
      <div className="grid grid-cols-5">
        <div className="col-span-3 min-w-0 border-r border-line p-3">
          <LiveScene />
          <p className="mt-2 text-[10px] text-muted">1 confirmed · 1 needs review · 1 unrecognised</p>
        </div>
        <div className="col-span-2 min-w-0">
          <p className="border-b border-line px-3 py-2 text-[11px] font-semibold text-ink">CSE-A · Period 2</p>
          <Roster />
        </div>
      </div>
    </Browser>
  )
}

function PeriodsMock() {
  const periods = [
    ['Period 1', '09:00–09:50'],
    ['Period 2', '10:00–10:50'],
    ['Period 3', '11:10–12:00'],
  ]
  return (
    <Browser>
      <div className="flex gap-1 border-b border-line px-3 py-2 text-[10px] text-muted">
        <span className="rounded bg-brand-soft px-2 py-0.5 font-medium text-brand-strong">Default</span>
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
          <span key={day} className="px-1.5 py-0.5">
            {day}
          </span>
        ))}
      </div>
      <ul className="divide-y divide-line text-[11px] text-ink">
        {periods.map(([name, time]) => (
          <li key={name} className="flex justify-between px-3 py-2.5">
            <span className="font-medium">{name}</span>
            <span className="tabular-nums text-muted">{time}</span>
          </li>
        ))}
      </ul>
    </Browser>
  )
}

function ReportMock() {
  const rows = [
    ['Asha R', 96],
    ['Bala K', 88],
    ['Chitra M', 74],
    ['Devi S', 61],
  ] as const
  return (
    <Browser>
      <ul className="space-y-3 p-4 text-[11px] text-ink">
        {rows.map(([name, percent]) => (
          <li key={name}>
            <div className="mb-1 flex justify-between">
              <span className="font-medium">{name}</span>
              <span className="tabular-nums text-muted">{percent}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-canvas">
              <div className="h-1.5 rounded-full bg-brand" style={{ width: `${percent}%` }} />
            </div>
          </li>
        ))}
      </ul>
      <p className="border-t border-line px-4 py-2 text-[10px] text-muted">Illustrative figures</p>
    </Browser>
  )
}

function ReviewMock() {
  return (
    <Browser>
      <p className="border-b border-line px-3 py-2 text-[11px] font-semibold text-ink">Needs your review (1)</p>
      <div className="flex items-center justify-between gap-3 px-3 py-3 text-[11px]">
        <div>
          <p className="font-medium text-ink">Chitra M</p>
          <p className="text-muted">Match score is below the confirmation threshold.</p>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <span className="rounded border border-line px-2 py-1 font-medium text-ink">Mark present</span>
          <span className="rounded border border-line px-2 py-1 font-medium text-ink">Mark absent</span>
        </div>
      </div>
    </Browser>
  )
}

/* ----------------------------------------------------------------------------
 * Page building blocks
 * ------------------------------------------------------------------------- */

const buttonBase =
  'inline-flex h-12 items-center justify-center gap-2 px-7 text-xs font-semibold uppercase tracking-[0.14em] transition-colors'

function PrimaryLink({ to, children, onDark = false }: { to: string; children: ReactNode; onDark?: boolean }) {
  return (
    <Link to={to} className={`${buttonBase} ${onDark ? 'bg-white text-night hover:bg-white/85' : 'bg-night text-white hover:bg-night/85'}`}>
      {children}
    </Link>
  )
}

function Eyebrow({ children, onDark = false }: { children: ReactNode; onDark?: boolean }) {
  return <p className={`text-xs font-semibold uppercase tracking-[0.18em] ${onDark ? 'text-white/70' : 'text-muted'}`}>{children}</p>
}

function Feature({ title, text, visual, flip = false }: { title: string; text: string; visual: ReactNode; flip?: boolean }) {
  return (
    <div className="grid items-center gap-8 md:grid-cols-2 md:gap-16 [&>*]:min-w-0">
      <div className={flip ? 'md:order-2' : ''}>
        <h3 className="text-2xl font-semibold tracking-tight md:text-3xl">{title}</h3>
        <p className="mt-3 max-w-md text-base leading-relaxed text-muted">{text}</p>
      </div>
      <div className={`bg-canvas p-6 md:p-10 ${flip ? 'md:order-1' : ''}`}>{visual}</div>
    </div>
  )
}

const PRINCIPLES = [
  ['Consent comes first', 'A face can only be enrolled after consent is recorded for that student. Withdrawing consent deletes their face data.'],
  ['No video is kept', 'Frames are analysed in memory and discarded. Only an encrypted numeric template of each enrolled face is stored.'],
  ['The teacher decides', 'Uncertain matches wait for review, any record can be corrected, and the camera never overwrites a teacher’s decision.'],
  ['Unknown stays unknown', 'A face that matches nobody is shown as unrecognised. It is never given a name or a record.'],
  ['Every change is logged', 'Enrolments, corrections, exports and logins are written to an audit trail that administrators can read.'],
  ['Runs on your own machine', 'Recognition happens locally on the computer connected to the camera. Nothing is sent to a cloud service.'],
]

const ROADMAP = [
  ['Classroom observations', 'Hand raises, standing, leaving a seat and phone-like objects, reported as observations for the teacher to verify.'],
  ['Analytics and PDF reports', 'Attendance trends across dates, classes and subjects, with downloadable PDF reports.'],
  ['Packaged deployment', 'One-command setup with PostgreSQL, backups and health checks.'],
]

const STEPS = [
  ['Set up classes', 'Add classes, subjects, rooms and, if you want them, period timings for each day.'],
  ['Add students', 'Create student profiles and place them in their classes.'],
  ['Record consent and enrol', 'Tick consent for a student, then take about five captures of their face.'],
  ['Connect a camera', 'Use the laptop webcam, or add an IP camera by its stream address.'],
  ['Start a session', 'Start it by hand or from the timetable. The camera worker begins marking attendance.'],
  ['Review and report', 'Confirm uncertain matches, correct anything, and download the attendance report.'],
]

const SECTIONS = [
  ['#attendance', 'Attendance'],
  ['#features', 'Features'],
  ['#privacy', 'Privacy'],
  ['#roadmap', 'Roadmap'],
  ['#how', 'How it works'],
]

export function Landing() {
  const { user } = useAuth()
  const entry = user ? '/' : '/login'
  const entryLabel = user ? 'Open dashboard' : 'Sign in'

  return (
    <div className="overflow-x-clip bg-surface text-ink">
      {/* Hero */}
      <header className="overflow-x-clip bg-night text-white">
        <nav aria-label="Main" className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-5 py-5 md:px-10">
          <Link to="/about" aria-label="Nunarvu AI home">
            <Logo tone="light" size={30} />
          </Link>
          <div className="hidden items-center gap-8 text-sm text-white/80 md:flex">
            {SECTIONS.slice(1).map(([href, label]) => (
              <a key={href} href={href} className="hover:text-white">
                {label}
              </a>
            ))}
          </div>
          <Link to={entry} className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-[0.14em] hover:text-white/80">
            {entryLabel}
            <ArrowRight size={14} aria-hidden="true" />
          </Link>
        </nav>

        <div className="mx-auto grid max-w-7xl items-center gap-12 px-5 pb-0 pt-10 md:grid-cols-2 md:px-10 md:pt-16">
          <div className="min-w-0 pb-4 md:pb-24">
            <Eyebrow onDark>Classroom monitoring</Eyebrow>
            <h1 className="mt-5 text-5xl font-semibold leading-[1.02] tracking-tight md:text-7xl">Attendance that takes itself.</h1>
            <p className="mt-6 max-w-md text-lg leading-relaxed text-white/75">
              Nunarvu AI marks attendance for every period from a classroom camera, and leaves the uncertain cases to the teacher.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-5">
              <PrimaryLink to={entry} onDark>
                {entryLabel}
              </PrimaryLink>
              <a href="#how" className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-white/80 hover:text-white">
                See how it works
                <ArrowRight size={14} aria-hidden="true" />
              </a>
            </div>
          </div>
          <div className="relative min-w-0 pb-10 md:translate-y-10 md:pb-0">
            <SessionMock />
            <Phone className="absolute -right-4 bottom-0 hidden w-40 sm:block md:-bottom-6 md:-right-8 md:w-44">
              <p className="px-3 pb-1 pt-2 text-[10px] font-semibold text-ink">Today · Period 2</p>
              <Roster rows={ROSTER.slice(0, 3)} />
            </Phone>
          </div>
        </div>
      </header>

      {/* In-page section links */}
      <div className="sticky top-0 z-10 border-b border-line bg-surface/95 backdrop-blur">
        <nav aria-label="Sections" className="mx-auto flex max-w-7xl gap-7 overflow-x-auto px-5 py-4 text-xs font-semibold uppercase tracking-[0.14em] text-muted md:px-10">
          {SECTIONS.map(([href, label]) => (
            <a key={href} href={href} className="whitespace-nowrap hover:text-ink">
              {label}
            </a>
          ))}
        </nav>
      </div>

      <main>
        {/* Showcase */}
        <section id="attendance" className="mx-auto max-w-7xl scroll-mt-16 px-5 py-20 md:px-10 md:py-28">
          <div className="grid gap-10 md:grid-cols-2 md:gap-16">
            <h2 className="text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl">One record per student, per period.</h2>
            <div className="self-end">
              <p className="max-w-md text-lg leading-relaxed text-muted">
                Each period is its own session. A student is marked present after two confident sightings, late if they arrive after
                the grace time, and absent if they are never seen. Duplicates are blocked by the database, not by hope.
              </p>
              <div className="mt-7">
                <PrimaryLink to={entry}>{entryLabel}</PrimaryLink>
              </div>
            </div>
          </div>
          <div className="mt-14 grid gap-5 md:grid-cols-3">
            {[
              ['Sessions', <SessionMock key="s" />],
              ['Period timings', <PeriodsMock key="p" />],
              ['Reports', <ReportMock key="r" />],
            ].map(([label, visual]) => (
              <figure key={label as string} className="min-w-0 bg-canvas p-5">
                {visual}
                <figcaption className="mt-4 text-xs font-semibold uppercase tracking-[0.14em] text-muted">{label}</figcaption>
              </figure>
            ))}
          </div>
        </section>

        {/* Features */}
        <section id="features" className="scroll-mt-16 border-t border-line">
          <div className="mx-auto max-w-7xl px-5 py-20 md:px-10 md:py-28">
            <Eyebrow>What it does today</Eyebrow>
            <h2 className="mt-4 max-w-3xl text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl">Built around the way a class actually runs.</h2>
            <div className="mt-16 space-y-20 md:space-y-28">
              <Feature
                title="A live view of the room"
                text="A background worker reads the camera and shows every face it sees: confirmed, needing review, or unrecognised. If the camera drops, it retries by itself and tells you."
                visual={
                  <Browser>
                    <div className="p-3">
                      <LiveScene />
                    </div>
                  </Browser>
                }
              />
              <Feature
                flip
                title="Uncertain matches go to the teacher"
                text="A borderline match never marks anyone present. It appears in a review list with the reason, and the teacher confirms or rejects it in one click."
                visual={<ReviewMock />}
              />
              <Feature
                title="Timings that fit your timetable"
                text="Set one default schedule, give any weekday its own timings, or change a single date. Or set nothing at all and start sessions by hand."
                visual={<PeriodsMock />}
              />
              <Feature
                flip
                title="Reports from stored records"
                text="Attendance percentages by student, filtered by class, subject and date range, with CSV export. Records still awaiting review are left out of the percentage."
                visual={<ReportMock />}
              />
            </div>
          </div>
        </section>

        {/* Privacy principles */}
        <section id="privacy" className="scroll-mt-16 bg-canvas">
          <div className="mx-auto max-w-7xl px-5 py-20 md:px-10 md:py-28">
            <Eyebrow>Privacy and responsibility</Eyebrow>
            <h2 className="mt-4 max-w-3xl text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl">Designed for a room full of real people.</h2>
            <dl className="mt-14 grid gap-x-12 gap-y-10 md:grid-cols-3">
              {PRINCIPLES.map(([title, text]) => (
                <div key={title} className="border-t border-ink/15 pt-5">
                  <dt className="text-lg font-semibold tracking-tight">{title}</dt>
                  <dd className="mt-2 text-sm leading-relaxed text-muted">{text}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* Roadmap */}
        <section id="roadmap" className="mx-auto max-w-7xl scroll-mt-16 px-5 py-20 md:px-10 md:py-28">
          <Eyebrow>Not built yet</Eyebrow>
          <h2 className="mt-4 text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl">On the roadmap.</h2>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {ROADMAP.map(([title, text]) => (
              <article key={title} className="flex flex-col justify-between border border-line p-7">
                <div>
                  <span className="rounded-full bg-warn-soft px-2.5 py-1 text-xs font-medium text-warn">Planned</span>
                  <h3 className="mt-5 text-xl font-semibold tracking-tight">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{text}</p>
                </div>
                <ArrowUpRight size={20} aria-hidden="true" className="mt-8 text-muted" />
              </article>
            ))}
          </div>
        </section>

        {/* Steps */}
        <section id="how" className="scroll-mt-16 border-t border-line">
          <div className="mx-auto grid max-w-7xl gap-12 px-5 py-20 md:grid-cols-3 md:px-10 md:py-28">
            <h2 className="text-4xl font-semibold leading-[1.05] tracking-tight md:text-5xl">From setup to the first report.</h2>
            <ol className="grid gap-x-12 gap-y-10 sm:grid-cols-2 md:col-span-2">
              {STEPS.map(([title, text], index) => (
                <li key={title} className="border-t border-ink/15 pt-5">
                  <span className="text-xs font-semibold tabular-nums tracking-[0.14em] text-muted">{String(index + 1).padStart(2, '0')}</span>
                  <h3 className="mt-2 text-lg font-semibold tracking-tight">{title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">{text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Notes */}
        <section className="mx-auto grid max-w-7xl gap-5 px-5 pb-20 md:grid-cols-2 md:px-10 md:pb-28">
          <article className="bg-canvas p-8">
            <Cpu size={24} aria-hidden="true" />
            <h3 className="mt-5 text-xl font-semibold tracking-tight">What it needs</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              A computer with a camera. A graphics card makes it faster but is not required. How far away it can recognise a face
              depends on the camera: a laptop webcam covers the first few metres, and a full classroom needs a higher-resolution camera.
            </p>
          </article>
          <article className="bg-canvas p-8">
            <ScanFace size={24} aria-hidden="true" />
            <h3 className="mt-5 text-xl font-semibold tracking-tight">What it does not claim</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Recognition is not perfect, and its accuracy in your room has to be measured, not assumed. The system reports what a
              camera can observe. It does not judge attention, intent or character.
            </p>
          </article>
        </section>

        {/* Closing call to action */}
        <section className="bg-night text-white">
          <div className="mx-auto max-w-3xl px-5 py-24 text-center md:py-32">
            <h2 className="text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl">Take the register off your desk.</h2>
            <p className="mx-auto mt-5 max-w-md text-lg text-white/75">Sign in to set up a class and run your first session.</p>
            <div className="mt-9 flex flex-wrap items-center justify-center gap-5">
              <PrimaryLink to={entry} onDark>
                {entryLabel}
              </PrimaryLink>
              <a
                href={REPO_URL}
                target="_blank"
                rel="noreferrer"
                className={`${buttonBase} border border-white/40 text-white hover:border-white`}
              >
                View the source
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-night text-white/70">
        <div className="mx-auto grid max-w-7xl gap-10 border-t border-white/15 px-5 py-14 text-sm md:grid-cols-4 md:px-10">
          <div className="md:col-span-2">
            <Logo tone="light" size={28} />
            <p className="mt-4 max-w-xs">Period-based classroom attendance from a camera, with the teacher in control.</p>
          </div>
          <div>
            <p className="font-semibold text-white">Product</p>
            <ul className="mt-3 space-y-2">
              {SECTIONS.map(([href, label]) => (
                <li key={href}>
                  <a href={href} className="hover:text-white">
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="font-semibold text-white">Project</p>
            <ul className="mt-3 space-y-2">
              <li>
                <a href={REPO_URL} target="_blank" rel="noreferrer" className="hover:text-white">
                  Source code on GitHub
                </a>
              </li>
              <li>
                <Link to={entry} className="hover:text-white">
                  {entryLabel}
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <p className="mx-auto max-w-7xl px-5 pb-10 text-xs text-white/50 md:px-10">
          Nunarvu AI. Screens shown on this page are illustrations, and the people in them are not real.
        </p>
      </footer>
    </div>
  )
}
