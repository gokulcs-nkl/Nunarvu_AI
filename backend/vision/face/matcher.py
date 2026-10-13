"""Match face embeddings from one frame against enrolled students."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CONFIRMED = 'confirmed'
REVIEW = 'review'
UNKNOWN = 'unknown'


@dataclass(frozen=True)
class Match:
    band: str                 # CONFIRMED, REVIEW or UNKNOWN
    student_id: int | None    # None when UNKNOWN
    score: float              # cosine similarity to the best candidate, -1 to 1
    reason: str = ''          # why a match was held back for review


def match_faces(
    embeddings: list[np.ndarray],
    gallery: dict[int, np.ndarray],
    confirm_threshold: float,
    review_threshold: float,
    margin: float = 0.05,
) -> list[Match]:
    """
    Decide who each face in a single frame is.

    `gallery` maps a student id to an (n, d) array of that student's unit-length embeddings.
    A face is CONFIRMED only when its best score clears `confirm_threshold`, beats the next
    student by `margin`, and no stronger face in the same frame claimed that student.
    Anything weaker but above `review_threshold` is REVIEW; the rest are UNKNOWN.
    """
    results: list[Match] = [Match(UNKNOWN, None, 0.0)] * len(embeddings)
    if not embeddings or not gallery:
        return results

    student_ids = list(gallery.keys())
    # Per face, each student's best similarity over their enrolled embeddings.
    scores = np.stack([
        np.array([float(np.max(gallery[student_id] @ embedding)) for student_id in student_ids])
        for embedding in embeddings
    ])

    candidates = []
    for face_index, row in enumerate(scores):
        order = np.argsort(row)[::-1]
        best = int(order[0])
        runner_up = float(row[order[1]]) if len(order) > 1 else -1.0
        candidates.append((float(row[best]), face_index, student_ids[best], runner_up))

    claimed: set[int] = set()
    for score, face_index, student_id, runner_up in sorted(candidates, reverse=True):
        if score < review_threshold:
            results[face_index] = Match(UNKNOWN, None, score)
        elif student_id in claimed:
            results[face_index] = Match(REVIEW, student_id, score, 'Another face in the same frame matched this student more strongly.')
        else:
            claimed.add(student_id)
            if score < confirm_threshold:
                results[face_index] = Match(REVIEW, student_id, score, 'Match score is below the confirmation threshold.')
            elif score - runner_up < margin:
                results[face_index] = Match(REVIEW, student_id, score, 'Too close to another student to be sure.')
            else:
                results[face_index] = Match(CONFIRMED, student_id, score)
    return results
