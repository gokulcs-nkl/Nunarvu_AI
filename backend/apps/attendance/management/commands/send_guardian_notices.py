from django.core.management.base import BaseCommand, CommandError

from apps.academics.models import Term
from apps.attendance.notices import send_notices


class Command(BaseCommand):
    help = (
        "Email guardians of students whose attendance gives an early warning. Only students with a "
        "guardian email on record are contacted, and the same warning is not repeated within two weeks. "
        "Switch it on first on the Privacy page. Use --dry-run to see who would be told."
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help="List who would be told, without sending")
        parser.add_argument('--term', type=int, help="Term id (default: the term covering today)")

    def handle(self, *args, **options):
        term = Term.objects.filter(pk=options['term']).first() if options['term'] else Term.current()
        if term is None:
            raise CommandError("No term covers today. Create a term, or pass --term.")
        result = send_notices(term, dry_run=options['dry_run'])
        if result['disabled']:
            self.stdout.write(self.style.WARNING("Guardian notices are switched off on the Privacy page."))
            return
        for item in result['recipients']:
            self.stdout.write(f"  {item['student']} -> {item['to']}")
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f"{result['skipped']} notice(s) would be sent for {term.name}."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Sent {result['sent']}, failed {result['failed']}, for {term.name}."))
