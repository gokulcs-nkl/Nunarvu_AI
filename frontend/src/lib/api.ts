const BASE = '/api/v1'

/** Error returned by the API, with per-field messages when the server provides them. */
export class ApiError extends Error {
  readonly status: number
  readonly fields: Record<string, string[]>

  constructor(status: number, message: string, fields: Record<string, string[]> = {}) {
    super(message)
    this.status = status
    this.fields = fields
  }
}

function readCookie(name: string): string | null {
  const match = document.cookie.split('; ').find((part) => part.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null
}

async function csrfToken(): Promise<string> {
  const existing = readCookie('csrftoken')
  if (existing) return existing
  const response = await fetch(`${BASE}/auth/csrf/`, { credentials: 'same-origin' })
  const body = (await response.json()) as { csrfToken: string }
  return body.csrfToken
}

function toApiError(status: number, body: unknown): ApiError {
  if (Array.isArray(body)) {
    return new ApiError(status, body.map(String).join(' '))
  }
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>
    const fields: Record<string, string[]> = {}
    for (const [key, value] of Object.entries(record)) {
      fields[key] = Array.isArray(value) ? value.map(String) : [String(value)]
    }
    const general = fields.detail ?? fields.non_field_errors
    const message = general?.join(' ') ?? Object.values(fields).flat().join(' ')
    return new ApiError(status, message || `Request failed (${status}).`, fields)
  }
  return new ApiError(status, `Request failed (${status}).`)
}

export async function api<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (method !== 'GET') {
    headers['X-CSRFToken'] = await csrfToken()
  }
  const isForm = options.body instanceof FormData
  if (options.body !== undefined && !isForm) {
    headers['Content-Type'] = 'application/json'
  }

  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      body: options.body === undefined ? undefined : isForm ? (options.body as FormData) : JSON.stringify(options.body),
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Check that the backend is running.')
  }

  if (response.status === 204) return undefined as T
  const text = await response.text()
  let body: unknown = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = null
  }
  if (!response.ok) throw toApiError(response.status, body)
  return body as T
}

export interface Page<T> {
  count: number
  results: T[]
}

/** Fetch a whole list in one request (up to the server's 200-row page limit). */
export async function apiList<T>(path: string): Promise<T[]> {
  const joiner = path.includes('?') ? '&' : '?'
  const page = await api<Page<T>>(`${path}${joiner}page_size=200`)
  return page.results
}
