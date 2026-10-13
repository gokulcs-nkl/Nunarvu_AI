from django.core.management.base import BaseCommand
from django.db import transaction

from app1.models import CameraConfiguration, Student as LegacyStudent
from apps.academics.models import ClassGroup, Student
from apps.monitoring.models import Camera

LEGACY_YEAR = 'legacy'


class Command(BaseCommand):
    help = (
        "Copy students and camera configurations from the old app1 tables into the new ones. "
        "Photos are not copied: students must be re-enrolled with recorded consent. Safe to re-run."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        students = 0
        for legacy in LegacyStudent.objects.all():
            student, created = Student.objects.get_or_create(
                roll_number=f"LEGACY-{legacy.pk}",
                defaults={
                    'full_name': legacy.name,
                    'email': legacy.email,
                    'phone_number': legacy.phone_number,
                },
            )
            if created:
                students += 1
                if legacy.student_class:
                    group, _ = ClassGroup.objects.get_or_create(name=legacy.student_class, academic_year=LEGACY_YEAR)
                    student.class_groups.add(group)

        cameras = 0
        for config in CameraConfiguration.objects.all():
            source = config.camera_source.strip()
            if source.isdigit():
                source_type = Camera.SourceType.WEBCAM
            elif source.lower().startswith('rtsp'):
                source_type = Camera.SourceType.RTSP
            else:
                source_type = Camera.SourceType.HTTP
            # The seeded default already covers webcam 0.
            if Camera.objects.filter(source_type=source_type, source=source).exists():
                continue
            _, created = Camera.objects.get_or_create(
                name=config.name, defaults={'source_type': source_type, 'source': source},
            )
            cameras += created

        self.stdout.write(self.style.SUCCESS(f"Imported {students} student(s) and {cameras} camera(s)."))
