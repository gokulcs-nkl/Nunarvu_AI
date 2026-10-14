"""Store classroom events produced by the behaviour analyser, worded as observations."""
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from vision.behavior import analyzer
from vision.behavior.analyzer import EventUpdate, Thresholds

from .models import ClassroomEvent, ObservationSettings


def thresholds_from_settings() -> Thresholds:
    config = ObservationSettings.load()
    enabled = {kind for kind in analyzer.KINDS if getattr(config, f'{kind}_enabled')}
    return Thresholds(
        hand_raise_seconds=config.hand_raise_seconds,
        head_down_seconds=config.head_down_seconds,
        phone_seconds=config.phone_seconds,
        unusual_activity_seconds=config.unusual_activity_seconds,
        enabled=frozenset(enabled),
    )


def describe(update: EventUpdate, thresholds: Thresholds) -> str:
    """What was observed, in words that do not claim to know why."""
    seconds = round(thresholds.seconds_for(update.kind))
    if update.kind == analyzer.HAND_RAISE:
        return 'Hand raised above shoulder height.'
    if update.kind == analyzer.HEAD_DOWN:
        return f'Head at or below shoulder level for over {seconds} s. Possible sleeping-like posture; teacher verification required.'
    if update.kind == analyzer.PHONE:
        return f'Phone-like object visible near this person for over {seconds} s.'
    return f'Fast movement by two or more people close together for over {seconds} s. Teacher verification required.'


def _aware(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)


def record_updates(session, camera, updates: list[EventUpdate], thresholds: Thresholds) -> list[ClassroomEvent]:
    """Create an event for each start and close the matching open event for each end. Returns new events."""
    created: list[ClassroomEvent] = []
    for update in updates:
        if update.action == 'start':
            created.append(ClassroomEvent.objects.create(
                session=session, camera=camera, kind=update.kind, subject=update.subject,
                student_id=update.student_id, started_at=_aware(update.at), confidence=update.confidence,
                summary=describe(update, thresholds), signals=list(update.signals),
                position_x=update.position[0] if update.position else None,
                position_y=update.position[1] if update.position else None,
            ))
        else:
            ClassroomEvent.objects.filter(
                session=session, camera=camera, kind=update.kind, subject=update.subject, ended_at__isnull=True,
            ).update(ended_at=_aware(update.at))
    return created
