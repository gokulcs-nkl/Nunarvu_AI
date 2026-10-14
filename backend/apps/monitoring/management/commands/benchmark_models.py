import time

import cv2
import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from vision.behavior.detectors import BehaviorModelsNotAvailable, PhoneDetector, PoseEstimator
from vision.face.engine import ModelNotAvailable, get_engine


def _time(action, runs: int) -> tuple[float, float]:
    """Median and slowest time in milliseconds over `runs` calls, after one warm-up call."""
    action()
    samples = []
    for _ in range(runs):
        started = time.perf_counter()
        action()
        samples.append((time.perf_counter() - started) * 1000)
    return float(np.median(samples)), float(max(samples))


class Command(BaseCommand):
    help = "Time each model on this computer. Use a real photo with --image for representative numbers."

    def add_arguments(self, parser):
        parser.add_argument('--image', help="Image to time against (default: a blank 1280x720 frame)")
        parser.add_argument('--runs', type=int, default=20)

    def handle(self, *args, **options):
        if options['image']:
            frame = cv2.imread(options['image'])
            if frame is None:
                raise CommandError(f"Could not read {options['image']}")
        else:
            frame = np.full((720, 1280, 3), 110, dtype=np.uint8)
        runs = max(3, options['runs'])
        height, width = frame.shape[:2]
        self.stdout.write(f"Frame: {width}x{height}, {runs} runs each\n")
        rows = []

        try:
            engine = get_engine()
        except ModelNotAvailable as error:
            raise CommandError(str(error))
        self.stdout.write(f"Face models: {engine.model_name} on {', '.join(engine.providers)}")
        rows.append(('Face detection (per frame)', *_time(lambda: engine.detect(frame), runs)))
        found = engine.detect(frame)
        if found:
            rows.append(('Face embedding (per face)', *_time(lambda: engine.embed(frame, found[0].landmarks), runs)))
        else:
            self.stdout.write("No face in the frame, so embedding is not timed. Pass --image with a face.")

        try:
            device = None if settings.BEHAVIOR_DEVICE == 'auto' else settings.BEHAVIOR_DEVICE
            pose = PoseEstimator(settings.BEHAVIOR_POSE_MODEL, device=device)
            phones = PhoneDetector(settings.BEHAVIOR_OBJECT_MODEL, device=device)
            rows.append(('Body pose (per frame)', *_time(lambda: pose.detect(frame), runs)))
            rows.append(('Phone-like objects (per frame)', *_time(lambda: phones.detect(frame), runs)))
            # The device is chosen on the first prediction, so it is read afterwards.
            self.stdout.write(f"Pose and object models on: {pose.model.predictor.device}")
        except BehaviorModelsNotAvailable as error:
            self.stdout.write(self.style.WARNING(f"Observation models not timed: {error}"))

        self.stdout.write("\nStep                                 Median ms   Slowest ms")
        for name, median, slowest in rows:
            self.stdout.write(f"{name:<36} {median:9.1f}   {slowest:10.1f}")
        detect = rows[0][1]
        self.stdout.write(f"\nFace tracking alone allows about {1000 / detect:.1f} frames per second on this computer.")
