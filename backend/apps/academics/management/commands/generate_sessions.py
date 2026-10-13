from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.academics.services import generate_sessions_for_date


class Command(BaseCommand):
    help = "Create class sessions from the timetable for a date (default: today)."

    def add_arguments(self, parser):
        parser.add_argument('--date', help="Date in YYYY-MM-DD format")

    def handle(self, *args, **options):
        day = date.fromisoformat(options['date']) if options['date'] else timezone.localdate()
        created = generate_sessions_for_date(day)
        self.stdout.write(self.style.SUCCESS(f"{created} session(s) created for {day}"))
