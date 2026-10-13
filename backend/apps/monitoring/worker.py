"""
Camera worker: reads one camera, recognises faces for the session running in that
camera's room, records attendance, and reports live state to the web server.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone as dt_timezone

import cv2
import numpy as np
import requests
from django.conf import settings
from django.db import DatabaseError, close_old_connections
from django.utils import timezone

from apps.academics.models import ClassSession, Student
from apps.attendance.embeddings import gallery_for_class
from apps.attendance.services import Sighting, record_sightings
from vision.capture import FrameGrabber
from vision.face import matcher
from vision.face.tracker import FaceTracker

from .models import Camera, CameraStatusLog

logger = logging.getLogger(__name__)

SESSION_REFRESH_SECONDS = 2.0
GALLERY_REFRESH_SECONDS = 30.0
HEARTBEAT_SECONDS = 5.0
CONFIG_REFRESH_SECONDS = 10.0


class HttpPublisher:
    """Sends live state and preview frames to the web server. Failures never stop the worker."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {'X-Worker-Token': token}
        self.failures = 0

    def _post(self, path: str, headers: dict | None = None, **kwargs) -> None:
        try:
            requests.post(
                f'{self.base_url}{path}', headers={**self.headers, **(headers or {})}, timeout=2, **kwargs,
            ).raise_for_status()
            self.failures = 0
        except requests.RequestException as error:
            self.failures += 1
            if self.failures in (1, 50):  # say so once, then stay quiet while the web server is down
                logger.warning('Could not reach the web server for live updates: %s', error)

    def publish_state(self, payload: dict) -> None:
        self._post(f"/api/v1/internal/cameras/{payload['camera']}/state/", json=payload)

    def publish_frame(self, camera_id: int, jpeg: bytes) -> None:
        self._post(
            f'/api/v1/internal/cameras/{camera_id}/frame/', data=jpeg, headers={'Content-Type': 'image/jpeg'},
        )


class NullPublisher:
    def publish_state(self, payload: dict) -> None:
        pass

    def publish_frame(self, camera_id: int, jpeg: bytes) -> None:
        pass


def active_session_for(camera: Camera) -> ClassSession | None:
    """
    The active session this camera serves: the one in the camera's room. A camera with no
    room serves active sessions that have no room, which keeps a single-webcam setup simple.
    """
    return (
        ClassSession.objects.filter(status=ClassSession.Status.ACTIVE, room=camera.room)
        .select_related('class_group')
        .order_by('-starts_at')
        .first()
    )


class CameraWorker:
    def __init__(self, camera: Camera, engine, publisher=None, grabber=None):
        self.camera = camera
        self.engine = engine
        self.publisher = publisher or NullPublisher()
        self.grabber = grabber or FrameGrabber(camera.source_type, camera.source)
        self.tracker = FaceTracker()
        self.session: ClassSession | None = None
        self._session_checked = 0.0
        self._gallery: dict[int, np.ndarray] = {}
        self._names: dict[int, str] = {}
        self._gallery_key: tuple | None = None
        self._gallery_loaded = 0.0
        self._latency_ms = 0.0
        self._fps = 0.0
        self._last_step = 0.0
        self._status: str | None = None

    # ----- per-frame work -------------------------------------------------

    def _refresh_session(self, now: float) -> None:
        if now - self._session_checked < SESSION_REFRESH_SECONDS:
            return
        self._session_checked = now
        session = active_session_for(self.camera)
        if (session.id if session else None) != (self.session.id if self.session else None):
            # A different session means a different class: forget who the tracked faces were.
            for track in self.tracker.tracks.values():
                track.band, track.student_id, track.score, track.reason, track.recognized_at = 'unknown', None, 0.0, '', None
            self._gallery_key = None
        self.session = session

    def _refresh_gallery(self, now: float) -> None:
        key = (self.session.class_group_id, self.engine.model_name)
        if key == self._gallery_key and now - self._gallery_loaded < GALLERY_REFRESH_SECONDS:
            return
        self._gallery = gallery_for_class(self.session.class_group, self.engine.model_name)
        self._names = dict(Student.objects.filter(id__in=self._gallery.keys()).values_list('id', 'full_name'))
        self._gallery_key = key
        self._gallery_loaded = now

    def step(self, frame: np.ndarray, now: float) -> dict:
        """Analyse one frame and return the live-state payload for it."""
        started = time.perf_counter()
        found = self.engine.detect(frame)
        tracks = self.tracker.update([face.box for face in found], now)
        self._refresh_session(now)

        changed = []
        if self.session is not None:
            self._refresh_gallery(now)
            every = settings.WORKER_RECOGNIZE_EVERY_SECONDS
            due = [
                (track, face) for track, face in zip(tracks, found)
                if track.recognized_at is None or now - track.recognized_at >= every
            ]
            embedded = [(track, self.engine.embed(frame, face.landmarks)) for track, face in due]
            embedded = [(track, embedding) for track, embedding in embedded if embedding is not None]
            matches = matcher.match_faces(
                [embedding for _, embedding in embedded], self._gallery,
                settings.FACE_MATCH_CONFIRM, settings.FACE_MATCH_REVIEW, settings.FACE_MATCH_MARGIN,
            )
            due_ids = {track.id for track, _ in embedded}
            held = {
                track.student_id for track in self.tracker.tracks.values()
                if track.band == matcher.CONFIRMED and track.id not in due_ids
            }
            sightings = []
            for (track, _), match in zip(embedded, matches):
                band, reason = match.band, match.reason
                if band == matcher.CONFIRMED and match.student_id in held:
                    band, reason = matcher.REVIEW, 'Another face in view is already identified as this student.'
                track.band, track.student_id, track.score, track.reason = band, match.student_id, match.score, reason
                track.recognized_at = now
                if match.student_id is not None:
                    sightings.append(Sighting(match.student_id, band, match.score, reason))
            if sightings:
                at = datetime.fromtimestamp(now, tz=dt_timezone.utc)
                changed = record_sightings(self.session, sightings, at=at)

        elapsed_ms = (time.perf_counter() - started) * 1000
        self._latency_ms = elapsed_ms if not self._latency_ms else 0.8 * self._latency_ms + 0.2 * elapsed_ms
        if self._last_step:
            instant = 1.0 / max(now - self._last_step, 1e-6)
            self._fps = instant if not self._fps else 0.8 * self._fps + 0.2 * instant
        self._last_step = now

        height, width = frame.shape[:2]
        return {
            'camera': self.camera.id,
            'camera_name': self.camera.name,
            'status': Camera.Status.ONLINE,
            'error': '',
            'session': self.session.id if self.session else None,
            'timestamp': now,
            'frame_size': [width, height],
            'fps': round(self._fps, 1),
            'latency_ms': round(self._latency_ms, 1),
            'faces': [
                {
                    'track': track.id,
                    'box': list(track.box),
                    'band': track.band,
                    'student': track.student_id,
                    'student_name': self._names.get(track.student_id) if track.student_id else None,
                    'score': round(track.score, 3),
                    'reason': track.reason,
                }
                for track in tracks
            ],
            'changed': [
                {'student': record.student_id, 'status': record.status, 'student_name': self._names.get(record.student_id)}
                for record in changed
            ],
        }

    # ----- status ---------------------------------------------------------

    def _set_status(self, status: str, error: str = '') -> None:
        """Write the heartbeat, and log the change when the status is different from last time."""
        fields = {
            'status': status, 'last_error': error[:255], 'last_heartbeat': timezone.now(),
            'fps': round(self._fps, 1) if status == Camera.Status.ONLINE else None,
            'latency_ms': round(self._latency_ms, 1) if status == Camera.Status.ONLINE else None,
        }
        Camera.objects.filter(pk=self.camera.pk).update(**fields)
        if status != self._status:
            CameraStatusLog.objects.create(camera=self.camera, status=status, detail=error[:255])
            logger.info('Camera %s is %s %s', self.camera.name, status, error)
            self._status = status

    def _error_payload(self, error: str, now: float) -> dict:
        return {
            'camera': self.camera.id, 'camera_name': self.camera.name, 'status': Camera.Status.ERROR, 'error': error,
            'session': self.session.id if self.session else None, 'timestamp': now, 'frame_size': [0, 0],
            'fps': 0, 'latency_ms': 0, 'faces': [], 'changed': [],
        }

    def _config_changed(self) -> bool:
        fresh = Camera.objects.filter(pk=self.camera.pk).values('is_enabled', 'source', 'source_type', 'room_id').first()
        if fresh is None or not fresh['is_enabled']:
            return True
        if (fresh['source'], fresh['source_type']) != (self.camera.source, self.camera.source_type):
            return True
        self.camera.room_id = fresh['room_id']
        return False

    # ----- main loop ------------------------------------------------------

    def run(self, stop: threading.Event) -> None:
        interval = 1.0 / settings.WORKER_ANALYSIS_FPS
        preview_interval = 1.0 / settings.WORKER_PREVIEW_FPS
        last_frame_time = last_preview = last_config = 0.0
        last_heartbeat = time.time()  # give the camera a few seconds to open before reporting an error
        self.grabber.start()
        try:
            while not stop.is_set():
                tick = time.time()
                try:
                    if tick - last_config >= CONFIG_REFRESH_SECONDS:
                        last_config = tick
                        close_old_connections()
                        if self._config_changed():
                            logger.info('Camera %s was disabled or changed; stopping its worker.', self.camera.name)
                            return

                    frame, frame_time = self.grabber.latest()
                    if frame is None or frame_time == last_frame_time:
                        if not self.grabber.connected and tick - last_heartbeat >= HEARTBEAT_SECONDS:
                            last_heartbeat = tick
                            error = self.grabber.last_error or 'Waiting for the camera.'
                            self._set_status(Camera.Status.ERROR, error)
                            self._refresh_session(tick)
                            self.publisher.publish_state(self._error_payload(error, tick))
                        stop.wait(0.05)
                        continue
                    last_frame_time = frame_time

                    payload = self.step(frame, tick)
                    self.publisher.publish_state(payload)
                    if tick - last_preview >= preview_interval:
                        last_preview = tick
                        self.publisher.publish_frame(self.camera.id, encode_preview(frame))
                    if tick - last_heartbeat >= HEARTBEAT_SECONDS:
                        last_heartbeat = tick
                        self._set_status(Camera.Status.ONLINE)
                except DatabaseError as error:
                    # e.g. the database is briefly locked by the web server; skip this frame.
                    logger.warning('Database error in worker for %s: %s', self.camera.name, error)
                    close_old_connections()
                except Exception:
                    # One bad frame must not end monitoring for the rest of the session.
                    logger.exception('Unexpected error in worker for %s; continuing.', self.camera.name)
                    stop.wait(1.0)
                stop.wait(max(0.0, interval - (time.time() - tick)))
        finally:
            self.grabber.stop()
            try:
                self._fps = self._latency_ms = 0.0
                Camera.objects.filter(pk=self.camera.pk).update(status=Camera.Status.OFFLINE, fps=None, latency_ms=None)
                if self._status != Camera.Status.OFFLINE:
                    CameraStatusLog.objects.create(camera=self.camera, status=Camera.Status.OFFLINE, detail='Worker stopped')
            except DatabaseError:
                pass


def encode_preview(frame: np.ndarray) -> bytes:
    """JPEG of the frame for the live view. The frame keeps its aspect ratio, so box coordinates still map."""
    height, width = frame.shape[:2]
    target = settings.WORKER_PREVIEW_WIDTH
    if width > target:
        frame = cv2.resize(frame, (target, round(height * target / width)))
    ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return encoded.tobytes() if ok else b''
