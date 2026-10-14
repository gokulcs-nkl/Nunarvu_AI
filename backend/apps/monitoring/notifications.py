"""Email people when a camera stops working, and when it comes back."""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from apps.accounts.models import NotificationPreference, Role, get_role

from .models import Camera, CameraStatusLog

logger = logging.getLogger(__name__)

# A camera that keeps failing and recovering sends at most one problem email in this time.
REPEAT_AFTER = timedelta(minutes=10)


def recipients() -> list[str]:
    """Email addresses of active administrators and teachers who have not switched camera alerts off."""
    opted_out = set(NotificationPreference.objects.filter(camera_offline=False).values_list('user_id', flat=True))
    users = get_user_model().objects.filter(is_active=True).exclude(email='').exclude(id__in=opted_out)
    return sorted({user.email for user in users if get_role(user) in (Role.ADMIN, Role.TEACHER)})


def camera_status_changed(camera: Camera, status: str, previous: str | None, detail: str = '') -> bool:
    """
    Called by the worker after it has logged a status change. Sends an email when a camera goes
    into error, and when it recovers from one. Returns True if an email was sent.
    A failure to send is logged and never raised: monitoring matters more than the message.
    """
    recent_errors = CameraStatusLog.objects.filter(
        camera=camera, status=Camera.Status.ERROR, at__gte=timezone.now() - REPEAT_AFTER,
    ).count()
    if recent_errors > 1:
        # The camera is failing and recovering repeatedly; one problem email covers the episode.
        return False
    if status == Camera.Status.ERROR:
        subject = f'Camera problem: {camera.name}'
        body = (
            f'The camera "{camera.name}" stopped working at {timezone.localtime():%H:%M on %d %b %Y}.\n\n'
            f'Reason: {detail or "not reported"}\n\n'
            'The camera worker keeps trying to reconnect. Attendance for the current session can be '
            'marked by hand in the meantime.'
        )
    elif status == Camera.Status.ONLINE and previous == Camera.Status.ERROR:
        subject = f'Camera working again: {camera.name}'
        body = f'The camera "{camera.name}" is working again as of {timezone.localtime():%H:%M on %d %b %Y}.'
    else:
        return False

    addresses = recipients()
    if not addresses:
        return False
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, addresses, fail_silently=False)
        return True
    except Exception as error:  # mail servers fail in many ways; none of them may stop the worker
        logger.warning('Could not send the camera notification: %s', error)
        return False
