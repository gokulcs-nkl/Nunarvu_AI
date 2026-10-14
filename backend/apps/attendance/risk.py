"""
Early warning for students whose attendance suggests they may be disengaging.

This is a transparent rule, not a trained model. Each signal below adds a fixed number of
points, and every point is reported with the signal that produced it, so a teacher can see
exactly why a student was flagged and judge whether it is fair. A high score means
"worth a conversation", never a conclusion about the student or a prediction of dropout.

The signals follow what attendance research and the Indian state early-warning programmes use:
a low overall rate, a rate that is falling, several subjects in trouble at once, and a run of
consecutive absences, which is the strongest single warning sign.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

from django.db.models import Count, Q

from apps.academics.models import ClassSession, Student, Term

from .forecast import ATTENDED, AT_RISK, CANNOT_REACH, forecast
from .models import AttendanceRecord

Status = AttendanceRecord.Status

# How many points each signal contributes, and the thresholds that trigger it.
BELOW_MINIMUM_POINTS = 30
WELL_BELOW_MINIMUM_POINTS = 20      # added on top when far below, see WELL_BELOW_GAP
WELL_BELOW_GAP = 15                 # percentage points under the minimum
FALLING_POINTS = 20
FALLING_DROP = 10                   # percentage points lower in the recent window
CONSECUTIVE_POINTS = 25
CONSECUTIVE_ABSENCES = 3
SUBJECTS_AT_RISK_POINTS = 15        # when two or more subjects are at risk
CANNOT_REACH_POINTS = 20

RECENT_SESSIONS = 10                # the recent window used for the trend

LOW, MEDIUM, HIGH = 'low', 'medium', 'high'
MEDIUM_FROM, HIGH_FROM = 25, 50


@dataclass(frozen=True)
class Signal:
    name: str
    detail: str
    points: int


@dataclass(frozen=True)
class RiskRow:
    student: int
    roll_number: str
    full_name: str
    class_group: int | None
    percent: float | None
    attended: int
    held: int
    consecutive_absences: int
    subjects_at_risk: int
    score: int
    band: str
    signals: list = field(default_factory=list)
    guardian_contact: str = ''


def band_for(score: int) -> str:
    if score >= HIGH_FROM:
        return HIGH
    if score >= MEDIUM_FROM:
        return MEDIUM
    return LOW


def consecutive_absences(student_id: int, term: Term, today: date) -> int:
    """How many of the student's most recent closed sessions, in a row, they were absent from."""
    recent = (
        AttendanceRecord.objects.filter(
            student_id=student_id, session__status=ClassSession.Status.CLOSED,
            session__date__range=(term.start_date, min(today, term.end_date)),
        )
        .exclude(status=Status.PENDING)
        .order_by('-session__date', '-session__starts_at')
        .values_list('status', flat=True)[:30]
    )
    run = 0
    for status in recent:
        if status == Status.ABSENT:
            run += 1
        else:
            break
    return run


def _trend(student_id: int, term: Term, today: date) -> tuple[float | None, float | None]:
    """Attendance percentage over the recent window, and over everything before it."""
    records = list(
        AttendanceRecord.objects.filter(
            student_id=student_id, session__status=ClassSession.Status.CLOSED,
            session__date__range=(term.start_date, min(today, term.end_date)),
        )
        .exclude(status=Status.PENDING)
        .order_by('-session__date', '-session__starts_at')
        .values_list('status', flat=True)
    )
    if len(records) < RECENT_SESSIONS * 2:
        return None, None  # too little history to call a trend
    recent, earlier = records[:RECENT_SESSIONS], records[RECENT_SESSIONS:]
    rate = lambda rows: 100 * sum(1 for status in rows if status in ATTENDED) / len(rows)
    return rate(recent), rate(earlier)


def assess(term: Term, today: date, class_group_ids=None, teacher_user=None) -> list[RiskRow]:
    """Score every student in scope. Returns the highest scores first."""
    minimum = term.minimum_attendance

    # Per-subject trouble comes from the forecast, so the two features always agree.
    per_subject = forecast(term, today, class_group_ids=class_group_ids, teacher_user=teacher_user)
    trouble: dict[int, dict[str, int]] = {}
    for row in per_subject:
        counts = trouble.setdefault(row.student, {'at_risk': 0, 'cannot_reach': 0})
        if row.status == AT_RISK:
            counts['at_risk'] += 1
        elif row.status == CANNOT_REACH:
            counts['cannot_reach'] += 1

    students = Student.objects.filter(is_active=True)
    if class_group_ids is not None:
        students = students.filter(class_groups__in=class_group_ids)
    if teacher_user is not None:
        taught = {row.class_group for row in per_subject}
        students = students.filter(class_groups__in=taught) if taught else students.none()
    students = students.distinct().prefetch_related('class_groups')

    totals = {
        row['student']: row
        for row in AttendanceRecord.objects.filter(
            student__in=students, session__status=ClassSession.Status.CLOSED,
            session__date__range=(term.start_date, min(today, term.end_date)),
        ).values('student').annotate(
            attended=Count('id', filter=Q(status__in=ATTENDED)),
            held=Count('id', filter=~Q(status=Status.PENDING)),
        )
    }

    rows: list[RiskRow] = []
    for student in students:
        counts = totals.get(student.id, {'attended': 0, 'held': 0})
        attended, held = counts['attended'], counts['held']
        percent = round(100 * attended / held, 1) if held else None
        signals: list[Signal] = []
        score = 0

        if percent is not None and percent < minimum:
            signals.append(Signal('below_minimum', f'Attendance {percent}% is under the {minimum}% minimum.', BELOW_MINIMUM_POINTS))
            score += BELOW_MINIMUM_POINTS
            if percent < minimum - WELL_BELOW_GAP:
                signals.append(Signal('well_below_minimum', f'More than {WELL_BELOW_GAP} points under the minimum.', WELL_BELOW_MINIMUM_POINTS))
                score += WELL_BELOW_MINIMUM_POINTS

        recent_rate, earlier_rate = _trend(student.id, term, today)
        if recent_rate is not None and earlier_rate is not None and earlier_rate - recent_rate >= FALLING_DROP:
            signals.append(Signal(
                'falling', f'Recent attendance {round(recent_rate)}% against {round(earlier_rate)}% before that.', FALLING_POINTS,
            ))
            score += FALLING_POINTS

        run = consecutive_absences(student.id, term, today)
        if run >= CONSECUTIVE_ABSENCES:
            signals.append(Signal('consecutive_absences', f'Absent from the last {run} classes in a row.', CONSECUTIVE_POINTS))
            score += CONSECUTIVE_POINTS

        subject_counts = trouble.get(student.id, {'at_risk': 0, 'cannot_reach': 0})
        if subject_counts['at_risk'] >= 2:
            signals.append(Signal('several_subjects', f"{subject_counts['at_risk']} subjects at risk.", SUBJECTS_AT_RISK_POINTS))
            score += SUBJECTS_AT_RISK_POINTS
        if subject_counts['cannot_reach']:
            signals.append(Signal(
                'cannot_reach', f"Can no longer reach the minimum in {subject_counts['cannot_reach']} subject(s).", CANNOT_REACH_POINTS,
            ))
            score += CANNOT_REACH_POINTS

        score = min(score, 100)
        if not signals:
            continue  # nothing to report about this student
        group = student.class_groups.first()
        rows.append(RiskRow(
            student=student.id, roll_number=student.roll_number, full_name=student.full_name,
            class_group=group.id if group else None, percent=percent, attended=attended, held=held,
            consecutive_absences=run, subjects_at_risk=subject_counts['at_risk'] + subject_counts['cannot_reach'],
            score=score, band=band_for(score), signals=[asdict(signal) for signal in signals],
            guardian_contact=student.guardian_contact,
        ))
    rows.sort(key=lambda row: (-row.score, row.roll_number))
    return rows


def as_dicts(rows: list[RiskRow]) -> list[dict]:
    return [asdict(row) for row in rows]
