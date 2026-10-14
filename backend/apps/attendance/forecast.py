"""
Attendance shortage forecast: for each student and subject, how many of the remaining classes
this term the student must attend to finish at or above the minimum attendance.

Counted so far: records from closed sessions in the term, where a teacher or the camera has
decided the status. Pending records are left out until decided. Remaining: timetable slots from
today to the end of the term, skipping holidays, days without period timings for that slot, and
sessions already finished or cancelled. Sessions started by hand cannot be foreseen and are not
counted ahead.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from django.db.models import Count, Q

from apps.academics.models import ClassSession, Holiday, Period, Student, Subject, Term, TimetableEntry

from .models import AttendanceRecord

Status = AttendanceRecord.Status
ATTENDED = [Status.PRESENT, Status.LATE, Status.LEFT_EARLY]
# A student who can afford to miss this many classes or fewer is shown as at risk.
SAFETY_MARGIN = 2

SAFE, AT_RISK, CANNOT_REACH, NO_CLASSES = 'safe', 'at_risk', 'cannot_reach', 'no_classes'


@dataclass(frozen=True)
class Forecast:
    student: int
    roll_number: str
    full_name: str
    class_group: int
    subject: int
    subject_code: str
    attended: int
    held: int
    percent: float | None
    remaining: int
    must_attend: int             # of the remaining classes
    can_miss: int                # of the remaining classes, while still reaching the minimum
    best_possible: float | None  # final percentage if every remaining class is attended
    status: str


def classes_needed(attended: int, held: int, remaining: int, minimum: float) -> int:
    """Smallest number of the remaining classes that brings the final percentage up to `minimum`."""
    needed = math.ceil(minimum / 100 * (held + remaining) - attended - 1e-9)
    return max(needed, 0)


def _periods_by_day(start: date, end: date) -> dict[date, set[int]]:
    """Period numbers with timings on each non-holiday day, with the same precedence as the scheduler."""
    by_date, by_weekday, default = defaultdict(set), defaultdict(set), set()
    for period in Period.objects.values('number', 'weekday', 'specific_date'):
        if period['specific_date']:
            by_date[period['specific_date']].add(period['number'])
        elif period['weekday'] is not None:
            by_weekday[period['weekday']].add(period['number'])
        else:
            default.add(period['number'])
    holidays = set(Holiday.objects.filter(date__range=(start, end)).values_list('date', flat=True))
    days = {}
    day = start
    while day <= end:
        if day not in holidays:
            days[day] = by_date.get(day) or by_weekday.get(day.weekday()) or default
        day += timedelta(days=1)
    return days


def remaining_classes(term: Term, today: date, class_group_ids=None) -> dict[tuple[int, int], int]:
    """(class group, subject) -> timetable classes still to come this term, including today's unfinished ones."""
    if today > term.end_date:
        return {}
    start = max(today, term.start_date)
    days = _periods_by_day(start, term.end_date)
    entries = TimetableEntry.objects.all()
    if class_group_ids is not None:
        entries = entries.filter(class_group_id__in=class_group_ids)
    entries = list(entries.values('class_group_id', 'subject_id', 'weekday', 'period_number'))

    finished = set(
        ClassSession.objects.filter(
            date__range=(start, term.end_date), period_number__isnull=False,
            status__in=[ClassSession.Status.CLOSED, ClassSession.Status.CANCELLED],
        ).values_list('class_group_id', 'date', 'period_number')
    )
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for day, numbers in days.items():
        for entry in entries:
            if entry['weekday'] != day.weekday() or entry['period_number'] not in numbers:
                continue
            if (entry['class_group_id'], day, entry['period_number']) in finished:
                continue
            counts[(entry['class_group_id'], entry['subject_id'])] += 1
    return dict(counts)


def forecast(term: Term, today: date, class_group_ids=None, subject_ids=None, teacher_user=None) -> list[Forecast]:
    records = AttendanceRecord.objects.filter(
        session__date__range=(term.start_date, min(today, term.end_date)),
        session__status=ClassSession.Status.CLOSED,
    )
    if class_group_ids is not None:
        records = records.filter(session__class_group_id__in=class_group_ids)
    if subject_ids is not None:
        records = records.filter(session__subject_id__in=subject_ids)
    so_far = {
        (row['student'], row['session__class_group'], row['session__subject']): (row['attended'], row['held'])
        for row in records.values('student', 'session__class_group', 'session__subject').annotate(
            attended=Count('id', filter=Q(status__in=ATTENDED)),
            held=Count('id', filter=~Q(status=Status.PENDING)),
        )
    }
    ahead = remaining_classes(term, today, class_group_ids)

    # Every (class, subject) pair with a past session or a timetable slot is forecast.
    pairs = {(group, subject) for (_, group, subject) in so_far} | set(ahead)
    if subject_ids is not None:
        pairs = {pair for pair in pairs if pair[1] in subject_ids}
    if teacher_user is not None:
        taught = set(
            TimetableEntry.objects.filter(teacher__user=teacher_user).values_list('class_group_id', 'subject_id')
        ) | set(ClassSession.objects.filter(teacher__user=teacher_user).values_list('class_group_id', 'subject_id'))
        pairs &= taught
    if not pairs:
        return []

    codes = dict(Subject.objects.filter(id__in={subject for _, subject in pairs}).values_list('id', 'code'))
    students_by_group = defaultdict(list)
    for student in Student.objects.filter(is_active=True, class_groups__in={group for group, _ in pairs}).values(
        'id', 'roll_number', 'full_name', 'class_groups',
    ):
        students_by_group[student['class_groups']].append(student)

    minimum = term.minimum_attendance
    rows = []
    for group, subject in pairs:
        remaining = ahead.get((group, subject), 0)
        for student in students_by_group.get(group, []):
            attended, held = so_far.get((student['id'], group, subject), (0, 0))
            total = held + remaining
            if total == 0:
                status, must, can_miss, best = NO_CLASSES, 0, 0, None
            else:
                must = classes_needed(attended, held, remaining, minimum)
                can_miss = max(remaining - must, 0)
                best = round(100 * (attended + remaining) / total, 1)
                below_now = bool(held) and 100 * attended / held < minimum
                if must > remaining:
                    status = CANNOT_REACH
                elif must == 0:
                    # Meets the minimum even attending none of the remaining classes.
                    status = SAFE
                elif can_miss <= SAFETY_MARGIN or below_now:
                    status = AT_RISK
                else:
                    status = SAFE
            rows.append(Forecast(
                student=student['id'], roll_number=student['roll_number'], full_name=student['full_name'],
                class_group=group, subject=subject, subject_code=codes.get(subject, ''),
                attended=attended, held=held, percent=round(100 * attended / held, 1) if held else None,
                remaining=remaining, must_attend=min(must, remaining), can_miss=can_miss,
                best_possible=best, status=status,
            ))
    order = {CANNOT_REACH: 0, AT_RISK: 1, SAFE: 2, NO_CLASSES: 3}
    rows.sort(key=lambda row: (order[row.status], row.can_miss, row.roll_number, row.subject_code))
    return rows


def as_dicts(rows: list[Forecast]) -> list[dict]:
    return [asdict(row) for row in rows]
