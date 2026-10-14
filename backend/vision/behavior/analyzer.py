"""
Turn per-frame posture measurements into classroom events.

An event starts only after its condition has held for a configured time, and ends after the
condition has been absent for a short grace period. This filters out single-frame noise and
means one continuous occurrence is one event, not one per frame.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import rules

HAND_RAISE = 'hand_raise'
HEAD_DOWN = 'head_down'
PHONE = 'phone'
UNUSUAL_ACTIVITY = 'unusual_activity'
KINDS = (HAND_RAISE, HEAD_DOWN, PHONE, UNUSUAL_ACTIVITY)

ROOM = 'room'             # subject key for events about the room rather than one person
GRACE_SECONDS = 1.5       # how long a condition may lapse before the event is considered over
COOLDOWN_SECONDS = 20.0   # minimum gap before the same subject can start the same kind again
# Keypoint speed, in shoulder-widths per second, treated as fast movement.
FAST_MOVEMENT_SPEED = 2.5
# Two people closer than this many shoulder-widths are "close together".
CLOSE_DISTANCE = 3.0


@dataclass(frozen=True)
class Person:
    track_id: int
    box: tuple[int, int, int, int]
    keypoints: np.ndarray    # 17x2 pixel coordinates
    confidence: np.ndarray   # 17 keypoint confidences
    student_id: int | None = None


@dataclass(frozen=True)
class Thresholds:
    hand_raise_seconds: float = 1.0
    head_down_seconds: float = 60.0
    phone_seconds: float = 5.0
    unusual_activity_seconds: float = 3.0
    enabled: frozenset = frozenset(KINDS)

    def seconds_for(self, kind: str) -> float:
        return getattr(self, f'{kind}_seconds')


@dataclass(frozen=True)
class EventUpdate:
    action: str               # 'start' or 'end'
    kind: str
    subject: str              # person track id as text, or ROOM
    student_id: int | None
    at: float
    confidence: float = 0.0
    signals: tuple = ()       # measurements that triggered the event, as dicts
    position: tuple[float, float] | None = None  # person's centre as a fraction of the frame


@dataclass
class _Condition:
    since: float | None = None      # when the condition became continuously true
    last_true: float = 0.0
    open: bool = False              # an event has been started and not yet ended
    ended_at: float = float('-inf')
    confidences: list = field(default_factory=list)
    signals: tuple = ()
    student_id: int | None = None
    position: tuple[float, float] | None = None


def _box_contains(box, point) -> bool:
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


class BehaviorAnalyzer:
    def __init__(self, thresholds: Thresholds | None = None):
        self.thresholds = thresholds or Thresholds()
        self._conditions: dict[tuple[str, str], _Condition] = {}
        self._previous: dict[int, tuple[np.ndarray, float]] = {}

    def _observe(self, subject: str, kind: str, met: bool, now: float, confidence: float, signals: tuple,
                 student_id: int | None, updates: list[EventUpdate], position: tuple[float, float] | None = None) -> None:
        if kind not in self.thresholds.enabled:
            return
        state = self._conditions.setdefault((subject, kind), _Condition())
        if student_id is not None:
            state.student_id = student_id
        if met:
            if state.since is None:
                state.since = now
                state.confidences = []
            state.last_true = now
            state.confidences.append(confidence)
            state.signals = signals
            if position is not None:
                state.position = position
            held = now - state.since
            if not state.open and held >= self.thresholds.seconds_for(kind) and now - state.ended_at >= COOLDOWN_SECONDS:
                state.open = True
                updates.append(EventUpdate(
                    'start', kind, subject, state.student_id, state.since,
                    float(np.mean(state.confidences)), signals + ({'signal': 'held_seconds', 'value': round(held, 1), 'threshold': self.thresholds.seconds_for(kind)},),
                    state.position,
                ))
        elif state.since is not None and now - state.last_true > GRACE_SECONDS:
            self._finish(subject, kind, state, updates)

    def _finish(self, subject: str, kind: str, state: _Condition, updates: list[EventUpdate]) -> None:
        if state.open:
            updates.append(EventUpdate('end', kind, subject, state.student_id, state.last_true))
            state.ended_at = state.last_true
        state.since, state.open = None, False

    def update(self, people: list[Person], phone_boxes: list[tuple], now: float, frame_size: tuple[int, int] | None = None) -> list[EventUpdate]:
        """
        Feed one sample. `phone_boxes` are (x1, y1, x2, y2, score) detections of phone-like objects.
        Returns the events that started or ended at this sample.
        """
        updates: list[EventUpdate] = []
        seen: set[str] = set()
        fast: list[Person] = []

        for person in people:
            subject = str(person.track_id)
            seen.add(subject)
            where = None
            if frame_size and frame_size[0] and frame_size[1]:
                where = (
                    round(min(max((person.box[0] + person.box[2]) / 2 / frame_size[0], 0.0), 1.0), 4),
                    round(min(max((person.box[1] + person.box[3]) / 2 / frame_size[1], 0.0), 1.0), 4),
                )

            raised = rules.hand_raise(person.keypoints, person.confidence)
            if raised is not None:
                self._observe(subject, HAND_RAISE, raised.met, now, raised.confidence, (raised.as_dict(),), person.student_id, updates, where)

            lowered = rules.head_down(person.keypoints, person.confidence)
            if lowered is not None:
                self._observe(subject, HEAD_DOWN, lowered.met, now, lowered.confidence, (lowered.as_dict(),), person.student_id, updates, where)

            near = [box for box in phone_boxes if _box_contains(person.box, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2))]
            score = max((box[4] for box in near), default=0.0)
            self._observe(
                subject, PHONE, bool(near), now, score,
                ({'signal': 'phone_like_object_score', 'value': round(score, 2), 'threshold': 0.0},), person.student_id, updates, where,
            )

            previous = self._previous.get(person.track_id)
            if previous is not None:
                speed = rules.movement_speed(previous[0], person.keypoints, person.confidence, now - previous[1])
                if speed is not None and speed >= FAST_MOVEMENT_SPEED:
                    fast.append(person)
            self._previous[person.track_id] = (person.keypoints, now)

        # Room level: at least two fast-moving people close to each other.
        involved = 0
        for index, first in enumerate(fast):
            for second in fast[index + 1:]:
                scale = rules.shoulder_width(first.keypoints, first.confidence) or 1.0
                centres = [((p.box[0] + p.box[2]) / 2, (p.box[1] + p.box[3]) / 2) for p in (first, second)]
                distance = float(np.hypot(centres[0][0] - centres[1][0], centres[0][1] - centres[1][1])) / scale
                if distance <= CLOSE_DISTANCE:
                    involved = max(involved, 2)
        self._observe(
            ROOM, UNUSUAL_ACTIVITY, involved >= 2, now, 0.5,
            ({'signal': 'fast_moving_people_close_together', 'value': involved, 'threshold': 2},), None, updates,
        )

        # People who left the view: close their events and forget them after the grace period.
        for (subject, kind), state in list(self._conditions.items()):
            if subject == ROOM or subject in seen:
                continue
            if now - state.last_true > GRACE_SECONDS:
                if state.since is not None:
                    self._finish(subject, kind, state, updates)
                if now - state.ended_at > COOLDOWN_SECONDS and now - state.last_true > COOLDOWN_SECONDS:
                    del self._conditions[(subject, kind)]
        self._previous = {track: value for track, value in self._previous.items() if str(track) in seen}
        return updates

    def close_all(self, now: float) -> list[EventUpdate]:
        """End every open event, for example when the session changes."""
        updates: list[EventUpdate] = []
        for (subject, kind), state in self._conditions.items():
            self._finish(subject, kind, state, updates)
        self._conditions.clear()
        self._previous.clear()
        return updates
