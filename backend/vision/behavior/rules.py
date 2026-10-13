"""
Posture measurements from body keypoints.

Each function returns a measurement and whether it crosses a threshold. They describe what
is visible in one frame; they say nothing about what a person is thinking or intending.
Keypoints follow the COCO order used by YOLO pose models.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

NOSE, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_WRIST, RIGHT_WRIST = 0, 5, 6, 9, 10
MIN_KEYPOINT_CONFIDENCE = 0.5

# A wrist this many shoulder-widths above its shoulder counts as a raised hand.
HAND_RAISE_HEIGHT = 0.3
# Seated upright, the nose sits roughly 0.6-0.9 shoulder-widths above the shoulder line.
# Below this the head is level with or under the shoulders.
HEAD_DOWN_HEIGHT = 0.2


@dataclass(frozen=True)
class Measurement:
    name: str
    value: float       # the measured quantity, in shoulder-widths unless stated
    threshold: float
    met: bool
    confidence: float  # lowest confidence among the keypoints used, 0-1

    def as_dict(self) -> dict:
        return {
            'signal': self.name, 'value': round(self.value, 2), 'threshold': self.threshold,
            'confidence': round(self.confidence, 2),
        }


def _visible(confidence: np.ndarray, *indices: int) -> bool:
    return all(confidence[index] >= MIN_KEYPOINT_CONFIDENCE for index in indices)


def shoulder_width(keypoints: np.ndarray, confidence: np.ndarray) -> float | None:
    """Distance between the shoulders in pixels: the unit every other measurement is scaled by."""
    if not _visible(confidence, LEFT_SHOULDER, RIGHT_SHOULDER):
        return None
    width = float(np.linalg.norm(keypoints[LEFT_SHOULDER] - keypoints[RIGHT_SHOULDER]))
    return width if width >= 8 else None  # too small to measure anything reliably


def hand_raise(keypoints: np.ndarray, confidence: np.ndarray) -> Measurement | None:
    """How far the higher wrist is above its shoulder. None when the points needed are not visible."""
    scale = shoulder_width(keypoints, confidence)
    if scale is None:
        return None
    best: Measurement | None = None
    for wrist, shoulder in ((LEFT_WRIST, LEFT_SHOULDER), (RIGHT_WRIST, RIGHT_SHOULDER)):
        if not _visible(confidence, wrist):
            continue
        height = float(keypoints[shoulder][1] - keypoints[wrist][1]) / scale  # image y grows downwards
        found = Measurement(
            'wrist_above_shoulder', height, HAND_RAISE_HEIGHT, height >= HAND_RAISE_HEIGHT,
            float(min(confidence[wrist], confidence[shoulder])),
        )
        if best is None or found.value > best.value:
            best = found
    return best


def head_down(keypoints: np.ndarray, confidence: np.ndarray) -> Measurement | None:
    """How far the nose is above the shoulder line. A small or negative value means the head is lowered."""
    scale = shoulder_width(keypoints, confidence)
    if scale is None or not _visible(confidence, NOSE):
        return None
    shoulder_line = float(keypoints[LEFT_SHOULDER][1] + keypoints[RIGHT_SHOULDER][1]) / 2
    height = (shoulder_line - float(keypoints[NOSE][1])) / scale
    return Measurement(
        'nose_above_shoulders', height, HEAD_DOWN_HEIGHT, height <= HEAD_DOWN_HEIGHT,
        float(min(confidence[NOSE], confidence[LEFT_SHOULDER], confidence[RIGHT_SHOULDER])),
    )


def movement_speed(previous: np.ndarray, current: np.ndarray, confidence: np.ndarray, seconds: float) -> float | None:
    """Average keypoint speed in shoulder-widths per second between two samples of the same person."""
    scale = shoulder_width(current, confidence)
    if scale is None or seconds <= 0:
        return None
    visible = confidence >= MIN_KEYPOINT_CONFIDENCE
    if visible.sum() < 4:
        return None
    distance = np.linalg.norm(current[visible] - previous[visible], axis=1).mean()
    return float(distance / scale / seconds)
