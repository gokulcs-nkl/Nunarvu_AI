"""Follow faces from frame to frame so each person is recognised once, not on every frame."""
from __future__ import annotations

from dataclasses import dataclass, field

Box = tuple[int, int, int, int]


def iou(a: Box, b: Box) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0, x2 - x1) * max(0, y2 - y1)
    if overlap == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return overlap / (area_a + area_b - overlap)


@dataclass
class Track:
    id: int
    box: Box
    first_seen: float
    last_seen: float
    # Identity from the most recent recognition attempt
    band: str = 'unknown'
    student_id: int | None = None
    score: float = 0.0
    reason: str = ''
    recognized_at: float | None = None
    extra: dict = field(default_factory=dict)


class FaceTracker:
    """
    Greedy IoU tracker. Faces move little between sampled frames, so overlap alone is
    enough to keep identities stable; a face that disappears for `max_gap` seconds is dropped
    and will be recognised afresh when it returns.
    """

    def __init__(self, min_iou: float = 0.3, max_gap: float = 1.5):
        self.min_iou = min_iou
        self.max_gap = max_gap
        self.tracks: dict[int, Track] = {}
        self._next_id = 1

    def update(self, boxes: list[Box], now: float) -> list[Track]:
        """Match this frame's boxes to tracks. Returns the track for each box, in the same order."""
        pairs = sorted(
            ((iou(track.box, box), track.id, index) for track in self.tracks.values() for index, box in enumerate(boxes)),
            reverse=True,
        )
        assigned: dict[int, Track] = {}
        used_tracks: set[int] = set()
        for overlap, track_id, index in pairs:
            if overlap < self.min_iou:
                break
            if track_id in used_tracks or index in assigned:
                continue
            track = self.tracks[track_id]
            track.box = boxes[index]
            track.last_seen = now
            assigned[index] = track
            used_tracks.add(track_id)

        for index, box in enumerate(boxes):
            if index not in assigned:
                track = Track(id=self._next_id, box=box, first_seen=now, last_seen=now)
                self._next_id += 1
                self.tracks[track.id] = track
                assigned[index] = track

        self.tracks = {track_id: track for track_id, track in self.tracks.items() if now - track.last_seen <= self.max_gap}
        return [assigned[index] for index in range(len(boxes))]
