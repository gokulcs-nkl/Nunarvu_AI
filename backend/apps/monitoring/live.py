"""Web-server side of live monitoring: the latest preview frame per camera and fan-out to browsers."""
from __future__ import annotations

import threading
import time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

FRAME_MAX_AGE = 5.0  # seconds before a preview frame is considered stale

# Preview frames live only in this process's memory. They are never written to disk.
_frames: dict[int, tuple[bytes, float]] = {}
_frames_lock = threading.Lock()


def session_group(session_id: int) -> str:
    return f'session.{session_id}'


def store_frame(camera_id: int, jpeg: bytes) -> None:
    with _frames_lock:
        _frames[camera_id] = (jpeg, time.time())


def latest_frame(camera_id: int, max_age: float = FRAME_MAX_AGE) -> bytes | None:
    with _frames_lock:
        entry = _frames.get(camera_id)
    if entry is None or time.time() - entry[1] > max_age:
        return None
    return entry[0]


def clear_frames() -> None:
    with _frames_lock:
        _frames.clear()


def broadcast(payload: dict) -> None:
    """Send one worker update to everyone watching the session that camera is serving."""
    if payload.get('session'):
        async_to_sync(get_channel_layer().group_send)(
            session_group(payload['session']), {'type': 'live.update', 'payload': payload},
        )
