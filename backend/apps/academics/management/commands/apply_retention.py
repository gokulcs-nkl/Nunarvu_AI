from django.core.management.base import BaseCommand

from apps.academics.privacy import apply_retention


class Command(BaseCommand):
    help = "Delete data past its retention period, as set on the Privacy page. Safe to run on a schedule."

    def handle(self, *args, **options):
        removed = apply_retention()
        self.stdout.write(self.style.SUCCESS(
            f"Removed: {removed['face_enrollments']} face enrolments, "
            f"{removed['attendance_records']} attendance records, {removed['observations']} observations."
        ))
