import logging
import threading
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from apps.monitoring.models import Camera
from apps.monitoring.worker import CameraWorker, HttpPublisher, NullPublisher
from vision.face.engine import ModelNotAvailable, get_engine

RESCAN_SECONDS = 10


class Command(BaseCommand):
    help = (
        "Run the camera worker. It reads every enabled camera (or only --camera IDs), records "
        "attendance for the active session in each camera's room, and feeds the live view. "
        "Stop it with Ctrl+C."
    )

    def add_arguments(self, parser):
        parser.add_argument('--camera', type=int, action='append', help="Camera ID to run (repeatable)")

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
        try:
            engine = get_engine()
        except ModelNotAvailable as error:
            raise CommandError(f"{error}. Run `python manage.py download_face_models` first.")
        self.stdout.write(f"Face models: {engine.model_name} on {', '.join(engine.providers)}")

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
                CameraWorker(camera, engine, publisher).run(stop)
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
                close_old_connections()
                time.sleep(RESCAN_SECONDS)
        except KeyboardInterrupt:
            self.stdout.write("Stopping...")
        finally:
            stop.set()
            for thread in threads.values():
                thread.join(timeout=8)
