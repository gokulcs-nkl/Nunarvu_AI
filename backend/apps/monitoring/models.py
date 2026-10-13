from django.db import models

from apps.academics.models import Room


class Camera(models.Model):
    class SourceType(models.TextChoices):
        WEBCAM = 'webcam', 'Built-in or USB webcam'
        RTSP = 'rtsp', 'IP camera (RTSP)'
        HTTP = 'http', 'IP camera (HTTP stream)'
        FILE = 'file', 'Recorded video file'

    name = models.CharField(max_length=100, unique=True)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.WEBCAM)
    source = models.CharField(max_length=500, help_text="Device index for a webcam, stream URL, or file path")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='cameras')
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
