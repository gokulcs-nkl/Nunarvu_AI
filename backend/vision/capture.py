"""Camera capture that always hands back the newest frame and reconnects after failures."""
from __future__ import annotations

import sys
import threading
import time
from typing import Callable

import cv2
import numpy as np

RECONNECT_DELAYS = (1, 2, 4, 8, 15, 30)  # seconds; the last value repeats

# Windows gives a second program a black picture when the webcam is already in use, and a
# closed privacy cover looks the same. Both arrive as valid frames, so they are checked for.
BLACK_PIXEL_LEVEL = 8        # no pixel brighter than this (of 255) means the picture is black
BLACK_REPORT_SECONDS = 2.0   # black for this long: stop treating the camera as working
BLACK_REOPEN_SECONDS = 15.0  # black for this long: close the camera and open it again
BLACK_MESSAGE = 'The camera is sending a black picture. Another program may be using it, or its cover may be closed.'


def is_black(frame: np.ndarray) -> bool:
    """True when a sparse sample of the frame has no pixel above near-black."""
    return int(frame[::16, ::16].max()) <= BLACK_PIXEL_LEVEL


def open_capture(source_type: str, source: str):
    """Open an OpenCV capture for a camera record's source."""
    if source_type == 'webcam':
        index = int(source)
        # DirectShow opens webcams much faster than the default backend on Windows.
        return cv2.VideoCapture(index, cv2.CAP_DSHOW) if sys.platform == 'win32' else cv2.VideoCapture(index)
    return cv2.VideoCapture(source)


class FrameGrabber:
    """
    Reads a camera on its own thread and keeps only the latest frame, so slow inference
    drops frames instead of falling behind. If the camera fails it retries with a growing delay.
    """

    def __init__(
        self,
        source_type: str,
        source: str,
        opener: Callable[[str, str], object] = open_capture,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ):
        self.source_type = source_type
        self.source = source
        self._opener = opener
        self._sleep = sleep
        self._clock = clock
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._frame_time = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.connected = False
        self.last_error = ''
        self.reconnects = 0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name=f'grabber-{self.source}', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def latest(self) -> tuple[np.ndarray | None, float]:
        """Newest frame and the time it was read (0.0 if there is none yet)."""
        with self._lock:
            return self._frame, self._frame_time

    def _fail(self, message: str) -> None:
        self.connected = False
        self.last_error = message
        with self._lock:
            self._frame = None

    def _run(self) -> None:
        attempt = 0
        while not self._stop.is_set():
            capture = None
            try:
                capture = self._opener(self.source_type, self.source)
                if capture is None or not capture.isOpened():
                    raise ConnectionError('The camera could not be opened.')
                frame_delay = 0.0
                if self.source_type == 'file':
                    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
                    frame_delay = 1.0 / fps  # play a recording at its own speed
                failures = 0
                black_since = None
                while not self._stop.is_set():
                    ok, frame = capture.read()
                    if not ok or frame is None:
                        if self.source_type == 'file':
                            capture.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop the recording
                            failures += 1
                            if failures > 3:
                                raise ConnectionError('The video file could not be read.')
                            continue
                        failures += 1
                        if failures >= 10:
                            raise ConnectionError('The camera stopped sending frames.')
                        self._sleep(0.05)
                        continue
                    failures = 0
                    if self.source_type != 'file' and is_black(frame):
                        now = self._clock()
                        black_since = black_since if black_since is not None else now
                        if now - black_since >= BLACK_REOPEN_SECONDS:
                            raise ConnectionError(BLACK_MESSAGE)
                        if now - black_since >= BLACK_REPORT_SECONDS:
                            self._fail(BLACK_MESSAGE)
                        self._sleep(0.05)
                        continue
                    black_since = None
                    attempt = 0
                    self.connected = True
                    self.last_error = ''
                    with self._lock:
                        self._frame = frame
                        self._frame_time = time.time()
                    if frame_delay:
                        self._sleep(frame_delay)
            except Exception as error:  # a camera driver can raise anything; keep the thread alive
                self._fail(str(error) or error.__class__.__name__)
            finally:
                if capture is not None:
                    capture.release()
            if self._stop.is_set():
                break
            self.reconnects += 1
            self._sleep(RECONNECT_DELAYS[min(attempt, len(RECONNECT_DELAYS) - 1)])
            attempt += 1
