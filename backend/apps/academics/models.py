from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

WEEKDAYS = [
    (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
    (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
]


class Teacher(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teacher')
    employee_code = models.CharField(max_length=30, unique=True)
    department = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class ClassGroup(models.Model):
    """A cohort of students that attends sessions together, e.g. 'CSE-A'."""
    name = models.CharField(max_length=100)
    academic_year = models.CharField(max_length=20, help_text="e.g. 2026-27")

    class Meta:
        ordering = ['academic_year', 'name']
        constraints = [
            models.UniqueConstraint(fields=['name', 'academic_year'], name='uniq_classgroup_name_year'),
        ]

    def __str__(self):
        return f"{self.name} ({self.academic_year})"


class Subject(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Student(models.Model):
    roll_number = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    # Face enrolment is only permitted once consent is recorded.
    consent_given = models.BooleanField(default=False)
    consent_recorded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class_groups = models.ManyToManyField(ClassGroup, through='Enrollment', related_name='students')

    class Meta:
        ordering = ['roll_number']

    def __str__(self):
        return f"{self.roll_number} - {self.full_name}"


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_on = models.DateField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'class_group'], name='uniq_enrollment_student_class'),
        ]

    def __str__(self):
        return f"{self.student} in {self.class_group}"


class Period(models.Model):
    """
    Bell-schedule slot. Scope is, from least to most specific:
    default (no weekday, no date), one weekday, or one calendar date.
    """
    number = models.PositiveSmallIntegerField(help_text="Position of the period in the day (1, 2, 3...)")
    name = models.CharField(max_length=50, blank=True)
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS, null=True, blank=True)
    specific_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['specific_date', 'weekday', 'number']
        constraints = [
            models.CheckConstraint(check=Q(end_time__gt=F('start_time')), name='period_end_after_start'),
            models.CheckConstraint(
                check=Q(weekday__isnull=True) | Q(specific_date__isnull=True),
                name='period_single_scope',
            ),
            models.UniqueConstraint(
                fields=['number'], condition=Q(weekday__isnull=True, specific_date__isnull=True),
                name='uniq_period_default_number',
            ),
            models.UniqueConstraint(
                fields=['number', 'weekday'], condition=Q(weekday__isnull=False),
                name='uniq_period_weekday_number',
            ),
            models.UniqueConstraint(
                fields=['number', 'specific_date'], condition=Q(specific_date__isnull=False),
                name='uniq_period_date_number',
            ),
        ]

    def __str__(self):
        if self.specific_date:
            scope = str(self.specific_date)
        elif self.weekday is not None:
            scope = self.get_weekday_display()
        else:
            scope = 'Default'
        return f"{scope} P{self.number} {self.start_time:%H:%M}-{self.end_time:%H:%M}"

    def same_scope(self):
        """Other periods sharing this period's scope."""
        return Period.objects.filter(weekday=self.weekday, specific_date=self.specific_date).exclude(pk=self.pk)

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})
        if self.weekday is not None and self.specific_date is not None:
            raise ValidationError('Set either a weekday or a specific date, not both.')
        if self.start_time and self.end_time:
            clash = self.same_scope().filter(start_time__lt=self.end_time, end_time__gt=self.start_time).first()
            if clash:
                raise ValidationError(f'Overlaps with {clash}.')


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.date} - {self.name}"


class TimetableEntry(models.Model):
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name='timetable_entries')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='timetable_entries')
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_entries')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_entries')
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    period_number = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['weekday', 'period_number']
        constraints = [
            models.UniqueConstraint(fields=['class_group', 'weekday', 'period_number'], name='uniq_timetable_class_slot'),
            models.UniqueConstraint(
                fields=['room', 'weekday', 'period_number'], condition=Q(room__isnull=False),
                name='uniq_timetable_room_slot',
            ),
            models.UniqueConstraint(
                fields=['teacher', 'weekday', 'period_number'], condition=Q(teacher__isnull=False),
                name='uniq_timetable_teacher_slot',
            ),
        ]

    def __str__(self):
        return f"{self.class_group} {self.get_weekday_display()} P{self.period_number}: {self.subject.code}"


class ClassSession(models.Model):
    """One taught period for one class group; the unit attendance is recorded against."""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Source(models.TextChoices):
        TIMETABLE = 'timetable', 'Timetable'
        MANUAL = 'manual', 'Manual'

    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name='sessions')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='sessions')
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    date = models.DateField()
    period_number = models.PositiveSmallIntegerField(null=True, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True, help_text="Empty while a manual session is still open")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)

    class Meta:
        ordering = ['-date', 'starts_at']
        constraints = [
            models.UniqueConstraint(
                fields=['class_group', 'date', 'period_number'], condition=Q(period_number__isnull=False),
                name='uniq_session_class_date_period',
            ),
        ]
        indexes = [
            models.Index(fields=['class_group', 'date']),
            models.Index(fields=['room', 'starts_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        slot = f"P{self.period_number}" if self.period_number else f"{self.starts_at:%H:%M}"
        return f"{self.class_group} {self.subject.code} {self.date} {slot}"


class Term(models.Model):
    """A teaching term. The attendance forecast counts the classes left until its end."""
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    minimum_attendance = models.PositiveSmallIntegerField(
        default=75, help_text="Percentage a student must keep in each subject",
    )

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError({'end_date': 'The term must end after it starts.'})
        if not 1 <= (self.minimum_attendance or 0) <= 100:
            raise ValidationError({'minimum_attendance': 'Use a percentage from 1 to 100.'})
        if self.start_date and self.end_date:
            overlap = Term.objects.exclude(pk=self.pk).filter(start_date__lte=self.end_date, end_date__gte=self.start_date)
            if overlap.exists():
                raise ValidationError(f'Overlaps with {overlap.first()}.')

    @classmethod
    def current(cls, day=None):
        from django.utils import timezone

        day = day or timezone.localdate()
        return cls.objects.filter(start_date__lte=day, end_date__gte=day).first()
