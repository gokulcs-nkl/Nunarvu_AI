"""
Face detection (SCRFD) and embedding (ArcFace) on ONNX Runtime.

Uses the model files from an InsightFace pack (buffalo_l, buffalo_s or buffalo_sc)
directly, so only onnxruntime, OpenCV and NumPy are required. The pretrained packs
are licensed by InsightFace for non-commercial research use.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# Landmark positions (eyes, nose, mouth corners) that ArcFace expects in a 112x112 crop.
ARCFACE_TEMPLATE = np.array(
    [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366], [41.5493, 92.3655], [70.7299, 92.2041]],
    dtype=np.float32,
)
DETECTOR_STRIDES = (8, 16, 32)
ANCHORS_PER_CELL = 2


class ModelNotAvailable(RuntimeError):
    """The face model files are missing or could not be loaded."""


@dataclass(frozen=True)
class FaceBox:
    box: tuple[int, int, int, int]  # x1, y1, x2, y2 in source-image pixels
    score: float                    # detector confidence, 0-1
    landmarks: np.ndarray           # 5x2 points


@dataclass(frozen=True)
class DetectedFace:
    box: tuple[int, int, int, int]  # x1, y1, x2, y2 in source-image pixels
    score: float                    # detector confidence, 0-1
    landmarks: np.ndarray           # 5x2 points
    embedding: np.ndarray           # unit-length vector

    @property
    def width(self) -> int:
        return self.box[2] - self.box[0]

    @property
    def height(self) -> int:
        return self.box[3] - self.box[1]


def _nms(boxes: np.ndarray, scores: np.ndarray, threshold: float) -> list[int]:
    order = scores.argsort()[::-1]
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    keep: list[int] = []
    while order.size > 0:
        current = order[0]
        keep.append(int(current))
        rest = order[1:]
        x1 = np.maximum(boxes[current, 0], boxes[rest, 0])
        y1 = np.maximum(boxes[current, 1], boxes[rest, 1])
        x2 = np.minimum(boxes[current, 2], boxes[rest, 2])
        y2 = np.minimum(boxes[current, 3], boxes[rest, 3])
        overlap = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
        iou = overlap / (areas[current] + areas[rest] - overlap + 1e-9)
        order = rest[iou <= threshold]
    return keep


class FaceEngine:
    """Detects faces in a BGR image and returns an aligned embedding for each."""

    def __init__(
        self,
        detector_path: Path,
        recognizer_path: Path,
        providers: list[str] | None = None,
        input_size: int = 640,
        score_threshold: float = 0.5,
        nms_threshold: float = 0.4,
    ):
        for path in (detector_path, recognizer_path):
            if not Path(path).is_file():
                raise ModelNotAvailable(f"Model file not found: {path}")
        try:
            import onnxruntime as ort
        except ImportError as error:
            raise ModelNotAvailable("onnxruntime is not installed") from error

        # On a GPU install the NVIDIA libraries were already loaded at start-up (see vision.gpu).
        available = ort.get_available_providers()
        wanted = providers or ['CUDAExecutionProvider', 'CPUExecutionProvider']
        chosen = [name for name in wanted if name in available] or ['CPUExecutionProvider']
        self.detector = ort.InferenceSession(str(detector_path), providers=chosen)
        self.recognizer = ort.InferenceSession(str(recognizer_path), providers=chosen)
        self.providers = self.detector.get_providers()
        self.input_size = input_size
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.model_name = f"{Path(detector_path).stem}+{Path(recognizer_path).stem}"
        self._detector_input = self.detector.get_inputs()[0].name
        self._recognizer_input = self.recognizer.get_inputs()[0].name
        self._anchor_cache: dict[int, np.ndarray] = {}

    def _anchors(self, stride: int) -> np.ndarray:
        if stride not in self._anchor_cache:
            cells = self.input_size // stride
            grid = np.stack(np.mgrid[:cells, :cells][::-1], axis=-1).astype(np.float32).reshape(-1, 2) * stride
            self._anchor_cache[stride] = np.repeat(grid, ANCHORS_PER_CELL, axis=0)
        return self._anchor_cache[stride]

    def _detect(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        height, width = image.shape[:2]
        scale = self.input_size / max(height, width)
        resized = cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale))))
        canvas = np.zeros((self.input_size, self.input_size, 3), dtype=np.uint8)
        canvas[:resized.shape[0], :resized.shape[1]] = resized
        blob = cv2.dnn.blobFromImage(canvas, 1.0 / 128.0, (self.input_size, self.input_size), (127.5, 127.5, 127.5), swapRB=True)
        outputs = self.detector.run(None, {self._detector_input: blob})

        levels = len(DETECTOR_STRIDES)
        all_boxes, all_scores, all_points = [], [], []
        for index, stride in enumerate(DETECTOR_STRIDES):
            scores = outputs[index].reshape(-1)
            distances = outputs[index + levels].reshape(-1, 4) * stride
            offsets = outputs[index + 2 * levels].reshape(-1, 10) * stride
            keep = scores >= self.score_threshold
            if not keep.any():
                continue
            centers = self._anchors(stride)[keep]
            distances, offsets = distances[keep], offsets[keep]
            boxes = np.concatenate([centers - distances[:, :2], centers + distances[:, 2:]], axis=1)
            points = centers[:, None, :] + offsets.reshape(-1, 5, 2)
            all_boxes.append(boxes)
            all_scores.append(scores[keep])
            all_points.append(points)

        if not all_boxes:
            return np.empty((0, 4)), np.empty((0,)), np.empty((0, 5, 2))
        boxes = np.concatenate(all_boxes) / scale
        scores = np.concatenate(all_scores)
        points = np.concatenate(all_points) / scale
        keep = _nms(boxes, scores, self.nms_threshold)
        return boxes[keep], scores[keep], points[keep]

    def _embed(self, image: np.ndarray, landmarks: np.ndarray) -> np.ndarray | None:
        matrix, _ = cv2.estimateAffinePartial2D(landmarks.astype(np.float32), ARCFACE_TEMPLATE, method=cv2.LMEDS)
        if matrix is None:
            return None
        aligned = cv2.warpAffine(image, matrix, (112, 112), borderValue=0.0)
        blob = cv2.dnn.blobFromImage(aligned, 1.0 / 127.5, (112, 112), (127.5, 127.5, 127.5), swapRB=True)
        vector = self.recognizer.run(None, {self._recognizer_input: blob})[0].reshape(-1).astype(np.float32)
        norm = float(np.linalg.norm(vector))
        return vector / norm if norm > 0 else None

    def detect(self, image: np.ndarray) -> list[FaceBox]:
        """Find faces in a BGR image without computing embeddings. Largest first."""
        if image is None or image.ndim != 3 or image.size == 0:
            return []
        height, width = image.shape[:2]
        boxes, scores, points = self._detect(image)
        found: list[FaceBox] = []
        for box, score, landmarks in zip(boxes, scores, points):
            x1, y1, x2, y2 = box
            clipped = (
                int(max(0, round(x1))), int(max(0, round(y1))),
                int(min(width, round(x2))), int(min(height, round(y2))),
            )
            if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
                continue
            found.append(FaceBox(box=clipped, score=float(score), landmarks=landmarks))
        found.sort(key=lambda face: (face.box[2] - face.box[0]) * (face.box[3] - face.box[1]), reverse=True)
        return found

    def embed(self, image: np.ndarray, landmarks: np.ndarray) -> np.ndarray | None:
        """Unit-length embedding for the face with these landmarks, or None if it cannot be aligned."""
        return self._embed(image, landmarks)

    def analyze(self, image: np.ndarray) -> list[DetectedFace]:
        """Detect every face in a BGR image and embed each one. Largest first."""
        faces: list[DetectedFace] = []
        for found in self.detect(image):
            embedding = self._embed(image, found.landmarks)
            if embedding is not None:
                faces.append(DetectedFace(box=found.box, score=found.score, landmarks=found.landmarks, embedding=embedding))
        return faces


def configured_model_name() -> str:
    """Name of the model pair in settings, without loading the models."""
    from django.conf import settings

    return f"{Path(settings.FACE_DETECTOR_MODEL).stem}+{Path(settings.FACE_RECOGNIZER_MODEL).stem}"


_engine: FaceEngine | None = None
_engine_lock = threading.Lock()


def get_engine() -> FaceEngine:
    """Shared engine, loaded on first use from the paths in Django settings."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from django.conf import settings

                _engine = FaceEngine(Path(settings.FACE_DETECTOR_MODEL), Path(settings.FACE_RECOGNIZER_MODEL))
    return _engine
