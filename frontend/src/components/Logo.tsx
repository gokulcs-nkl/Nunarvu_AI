/** The Nunarvu AI mark: an N inside a camera viewfinder. It carries its own dark tile, so it works on any background. */
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" className="shrink-0">
      <rect width="64" height="64" rx="14" fill="#0b0d12" />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13 22v-6a3 3 0 0 1 3-3h6M51 42v6a3 3 0 0 1-3 3h-6M22 51h-6a3 3 0 0 1-3-3v-6" stroke="#ffffff" strokeWidth="3.5" />
        <path d="M42 13h6a3 3 0 0 1 3 3v6" stroke="#6ea0ff" strokeWidth="3.5" />
        <path d="M24 42V22l16 20V22" stroke="#ffffff" strokeWidth="5" />
      </g>
    </svg>
  )
}

/** Mark plus wordmark. `tone` is the colour of the text, to suit a light or dark background. */
export function Logo({ size = 28, tone = 'dark' }: { size?: number; tone?: 'dark' | 'light' }) {
  return (
    <span className={`inline-flex items-center gap-2 font-semibold tracking-tight ${tone === 'light' ? 'text-white' : 'text-ink'}`}>
      <LogoMark size={size} />
      <span style={{ fontSize: size * 0.64 }}>
        Nunarvu <span className={tone === 'light' ? 'text-[#8fb4ff]' : 'text-brand'}>AI</span>
      </span>
    </span>
  )
}
