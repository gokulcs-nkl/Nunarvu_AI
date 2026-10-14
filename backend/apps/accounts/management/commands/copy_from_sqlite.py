import os
import tempfile
from pathlib import Path

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connections, transaction

SOURCE = 'sqlite_source'
# Rebuilt by Django itself on the target, or not worth keeping (login sessions).
SKIPPED = ['contenttypes', 'auth.permission', 'sessions']


class Command(BaseCommand):
    help = (
        "Copy all data from an SQLite database file into the database configured in backend/.env "
        "(normally PostgreSQL). Run `python manage.py migrate` on the target first. The SQLite "
        "file is only read. Every table's row count is checked afterwards."
    )

    def add_arguments(self, parser):
        parser.add_argument('sqlite_file', help="Path to the SQLite file, for example db.sqlite3")
        parser.add_argument(
            '--replace', action='store_true',
            help="Delete what the target already holds first. Needed when it has user accounts.",
        )

    def handle(self, *args, **options):
        source_path = Path(options['sqlite_file']).resolve()
        if not source_path.is_file():
            raise CommandError(f"No such file: {source_path}")
        target = connections['default']
        if target.vendor == 'sqlite':
            raise CommandError("The configured database is SQLite. Set DB_ENGINE and the DB_* values in backend/.env first.")

        # configure_settings fills in Django's per-connection defaults; it insists on 'default' too.
        connections.settings[SOURCE] = connections.configure_settings({
            'default': dict(connections.settings['default']),
            SOURCE: {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(source_path)},
        })[SOURCE]
        models = [
            model for model in apps.get_models()
            if model._meta.managed and not model._meta.proxy
            and model._meta.app_label not in ('contenttypes', 'sessions')
            and model._meta.label_lower != 'auth.permission'
        ]
        source_tables = set(connections[SOURCE].introspection.table_names())
        models = [model for model in models if model._meta.db_table in source_tables]

        if get_user_model().objects.using('default').exists() and not options['replace']:
            raise CommandError("The target already has user accounts. Use --replace to overwrite it.")
        # Migrations create a few default rows (a default camera, settings); clear them so the
        # copied rows keep their original IDs without clashing.
        call_command('flush', interactive=False, database='default', verbosity=0)

        # Admin history entries that point at tables deleted long ago cannot be restored.
        log_model = apps.get_model('admin', 'LogEntry') if apps.is_installed('django.contrib.admin') else None
        kept_logs, skipped_logs = [], 0
        if log_model in models:
            for entry in log_model.objects.using(SOURCE).select_related('content_type'):
                if entry.content_type_id is None or entry.content_type.model_class() is not None:
                    kept_logs.append(str(entry.pk))
                else:
                    skipped_logs += 1

        dumps = []
        try:
            for labels, pks in (
                ([model._meta.label for model in models if model is not log_model], None),
                ([log_model._meta.label] if kept_logs else [], ','.join(kept_logs)),
            ):
                if not labels:
                    continue
                handle, path = tempfile.mkstemp(suffix='.json')
                os.close(handle)
                dumps.append(path)
                extra = {'primary_keys': pks} if pks else {}
                call_command('dumpdata', *labels, database=SOURCE, natural_foreign=True, output=path, verbosity=0, **extra)
            with transaction.atomic(using='default'):
                call_command('loaddata', *dumps, database='default', verbosity=0)
        finally:
            for path in dumps:
                os.remove(path)

        # Rows were inserted with their IDs, so the ID counters must be moved past them.
        statements = target.ops.sequence_reset_sql(no_style(), models)
        with target.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

        mismatches = []
        total = 0
        for model in models:
            expected = model._default_manager.using(SOURCE).count()
            if model is log_model:
                expected -= skipped_logs
            copied = model._default_manager.using('default').count()
            total += copied
            if expected != copied:
                mismatches.append(f"{model._meta.label}: {expected} in SQLite, {copied} copied")
        if mismatches:
            raise CommandError("Row counts differ:\n" + "\n".join(mismatches))
        self.stdout.write(self.style.SUCCESS(
            f"Copied {total} rows across {len(models)} tables from {source_path.name}; every count matches."
        ))
        if skipped_logs:
            self.stdout.write(f"Left out {skipped_logs} admin history entries about tables that no longer exist.")
