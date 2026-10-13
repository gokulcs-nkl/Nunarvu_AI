from django.conf import settings
from django.db import models


class Role(models.TextChoices):
    ADMIN = 'admin', 'Administrator'
    TEACHER = 'teacher', 'Teacher'
    VIEWER = 'viewer', 'Viewer'


class Profile(models.Model):
    """Role assignment for a Django user. Superusers are always treated as administrators."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


def get_role(user) -> str:
    """Return the effective role of an authenticated user."""
    if user.is_superuser:
        return Role.ADMIN
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile.role


class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preference')
    camera_offline = models.BooleanField(default=True)
    processing_failure = models.BooleanField(default=True)
    attendance_anomaly = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification preferences for {self.user.username}"


class AuditLog(models.Model):
    """Append-only record of sensitive operations."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_entries')
    action = models.CharField(max_length=50)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=64, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.action} {self.target_type}#{self.target_id}"
