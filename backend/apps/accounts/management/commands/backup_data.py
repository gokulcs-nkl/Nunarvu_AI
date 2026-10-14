import gzip
import io
from datetime import datetime
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

# Everything the new system stores. Login sessions and the old prototype's tables are left out.
APPS = ['auth.user', 'auth.group', 'accounts', 'academics', 'attendance', 'monitoring']


class Command(BaseCommand):
    help = (
        "Write a compressed backup of users, academic data, attendance, cameras and observations. "
        "Restore it into an empty, migrated database with `python manage.py loaddata <file>`. "
        "Face embeddings in the backup stay encrypted: keep FACE_EMBEDDING_KEY as well, or they cannot be read."
    )

    def add_arguments(self, parser):
        parser.add_argument('--out', default='backups', help="Folder to write to (default: backups)")

    def handle(self, *args, **options):
        folder = Path(options['out'])
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"nunarvu-{datetime.now():%Y%m%d-%H%M%S}.json.gz"
        buffer = io.StringIO()
        call_command('dumpdata', *APPS, natural_foreign=True, indent=1, stdout=buffer)
        with gzip.open(target, 'wt', encoding='utf-8') as handle:
            handle.write(buffer.getvalue())
        self.stdout.write(self.style.SUCCESS(f"Backup written to {target} ({target.stat().st_size / 1024:.0f} KB)"))
