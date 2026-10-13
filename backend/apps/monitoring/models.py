from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.academics.models import Room


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
