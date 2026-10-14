"""
Privacy and compliance actions, built around India's Digital Personal Data Protection Act, 2023.

The Act requires consent to be specific and withdrawable, bars keeping data longer than needed,
and gives a person the right to see and erase their data. These functions carry that out for a
student. Face data is the sensitive part, so withdrawing consent deletes it at once; attendance
records are kept unless the student is fully erased, because they are the school's own register.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceRecord, FaceEnrollment, PresenceWindow
from apps.monitoring.models import ClassroomEvent

from .models import ConsentRecord, PrivacySettings, Student


def is_minor(student: Student, on=None) -> bool | None:
    """True if under 18 on the given date. None when the date of birth is unknown."""
    if not student.date_of_birth:
        return None
    on = on or timezone.localdate()
    years = on.year - student.date_of_birth.year - ((on.month, on.day) < (student.date_of_birth.month, student.date_of_birth.day))
    return years < 18


@transaction.atomic
def grant_consent(student: Student, given_by: str = '', recorded_by=None, purpose='', note='') -> ConsentRecord:
    purpose = purpose or ConsentRecord._meta.get_field('purpose').default
    student.consent_given = True
    student.consent_recorded_at = timezone.now()
    student.consent_withdrawn_at = None
    student.save(update_fields=['consent_given', 'consent_recorded_at', 'consent_withdrawn_at'])
    return ConsentRecord.objects.create(
        student=student, action=ConsentRecord.Action.GRANTED, purpose=purpose,
        given_by=given_by, recorded_by=recorded_by, note=note,
    )


@transaction.atomic
def withdraw_consent(student: Student, given_by: str = '', recorded_by=None, note='') -> dict:
    """Record the withdrawal and delete the student's face data, which may no longer be held."""
    faces_removed = FaceEnrollment.objects.filter(student=student).count()
    FaceEnrollment.objects.filter(student=student).delete()
    student.consent_given = False
    student.consent_withdrawn_at = timezone.now()
    student.save(update_fields=['consent_given', 'consent_withdrawn_at'])
    ConsentRecord.objects.create(
        student=student, action=ConsentRecord.Action.WITHDRAWN, given_by=given_by, recorded_by=recorded_by, note=note,
    )
    return {'face_enrollments_deleted': faces_removed}


def export_student_data(student: Student) -> dict:
    """Everything the system holds about a student, for the right of access. Face data is described, not dumped."""
    return {
        'exported_at': timezone.now().isoformat(),
        'student': {
            'roll_number': student.roll_number, 'full_name': student.full_name, 'email': student.email,
            'phone_number': student.phone_number, 'date_of_birth': student.date_of_birth,
            'guardian_name': student.guardian_name, 'guardian_contact': student.guardian_contact,
            'is_active': student.is_active, 'created_at': student.created_at.isoformat(),
        },
        'consent': {
            'given': student.consent_given,
            'recorded_at': student.consent_recorded_at.isoformat() if student.consent_recorded_at else None,
            'withdrawn_at': student.consent_withdrawn_at.isoformat() if student.consent_withdrawn_at else None,
            'history': [
                {'action': record.action, 'purpose': record.purpose, 'given_by': record.given_by,
                 'note': record.note, 'at': record.at.isoformat()}
                for record in student.consent_records.all()
            ],
        },
        'face_data': {
            'enrollments_held': student.face_enrollments.count(),
            'note': 'Face data is stored as encrypted numeric features, not as photographs, and is not included here.',
            'models': sorted({enrollment.model_name for enrollment in student.face_enrollments.all()}),
        },
        'classes': [str(group) for group in student.class_groups.all()],
        'attendance': [
            {'date': record.session.date.isoformat(), 'subject': record.session.subject.code,
             'status': record.status, 'source': record.source}
            for record in AttendanceRecord.objects.filter(student=student).select_related('session', 'session__subject')
        ],
        'observations': [
            {'date': event.started_at.isoformat(), 'kind': event.kind, 'summary': event.summary,
             'review_status': event.review_status}
            for event in ClassroomEvent.objects.filter(student=student)
        ],
    }


@transaction.atomic
def erase_student(student: Student) -> dict:
    """
    Remove a student and everything personal to them. Attendance rows are deleted with the student;
    this is the full erasure right, stronger than withdrawing consent. Returns what was removed.
    """
    counts = {
        'face_enrollments': FaceEnrollment.objects.filter(student=student).count(),
        'attendance_records': AttendanceRecord.objects.filter(student=student).count(),
        'presence_windows': PresenceWindow.objects.filter(student=student).count(),
        'observations_unlinked': ClassroomEvent.objects.filter(student=student).count(),
        'roll_number': student.roll_number,
    }
    # Observations are the room's record, not the student's; keep them but remove the link.
    ClassroomEvent.objects.filter(student=student).update(student=None)
    student.delete()  # cascades to face enrolments, attendance and presence windows
    return counts


def apply_retention(now=None, settings=None) -> dict:
    """Delete data older than the retention periods. Safe to run as often as you like."""
    now = now or timezone.now()
    settings = settings or PrivacySettings.load()
    removed = {'face_enrollments': 0, 'attendance_records': 0, 'observations': 0}

    if settings.face_retention_days:
        cutoff = now - timedelta(days=settings.face_retention_days)
        removed['face_enrollments'] = FaceEnrollment.objects.filter(created_at__lt=cutoff).delete()[0]
    if settings.attendance_retention_days:
        cutoff = (now - timedelta(days=settings.attendance_retention_days)).date()
        removed['attendance_records'] = AttendanceRecord.objects.filter(session__date__lt=cutoff).delete()[0]
    if settings.event_retention_days:
        cutoff = now - timedelta(days=settings.event_retention_days)
        removed['observations'] = ClassroomEvent.objects.filter(started_at__lt=cutoff).delete()[0]
    return removed


def compliance_summary() -> dict:
    """A snapshot for the privacy dashboard: consent coverage and anything that needs attention."""
    active = Student.objects.filter(is_active=True)
    minors_no_guardian = [
        student.roll_number for student in active.filter(consent_given=True)
        if is_minor(student) and not student.guardian_contact
    ]
    # A face enrolment held for someone whose consent is not currently on record.
    without_consent = Student.objects.filter(is_active=True, consent_given=False, face_enrollments__isnull=False).distinct()
    settings = PrivacySettings.load()
    return {
        'active_students': active.count(),
        'with_consent': active.filter(consent_given=True).count(),
        'consent_withdrawn': active.filter(consent_given=False, consent_withdrawn_at__isnull=False).count(),
        'minors': sum(1 for student in active if is_minor(student)),
        'minors_missing_guardian_contact': minors_no_guardian,
        'face_data_without_consent': [student.roll_number for student in without_consent],
        'retention': {
            'face_days': settings.face_retention_days,
            'attendance_days': settings.attendance_retention_days,
            'observation_days': settings.event_retention_days,
            'blur_unconsented': settings.blur_unconsented,
        },
    }
