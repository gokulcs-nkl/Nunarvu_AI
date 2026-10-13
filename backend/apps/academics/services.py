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
