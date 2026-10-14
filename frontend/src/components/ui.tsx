import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  // Dark text on the bright accent keeps the label well above 4.5:1 contrast.
  primary: 'key bg-brand text-night hover:bg-brand-strong',
  secondary: 'key bg-raised text-ink border border-line hover:border-muted/60',
  danger: 'key bg-raised text-danger border border-line hover:bg-danger-soft',
  ghost: 'text-muted hover:bg-raised hover:text-ink',
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      type="button"
      {...props}
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-lg px-3.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_STYLES[variant]} ${className}`}
    />
  )
}

export function Input({ className = '', ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`h-9 w-full rounded-lg border border-line bg-canvas px-3 text-sm text-ink shadow-[inset_0_1px_2px_rgb(0_0_0/0.5)] placeholder:text-muted disabled:opacity-60 aria-[invalid=true]:border-danger ${className}`}
    />
  )
}

export function Card({ title, action, children }: { title?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="panel rounded-2xl">
      {(title || action) && (
        <header className="flex min-h-14 items-center justify-between gap-3 border-b border-line px-5 py-2.5">
          <h2 className="text-[0.95rem] font-semibold tracking-tight">{title}</h2>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  )
}

type Tone = 'neutral' | 'ok' | 'warn' | 'danger' | 'brand'

const TONE_STYLES: Record<Tone, string> = {
  neutral: 'bg-raised text-muted',
  ok: 'bg-ok-soft text-ok',
  warn: 'bg-warn-soft text-warn',
  danger: 'bg-danger-soft text-danger',
  brand: 'bg-brand-soft text-brand-strong',
}

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${TONE_STYLES[tone]}`}>
      {children}
    </span>
  )
}

export function Alert({ tone = 'danger', children }: { tone?: 'danger' | 'ok' | 'warn'; children: ReactNode }) {
  const border = { danger: 'border-danger/30', ok: 'border-ok/30', warn: 'border-warn/30' }[tone]
  return (
    <div role={tone === 'danger' ? 'alert' : 'status'} className={`rounded-xl border px-3.5 py-2.5 text-sm ${border} ${TONE_STYLES[tone]}`}>
      {children}
    </div>
  )
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-brand" aria-hidden="true" />
      {label}
    </div>
  )
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
      <p className="text-sm font-semibold">{title}</p>
      {hint && <p className="max-w-md text-sm text-muted">{hint}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

/** Small square that holds an icon, used at the head of stat tiles and list rows. */
export function IconTile({ children, tone = 'brand' }: { children: ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl shadow-[inset_0_1px_0_rgb(255_255_255/0.08)] ${TONE_STYLES[tone]}`} aria-hidden="true">
      {children}
    </span>
  )
}
