import logging
import threading
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from apps.academics.services import run_schedule
from apps.monitoring.models import Camera
from apps.monitoring.worker import CameraWorker, HttpPublisher, NullPublisher
from vision.behavior.detectors import BehaviorModelsNotAvailable, PhoneDetector, PoseEstimator
from vision.face.engine import ModelNotAvailable, get_engine

RESCAN_SECONDS = 10


class Command(BaseCommand):
    help = (
        "Run the camera worker. It reads every enabled camera (or only --camera IDs), records "
        "attendance for the active session in each camera's room, and feeds the live view. "
        "It also starts and ends timetable sessions at their period times. "
        "Stop it with Ctrl+C."
    )

    def add_arguments(self, parser):
        parser.add_argument('--camera', type=int, action='append', help="Camera ID to run (repeatable)")
        parser.add_argument('--no-observations', action='store_true', help="Record attendance only; skip posture and phone checks")

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
        try:
            engine = get_engine()
        except ModelNotAvailable as error:
            raise CommandError(f"{error}. Run `python manage.py download_face_models` first.")
        self.stdout.write(f"Face models: {engine.model_name} on {', '.join(engine.providers)}")

        pose = phones = None
        if not options['no_observations']:
            try:
                device = None if settings.BEHAVIOR_DEVICE == 'auto' else settings.BEHAVIOR_DEVICE
                pose = PoseEstimator(settings.BEHAVIOR_POSE_MODEL, device=device)
                phones = PhoneDetector(settings.BEHAVIOR_OBJECT_MODEL, device=device)
                self.stdout.write(f"Classroom observations: on ({settings.BEHAVIOR_DEVICE})")
                self.stdout.flush()
            except BehaviorModelsNotAvailable as error:
                self.stdout.write(self.style.WARNING(f"Classroom observations are off: {error}"))

        if settings.WORKER_TOKEN:
            publisher = HttpPublisher(settings.WORKER_WEB_URL, settings.WORKER_TOKEN)
        else:
            publisher = NullPublisher()
            self.stdout.write(self.style.WARNING(
                "WORKER_TOKEN is not set: attendance will be recorded, but the live view will stay empty."
            ))

        wanted = options['camera']
        stop = threading.Event()
        threads: dict[int, threading.Thread] = {}

        def run(camera):
            try:
                CameraWorker(camera, engine, publisher, pose=pose, phones=phones).run(stop)
            finally:
                close_old_connections()

        try:
            while True:
                cameras = Camera.objects.filter(is_enabled=True)
                if wanted:
                    cameras = cameras.filter(id__in=wanted)
                for camera in cameras:
                    thread = threads.get(camera.id)
                    if thread is None or not thread.is_alive():
                        self.stdout.write(f"Starting camera {camera.id}: {camera.name} ({camera.source_type} {camera.source})")
                        threads[camera.id] = threading.Thread(target=run, args=(camera,), name=f'camera-{camera.id}', daemon=True)
                        threads[camera.id].start()
                if not threads:
                    self.stdout.write("No enabled cameras yet; waiting.")
                # Start and end timetable sessions on time, so attendance follows the periods by itself.
                changes = run_schedule()
                if any(changes.values()):
                    self.stdout.write(f"Timetable: {changes['created']} created, {changes['started']} started, {changes['closed']} closed")
                    self.stdout.flush()
                close_old_connections()
                time.sleep(RESCAN_SECONDS)
        except KeyboardInterrupt:
            self.stdout.write("Stopping...")
        finally:
            stop.set()
            for thread in threads.values():
                thread.join(timeout=8)
