from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F, Min, Sum
from django.utils import timezone

from apps.academics.models import ClassSession, Student
from vision.face import matcher

from .models import AttendanceRecord, PresenceWindow

Status = AttendanceRecord.Status
Source = AttendanceRecord.Source


@dataclass(frozen=True)
class Sighting:
    student_id: int
    band: str        # matcher.CONFIRMED or matcher.REVIEW
    score: float
    reason: str = ''


def window_index(session: ClassSession, at: datetime) -> int:
    elapsed = max(timedelta(0), at - session.starts_at)
    return int(elapsed // timedelta(minutes=settings.ATTENDANCE_WINDOW_MINUTES))


def _arrival_status(session: ClassSession, first_seen: datetime) -> str:
    late_after = session.starts_at + timedelta(minutes=settings.ATTENDANCE_LATE_AFTER_MINUTES)
    return Status.LATE if first_seen > late_after else Status.PRESENT


@transaction.atomic
def record_sightings(session: ClassSession, sightings: list[Sighting], at: datetime | None = None) -> list[AttendanceRecord]:
    """
    Apply one frame's matches to a session and return the attendance records that changed.

    - A confirmed sighting is counted in the current time window. Once a student has
      ATTENDANCE_CONFIRM_SIGHTINGS confirmed sightings they are marked present or late.
    - An uncertain sighting creates a pending record for teacher review; it never marks anyone present.
    - A record a teacher set manually is never overwritten.
    """
    at = at or timezone.now()
    changed: list[AttendanceRecord] = []
    records = {
        record.student_id: record
        for record in AttendanceRecord.objects.select_for_update().filter(
            session=session, student_id__in=[s.student_id for s in sightings],
        )
    }

    for sighting in sightings:
        record = records.get(sighting.student_id)

        if sighting.band == matcher.REVIEW:
            if record is None:
                record = AttendanceRecord.objects.create(
                    session=session, student_id=sighting.student_id, status=Status.PENDING, source=Source.AUTO,
                    first_seen_at=at, last_seen_at=at, confidence=sighting.score, note=sighting.reason[:255],
                )
                records[sighting.student_id] = record
                changed.append(record)
            continue

        if sighting.band != matcher.CONFIRMED:
            continue

        window, _ = PresenceWindow.objects.get_or_create(
            session=session, student_id=sighting.student_id, window_index=window_index(session, at),
            defaults={'first_seen_at': at},
        )
        window.sightings = F('sightings') + 1
        window.best_score = max(window.best_score, sighting.score)
        window.save(update_fields=['sightings', 'best_score'])

        if record is not None and record.source == Source.MANUAL:
            continue

        seen = PresenceWindow.objects.filter(
            session=session, student_id=sighting.student_id,
        ).aggregate(total=Sum('sightings'), first=Min('first_seen_at'))
        total = seen['total'] or 0
        # Arrival time is the first confirmed sighting, not the one that completed the confirmation.
        first_seen = seen['first'] or at

        if record is None:
            if total < settings.ATTENDANCE_CONFIRM_SIGHTINGS:
                continue
            record = AttendanceRecord.objects.create(
                session=session, student_id=sighting.student_id, status=_arrival_status(session, first_seen),
                source=Source.AUTO, first_seen_at=first_seen, last_seen_at=at, confidence=sighting.score,
            )
            records[sighting.student_id] = record
            changed.append(record)
            continue

        previous = record.status
        record.last_seen_at = at
        record.confidence = max(record.confidence or 0.0, sighting.score)
        if record.status == Status.PENDING and total >= settings.ATTENDANCE_CONFIRM_SIGHTINGS:
            record.status = _arrival_status(session, first_seen)
            record.first_seen_at = first_seen
            record.note = ''
        record.save(update_fields=['first_seen_at', 'last_seen_at', 'confidence', 'status', 'note', 'updated_at'])
        if record.status != previous:
            changed.append(record)

    return changed


def finalize_session(session: ClassSession) -> int:
    """
    Close out a session's attendance. Returns the number of students marked absent.

    - Automatically marked students last seen more than two windows before the end become "left early".
    - Every enrolled, active student with no record is marked absent.
    - Pending and manual records are left for the teacher.
    """
    if session.ends_at is not None:
        cutoff = session.ends_at - timedelta(minutes=2 * settings.ATTENDANCE_WINDOW_MINUTES)
        if cutoff > session.starts_at:
            AttendanceRecord.objects.filter(
                session=session, source=Source.AUTO, status__in=[Status.PRESENT, Status.LATE],
                last_seen_at__lt=cutoff,
            ).update(status=Status.LEFT_EARLY)

    recorded = AttendanceRecord.objects.filter(session=session).values_list('student_id', flat=True)
    missing = Student.objects.filter(class_groups=session.class_group, is_active=True).exclude(id__in=recorded)
    created = AttendanceRecord.objects.bulk_create([
        AttendanceRecord(session=session, student=student, status=Status.ABSENT, source=Source.AUTO)
        for student in missing
    ])
    return len(created)
