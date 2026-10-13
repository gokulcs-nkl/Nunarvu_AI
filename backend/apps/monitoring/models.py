from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.academics.models import ClassSession, Room, Student


class Camera(models.Model):
    class SourceType(models.TextChoices):
        WEBCAM = 'webcam', 'Built-in or USB webcam'
        RTSP = 'rtsp', 'IP camera (RTSP)'
        HTTP = 'http', 'IP camera (HTTP stream)'
        FILE = 'file', 'Recorded video file'

    class Status(models.TextChoices):
        OFFLINE = 'offline', 'Offline'
        ONLINE = 'online', 'Online'
        ERROR = 'error', 'Camera error'

    name = models.CharField(max_length=100, unique=True)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.WEBCAM)
    source = models.CharField(max_length=500, help_text="Device index for a webcam, stream URL, or file path")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='cameras')
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Live state, written by the camera worker
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OFFLINE)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    fps = models.FloatField(null=True, blank=True, help_text="Frames analysed per second")
    latency_ms = models.FloatField(null=True, blank=True, help_text="Average time to analyse one frame")

    # A worker that has not reported for this long is treated as offline.
    HEARTBEAT_TIMEOUT = timedelta(seconds=20)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def live_status(self) -> str:
        """Stored status, downgraded to offline when the worker has gone quiet."""
        if self.last_heartbeat is None or timezone.now() - self.last_heartbeat > self.HEARTBEAT_TIMEOUT:
            return self.Status.OFFLINE
        return self.status


class CameraStatusLog(models.Model):
    """One row per status change, so uptime can be reported later."""
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='status_log')
    status = models.CharField(max_length=20, choices=Camera.Status.choices)
    detail = models.CharField(max_length=255, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-at']
        indexes = [models.Index(fields=['camera', '-at'])]

    def __str__(self):
        return f"{self.camera} {self.status} at {self.at:%Y-%m-%d %H:%M:%S}"


class ObservationSettings(models.Model):
    """Which classroom observations are switched on, and how long each must last. One row."""
    hand_raise_enabled = models.BooleanField(default=True)
    head_down_enabled = models.BooleanField(default=True)
    phone_enabled = models.BooleanField(default=True)
    unusual_activity_enabled = models.BooleanField(default=True)
    hand_raise_seconds = models.FloatField(default=1.0)
    head_down_seconds = models.FloatField(default=60.0)
    phone_seconds = models.FloatField(default=5.0)
    unusual_activity_seconds = models.FloatField(default=3.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'observation settings'

    def __str__(self):
        return 'Observation settings'

    @classmethod
    def load(cls) -> 'ObservationSettings':
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    @property
    def any_enabled(self) -> bool:
        return self.hand_raise_enabled or self.head_down_enabled or self.phone_enabled or self.unusual_activity_enabled


class ClassroomEvent(models.Model):
    """
    Something a camera observed during a session. It records what was seen and how it was
    measured; it is not a judgement, and stays unreviewed until a teacher looks at it.
    """

    class Kind(models.TextChoices):
        HAND_RAISE = 'hand_raise', 'Hand raised'
        HEAD_DOWN = 'head_down', 'Head-down posture'
        PHONE = 'phone', 'Phone-like object'
        UNUSUAL_ACTIVITY = 'unusual_activity', 'Unusual activity'

    class Review(models.TextChoices):
        UNREVIEWED = 'unreviewed', 'Not reviewed'
        CONFIRMED = 'confirmed', 'Confirmed by teacher'
        DISMISSED = 'dismissed', 'Dismissed by teacher'

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='events')
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    kind = models.CharField(max_length=30, choices=Kind.choices)
    subject = models.CharField(max_length=30, help_text="Person track within the camera view, or 'room'")
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    confidence = models.FloatField(help_text="Model confidence in the measurements, 0-1; not a probability that the event is true")
    summary = models.CharField(max_length=255)
    signals = models.JSONField(default=list, help_text="Measurements that triggered the event, with their thresholds")
    review_status = models.CharField(max_length=20, choices=Review.choices, default=Review.UNREVIEWED)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        constraints = [
            # The same occurrence cannot be stored twice.
            models.UniqueConstraint(fields=['session', 'camera', 'kind', 'subject', 'started_at'], name='uniq_event_occurrence'),
        ]
        indexes = [
            models.Index(fields=['session', '-started_at']),
            models.Index(fields=['review_status', 'kind']),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} in {self.session} at {self.started_at:%H:%M:%S}"
