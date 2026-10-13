import urllib.request
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

RELEASE_URL = 'https://github.com/deepinsight/insightface/releases/download/v0.7/{pack}.zip'
PACKS = {
    'buffalo_l': 'Most accurate; about 280 MB. Recommended with a GPU.',
    'buffalo_s': 'Smaller and faster; about 120 MB.',
    'buffalo_sc': 'Smallest; about 15 MB. Detection and recognition only, for CPU-only machines.',
}


class Command(BaseCommand):
    help = (
        "Download an InsightFace model pack into backend/models/. "
        "The pretrained models are licensed for non-commercial research use only."
    )

    def add_arguments(self, parser):
        parser.add_argument('--pack', default='buffalo_l', choices=sorted(PACKS))

    def handle(self, *args, **options):
        pack = options['pack']
        target = Path(settings.BASE_DIR) / 'models' / pack
        if target.is_dir() and any(target.glob('*.onnx')):
            self.stdout.write(f"{pack} is already in {target}")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        archive = target.parent / f'{pack}.zip'
        self.stdout.write(f"Downloading {pack} ({PACKS[pack]})")
        try:
            urllib.request.urlretrieve(RELEASE_URL.format(pack=pack), archive)
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(target)
        except (OSError, zipfile.BadZipFile) as error:
            raise CommandError(f"Download failed: {error}")
        archive.unlink()
        self.stdout.write(self.style.SUCCESS(f"Saved to {target}"))
        if pack != 'buffalo_l':
            self.stdout.write("Set FACE_MODEL_DIR, FACE_DETECTOR_FILE and FACE_RECOGNIZER_FILE in backend/.env to use this pack.")
