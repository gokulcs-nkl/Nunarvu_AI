from apps.academics.models import ClassSession, Student

from .models import AttendanceRecord


def finalize_session(session: ClassSession) -> int:
    """Mark every enrolled, active student without a record as absent. Returns rows created."""
    recorded = AttendanceRecord.objects.filter(session=session).values_list('student_id', flat=True)
    missing = Student.objects.filter(
        class_groups=session.class_group, is_active=True,
    ).exclude(id__in=recorded)
    created = AttendanceRecord.objects.bulk_create([
        AttendanceRecord(
            session=session, student=student,
            status=AttendanceRecord.Status.ABSENT, source=AttendanceRecord.Source.AUTO,
        )
        for student in missing
    ])
    return len(created)
