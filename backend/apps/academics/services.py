from datetime import date as date_type, datetime

from django.utils import timezone

from .models import ClassSession, Holiday, Period, TimetableEntry


def periods_for_date(day: date_type) -> list[Period]:
    """
    Period timings that apply on `day`: that date's own timings if any exist,
    otherwise that weekday's, otherwise the default schedule.
    """
    for scope in (
        Period.objects.filter(specific_date=day),
        Period.objects.filter(weekday=day.weekday()),
        Period.objects.filter(weekday__isnull=True, specific_date__isnull=True),
    ):
        periods = list(scope.order_by('number'))
        if periods:
            return periods
    return []


def generate_sessions_for_date(day: date_type) -> int:
    """Create the timetable sessions for `day`. Safe to run repeatedly. Returns sessions created."""
    if Holiday.objects.filter(date=day).exists():
        return 0

    periods = {period.number: period for period in periods_for_date(day)}
    if not periods:
        return 0

    tz = timezone.get_current_timezone()
    created_count = 0
    entries = TimetableEntry.objects.filter(weekday=day.weekday()).select_related('class_group', 'subject')
    for entry in entries:
        period = periods.get(entry.period_number)
        if period is None:
            continue
        _, created = ClassSession.objects.get_or_create(
            class_group=entry.class_group,
            date=day,
            period_number=entry.period_number,
            defaults={
                'subject': entry.subject,
                'teacher': entry.teacher,
                'room': entry.room,
                'starts_at': timezone.make_aware(datetime.combine(day, period.start_time), tz),
                'ends_at': timezone.make_aware(datetime.combine(day, period.end_time), tz),
                'source': ClassSession.Source.TIMETABLE,
            },
        )
        created_count += created
    return created_count


def run_schedule(now: datetime | None = None) -> dict:
    """
    Keep timetable sessions in step with the clock: create today's sessions, start the ones
    whose period has begun and close the ones whose period is over. Sessions started by hand
    are left alone. Safe to call as often as you like.
    """
    from apps.attendance.services import finalize_session

    now = now or timezone.now()
    created = generate_sessions_for_date(timezone.localtime(now).date())
    timetable = ClassSession.objects.filter(source=ClassSession.Source.TIMETABLE)

    started = timetable.filter(
        status=ClassSession.Status.SCHEDULED, starts_at__lte=now, ends_at__gt=now,
    ).update(status=ClassSession.Status.ACTIVE)

    closed = 0
    for session in timetable.filter(status=ClassSession.Status.ACTIVE, ends_at__lte=now):
        session.status = ClassSession.Status.CLOSED
        session.save(update_fields=['status'])
        finalize_session(session)
        closed += 1
    # A period that came and went without ever starting (the scheduler was not running) is closed
    # without marking anyone: nobody was watching, so absence cannot be inferred.
    for session in timetable.filter(status=ClassSession.Status.SCHEDULED, ends_at__lte=now):
        session.status = ClassSession.Status.CLOSED
        session.save(update_fields=['status'])
        closed += 1
    return {'created': created, 'started': started, 'closed': closed}
