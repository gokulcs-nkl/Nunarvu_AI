"""
Tell a guardian, early, that their child's attendance is slipping.

A notice goes only to a student whose guardian contact is on record, and the same warning is
not repeated within a cooling-off period. The wording states the figures and asks the guardian
to get in touch; it never accuses the student or predicts an outcome. Under the DPDP Act a
minor's guardian is the right person to inform, which is why the guardian contact is used.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings as django_settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.academics.models import PrivacySettings, Term

from .models import GuardianNotice
from .risk import HIGH, assess

logger = logging.getLogger(__name__)

# The same kind of notice is not sent to the same student again within this time.
COOLING_OFF = timedelta(days=14)


def is_email(contact: str) -> bool:
    return '@' in contact and '.' in contact.split('@')[-1]


def compose(row, term: Term) -> tuple[str, str]:
    reasons = '\n'.join(f'  - {signal["detail"]}' for signal in row.signals)
    subject = f'Attendance notice for {row.full_name} ({row.roll_number})'
    body = (
        f'Dear guardian,\n\n'
        f'This is an automatic notice about {row.full_name}\'s attendance in {term.name}.\n\n'
        f'Attendance so far: {row.attended} of {row.held} classes'
        f'{f" ({row.percent}%)" if row.percent is not None else ""}.\n'
        f'The minimum required is {term.minimum_attendance}%.\n\n'
        f'What we noticed:\n{reasons}\n\n'
        'These figures come from classroom attendance records. If there is a reason for the '
        'absences, or if you think the record is wrong, please contact the class teacher so it '
        'can be corrected. Attendance can be amended by a teacher at any time.\n\n'
        'This message was sent automatically by the school attendance system.'
    )
    return subject, body


def pending_notices(term: Term, today=None, class_group_ids=None, teacher_user=None) -> list:
    """Students who would be told now: high risk, a guardian contact on record, none sent recently."""
    today = today or timezone.localdate()
    rows = assess(term, today, class_group_ids=class_group_ids, teacher_user=teacher_user)
    since = timezone.now() - COOLING_OFF
    told_recently = set(
        GuardianNotice.objects.filter(term=term, kind=GuardianNotice.Kind.HIGH_RISK, sent_at__gte=since)
        .values_list('student_id', flat=True)
    )
    return [
        row for row in rows
        if row.band == HIGH and row.guardian_contact and is_email(row.guardian_contact)
        and row.student not in told_recently
    ]


def send_notices(term: Term, today=None, class_group_ids=None, sent_by=None, dry_run=False) -> dict:
    """
    Send a notice to each guardian who should hear from us. Returns what was sent and skipped.
    A failure to send one notice is logged and does not stop the rest.
    """
    privacy = PrivacySettings.load()
    if not getattr(privacy, 'guardian_notices_enabled', True):
        return {'sent': 0, 'failed': 0, 'skipped': 0, 'disabled': True, 'recipients': []}

    rows = pending_notices(term, today=today, class_group_ids=class_group_ids)
    result = {'sent': 0, 'failed': 0, 'skipped': 0, 'disabled': False, 'recipients': []}
    for row in rows:
        subject, body = compose(row, term)
        if dry_run:
            result['skipped'] += 1
            result['recipients'].append({'student': row.roll_number, 'to': row.guardian_contact, 'subject': subject})
            continue
        try:
            send_mail(subject, body, django_settings.DEFAULT_FROM_EMAIL, [row.guardian_contact], fail_silently=False)
        except Exception as error:
            logger.warning('Could not send a guardian notice for %s: %s', row.roll_number, error)
            result['failed'] += 1
            continue
        GuardianNotice.objects.create(
            student_id=row.student, term=term, kind=GuardianNotice.Kind.HIGH_RISK,
            sent_to=row.guardian_contact, subject=subject, body=body,
            attendance_percent=row.percent, sent_by=sent_by,
        )
        result['sent'] += 1
        result['recipients'].append({'student': row.roll_number, 'to': row.guardian_contact, 'subject': subject})
    return result
