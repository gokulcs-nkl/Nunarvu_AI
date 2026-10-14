"""Body-pose and phone-like-object detection with Ultralytics YOLO models."""
from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

COCO_CELL_PHONE = 67

# A YOLO model object must not run two predictions at once; camera threads share the models.
_predict_lock = threading.Lock()


class BehaviorModelsNotAvailable(RuntimeError):
    pass


def _load(path: Path):
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise BehaviorModelsNotAvailable('The ultralytics package is not installed.') from error
    try:
        # A missing file with a standard name is downloaded by Ultralytics on first use.
        return YOLO(str(path))
    except Exception as error:
        raise BehaviorModelsNotAvailable(f'Could not load {path.name}: {error}') from error


class PoseEstimator:
    """Finds people and their 17 body keypoints in a frame."""

    def __init__(self, model_path: Path, min_score: float = 0.4, image_size: int = 640, device: str | None = None):
        self.model = _load(model_path)
        self.device = device  # None lets Ultralytics choose: the graphics card when there is one
        self.min_score = min_score
        self.image_size = image_size

    def detect(self, frame: np.ndarray) -> list[tuple[tuple[int, int, int, int], np.ndarray, np.ndarray]]:
        """Returns (box, keypoints 17x2, keypoint confidences 17) for each person."""
        with _predict_lock:
            result = self.model.predict(frame, verbose=False, imgsz=self.image_size, conf=self.min_score, device=self.device)[0]
        if result.keypoints is None or result.boxes is None or len(result.boxes) == 0:
            return []
        boxes = result.boxes.xyxy.cpu().numpy()
        points = result.keypoints.xy.cpu().numpy()
        scores = result.keypoints.conf
        scores = scores.cpu().numpy() if scores is not None else np.ones(points.shape[:2])
        return [
            (tuple(int(value) for value in box), points[index], scores[index])
            for index, box in enumerate(boxes)
        ]


class PhoneDetector:
    """Finds phone-like objects. Small or partly hidden phones are often missed."""

    def __init__(self, model_path: Path, min_score: float = 0.35, image_size: int = 640, device: str | None = None):
        self.model = _load(model_path)
        self.device = device
        self.min_score = min_score
        self.image_size = image_size

    def detect(self, frame: np.ndarray) -> list[tuple[float, float, float, float, float]]:
        """Returns (x1, y1, x2, y2, score) for each phone-like object."""
        with _predict_lock:
            result = self.model.predict(
                frame, verbose=False, imgsz=self.image_size, conf=self.min_score, classes=[COCO_CELL_PHONE], device=self.device,
            )[0]
        if result.boxes is None or len(result.boxes) == 0:
            return []
        boxes = result.boxes.xyxy.cpu().numpy()
        scores = result.boxes.conf.cpu().numpy()
        return [(*map(float, box), float(score)) for box, score in zip(boxes, scores)]
