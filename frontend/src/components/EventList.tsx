import { useMutation, useQueryClient } from '@tanstack/react-query'

import { api, ApiError } from '../lib/api'
import type { ClassroomEvent } from '../lib/types'
import { Alert, Badge, Button } from './ui'

const REVIEW_TONE = { unreviewed: 'warn', confirmed: 'ok', dismissed: 'neutral' } as const
const REVIEW_LABEL = { unreviewed: 'Not reviewed', confirmed: 'Confirmed', dismissed: 'Dismissed' } as const

const SIGNAL_LABEL: Record<string, string> = {
  wrist_above_shoulder: 'Wrist above shoulder (shoulder-widths)',
  nose_above_shoulders: 'Nose above shoulder line (shoulder-widths)',
  phone_like_object_score: 'Phone-like object score',
  fast_moving_people_close_together: 'Fast-moving people close together',
  held_seconds: 'Held for (seconds)',
}

const clock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

function who(event: ClassroomEvent): string {
  if (event.kind === 'unusual_activity') return 'Room'
  return event.student_name ?? 'Unidentified person'
}

/** Observations with what was measured, and buttons for the teacher's decision. */
export function EventList({ events, canReview, showDate = false }: { events: ClassroomEvent[]; canReview: boolean; showDate?: boolean }) {
  const queryClient = useQueryClient()
  const review = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ClassroomEvent['review_status'] }) =>
      api<ClassroomEvent>(`/events/${id}/review/`, { method: 'POST', body: { status } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['events'] }),
  })

  return (
    <>
      {review.error && <Alert>{review.error instanceof ApiError ? review.error.message : 'Could not save the review.'}</Alert>}
      <ul className="divide-y divide-line">
        {events.map((event) => (
          <li key={event.id} className="py-3 text-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 font-medium">
                  {event.kind_label}
                  <span className="font-normal text-muted">{who(event)}</span>
                  <Badge tone={REVIEW_TONE[event.review_status]}>{REVIEW_LABEL[event.review_status]}</Badge>
                </p>
                <p className="mt-0.5 text-muted">{event.summary}</p>
                <p className="mt-0.5 text-xs tabular-nums text-muted">
                  {showDate ? `${new Date(event.started_at).toLocaleDateString(undefined, { dateStyle: 'medium' })} · ` : ''}
                  {clock(event.started_at)}
                  {event.ended_at ? ` to ${clock(event.ended_at)}` : ' · ongoing'} · model confidence {event.confidence.toFixed(2)}
                  {event.reviewed_by_username ? ` · reviewed by ${event.reviewed_by_username}` : ''}
                </p>
                {event.signals.length > 0 && (
                  <details className="mt-1 text-xs text-muted">
                    <summary className="cursor-pointer select-none">What was measured</summary>
                    <ul className="mt-1 space-y-0.5 tabular-nums">
                      {event.signals.map((signal) => (
                        <li key={signal.signal}>
                          {SIGNAL_LABEL[signal.signal] ?? signal.signal}: {signal.value} (threshold {signal.threshold})
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
              {canReview && (
                <div className="flex shrink-0 gap-2">
                  {event.review_status !== 'confirmed' && (
                    <Button variant="secondary" disabled={review.isPending} onClick={() => review.mutate({ id: event.id, status: 'confirmed' })}>
                      Confirm
                    </Button>
                  )}
                  {event.review_status !== 'dismissed' && (
                    <Button variant="secondary" disabled={review.isPending} onClick={() => review.mutate({ id: event.id, status: 'dismissed' })}>
                      Dismiss
                    </Button>
                  )}
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </>
  )
}
