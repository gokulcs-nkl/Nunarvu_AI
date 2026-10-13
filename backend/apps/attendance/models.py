from django.conf import settings
from django.db import models

from apps.academics.models import ClassSession, Student


class AttendanceRecord(models.Model):
    """A student's attendance for one class session. Exactly one row per session and student."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        PRESENT = 'present', 'Present'
        LATE = 'late', 'Late'
        LEFT_EARLY = 'left_early', 'Left early'
        ABSENT = 'absent', 'Absent'

    class Source(models.TextChoices):
        AUTO = 'auto', 'Automatic'
        MANUAL = 'manual', 'Manual'

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=20, choices=Status.choices)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    first_seen_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True, help_text="Best recognition score (0-1); empty for manual entries")
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    note = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['session', 'student__roll_number']
        constraints = [
            models.UniqueConstraint(fields=['session', 'student'], name='uniq_attendance_session_student'),
        ]
        indexes = [
            models.Index(fields=['student', 'status']),
        ]

    def __str__(self):
        return f"{self.student} - {self.session}: {self.status}"
