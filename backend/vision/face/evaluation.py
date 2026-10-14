"""Measure face recognition on labelled images: how often it misses the right person or accepts the wrong one."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ThresholdResult:
    threshold: float
    false_non_match_rate: float  # same person scored below the threshold
    false_match_rate: float      # different people scored at or above it


def pair_scores(embeddings: list[np.ndarray], labels: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """
    Cosine similarity for every pair of images, split into genuine pairs (same person) and
    impostor pairs (different people). Embeddings must be unit length.
    """
    matrix = np.stack(embeddings)
    scores = matrix @ matrix.T
    names = np.array(labels)
    upper = np.triu(np.ones(scores.shape, dtype=bool), k=1)
    same = names[:, None] == names[None, :]
    return scores[upper & same], scores[upper & ~same]


def rates_at(genuine: np.ndarray, impostor: np.ndarray, threshold: float) -> ThresholdResult:
    fnmr = float((genuine < threshold).mean()) if genuine.size else float('nan')
    fmr = float((impostor >= threshold).mean()) if impostor.size else float('nan')
    return ThresholdResult(threshold, fnmr, fmr)


def sweep(genuine: np.ndarray, impostor: np.ndarray, thresholds=None) -> list[ThresholdResult]:
    thresholds = thresholds if thresholds is not None else np.round(np.arange(0.20, 0.71, 0.05), 2)
    return [rates_at(genuine, impostor, float(value)) for value in thresholds]
