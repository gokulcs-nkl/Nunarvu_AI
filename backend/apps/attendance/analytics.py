"""Reports and analytics, computed from stored attendance records and events (never from video)."""
from __future__ import annotations

import io
from datetime import timedelta

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import ClassGroup, Student, Subject
from apps.accounts.audit import record
from apps.accounts.models import Role, get_role
from apps.accounts.permissions import STAFF_ROLES, RolePermission
from apps.monitoring.models import Camera, CameraStatusLog, ClassroomEvent

from .models import AttendanceRecord

Status = AttendanceRecord.Status
ATTENDED = [Status.PRESENT, Status.LATE, Status.LEFT_EARLY]

RECORD_FILTERS = {
    'class_group': 'session__class_group', 'subject': 'session__subject', 'teacher': 'session__teacher',
    'student': 'student', 'date_from': 'session__date__gte', 'date_to': 'session__date__lte',
}


def scoped_records(request):
    """Attendance records the user may see, narrowed by the request's filters."""
    records = AttendanceRecord.objects.all()
    if get_role(request.user) == Role.TEACHER:
        records = records.filter(session__teacher__user=request.user)
    for param, lookup in RECORD_FILTERS.items():
        value = request.query_params.get(param)
        if not value:
            continue
        if param.startswith('date_'):
            value = parse_date(value)
            if value is None:
                raise ValidationError({param: 'Use YYYY-MM-DD.'})
        elif not str(value).isdigit():
            raise ValidationError({param: 'Not a valid id.'})
        records = records.filter(**{lookup: value})
    return records


def _tallies():
    return {
        'attended': Count('id', filter=Q(status__in=ATTENDED)),
        'decided': Count('id', filter=~Q(status=Status.PENDING)),
        'sessions': Count('session', distinct=True),
    }


def _percent(attended: int, decided: int) -> float | None:
    return round(100 * attended / decided, 1) if decided else None


class AttendanceSummaryView(APIView):
    """
    Attendance totals, the daily trend, and breakdowns by class and subject.
    Filters: class_group, subject, teacher, student, date_from, date_to.
    Pending records are excluded from every percentage until a teacher decides them.
    """
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES

    def get(self, request):
        records = scoped_records(request)
        counts = records.aggregate(
            total=Count('id'), sessions=Count('session', distinct=True), students=Count('student', distinct=True),
            **{status: Count('id', filter=Q(status=status)) for status in Status.values},
        )
        attended = sum(counts[status] for status in ATTENDED)
        decided = counts['total'] - counts[Status.PENDING]

        by_date = [
            {'date': row['session__date'], 'attended': row['attended'], 'decided': row['decided'],
             'percent': _percent(row['attended'], row['decided'])}
            for row in records.values('session__date').annotate(**_tallies()).order_by('session__date')
        ]

        def breakdown(field, names):
            rows = records.values(field).annotate(**_tallies()).order_by(field)
            return [
                {'id': row[field], 'name': names.get(row[field], 'Unknown'), 'sessions': row['sessions'],
                 'attended': row['attended'], 'decided': row['decided'], 'percent': _percent(row['attended'], row['decided'])}
                for row in rows
            ]

        class_names = {group.id: str(group) for group in ClassGroup.objects.all()}
        subject_names = {subject.id: subject.code for subject in Subject.objects.all()}
        return Response({
            'totals': {
                'records': counts['total'],
                'sessions': counts['sessions'],
                'students': counts['students'],
                'present': counts[Status.PRESENT],
                'late': counts[Status.LATE],
                'left_early': counts[Status.LEFT_EARLY],
                'absent': counts[Status.ABSENT],
                'pending': counts[Status.PENDING],
                'attendance_percent': _percent(attended, decided),
            },
            'by_date': by_date,
            'by_class': breakdown('session__class_group', class_names),
            'by_subject': breakdown('session__subject', subject_names),
        })


class ObservationSummaryView(APIView):
    """Counts of classroom observations by type and review status. Filters: class_group, subject, date_from, date_to."""
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES

    def get(self, request):
        events = ClassroomEvent.objects.all()
        if get_role(request.user) == Role.TEACHER:
            events = events.filter(session__teacher__user=request.user)
        lookups = {
            'class_group': 'session__class_group', 'subject': 'session__subject',
            'date_from': 'session__date__gte', 'date_to': 'session__date__lte',
        }
        for param, lookup in lookups.items():
            value = request.query_params.get(param)
            if not value:
                continue
            if param.startswith('date_'):
                value = parse_date(value)
                if value is None:
                    raise ValidationError({param: 'Use YYYY-MM-DD.'})
            elif not str(value).isdigit():
                raise ValidationError({param: 'Not a valid id.'})
            events = events.filter(**{lookup: value})

        Review = ClassroomEvent.Review
        rows = events.values('kind').annotate(
            total=Count('id'),
            unreviewed=Count('id', filter=Q(review_status=Review.UNREVIEWED)),
            confirmed=Count('id', filter=Q(review_status=Review.CONFIRMED)),
            dismissed=Count('id', filter=Q(review_status=Review.DISMISSED)),
        )
        found = {row['kind']: row for row in rows}
        return Response([
            {'kind': kind, 'label': label, **{key: found.get(kind, {}).get(key, 0) for key in ('total', 'unreviewed', 'confirmed', 'dismissed')}}
            for kind, label in ClassroomEvent.Kind.choices
        ])


def camera_uptime(camera: Camera, start, end) -> float:
    """Seconds between `start` and `end` during which the camera's worker reported it online."""
    previous = CameraStatusLog.objects.filter(camera=camera, at__lt=start).order_by('-at').first()
    status, since = (previous.status if previous else Camera.Status.OFFLINE), start
    online = 0.0
    for entry in CameraStatusLog.objects.filter(camera=camera, at__gte=start, at__lte=end).order_by('at'):
        if status == Camera.Status.ONLINE:
            online += (entry.at - since).total_seconds()
        status, since = entry.status, entry.at
    if status == Camera.Status.ONLINE:
        # A worker that was killed never logs "offline"; its last heartbeat marks the real end.
        last = min(end, camera.last_heartbeat + Camera.HEARTBEAT_TIMEOUT) if camera.last_heartbeat else since
        online += max(0.0, (last - since).total_seconds())
    return online


class SystemHealthView(APIView):
    """Camera status and uptime, items waiting for review, and the models in use."""
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES

    def get(self, request):
        try:
            hours = min(max(int(request.query_params.get('hours', 24)), 1), 24 * 30)
        except ValueError:
            raise ValidationError({'hours': 'Use a whole number of hours.'})
        end = timezone.now()
        start = end - timedelta(hours=hours)
        window = (end - start).total_seconds()

        cameras = []
        for camera in Camera.objects.select_related('room'):
            online = camera_uptime(camera, start, end)
            last_change = camera.status_log.first()
            cameras.append({
                'id': camera.id, 'name': camera.name, 'room': camera.room.name if camera.room else None,
                'is_enabled': camera.is_enabled, 'status': camera.live_status, 'last_error': camera.last_error,
                'fps': camera.fps, 'latency_ms': camera.latency_ms, 'last_heartbeat': camera.last_heartbeat,
                'uptime_percent': round(100 * online / window, 1),
                'last_change': {'status': last_change.status, 'detail': last_change.detail, 'at': last_change.at} if last_change else None,
            })

        records = AttendanceRecord.objects.all()
        events = ClassroomEvent.objects.all()
        if get_role(request.user) == Role.TEACHER:
            records = records.filter(session__teacher__user=request.user)
            events = events.filter(session__teacher__user=request.user)

        from django.conf import settings
        from vision.face.engine import configured_model_name

        return Response({
            'window_hours': hours,
            'cameras': cameras,
            'alerts': [
                {'camera': item['id'], 'message': f"{item['name']}: {item['last_error'] or 'camera error'}"}
                for item in cameras if item['status'] == Camera.Status.ERROR
            ] + [
                {'camera': item['id'], 'message': f"{item['name']} is enabled but no worker is reporting for it."}
                for item in cameras if item['is_enabled'] and item['status'] == Camera.Status.OFFLINE
            ],
            'pending_attendance': records.filter(status=Status.PENDING).count(),
            'unreviewed_observations': events.filter(review_status=ClassroomEvent.Review.UNREVIEWED).count(),
            'students': {
                'active': Student.objects.filter(is_active=True).count(),
                'with_consent': Student.objects.filter(is_active=True, consent_given=True).count(),
                'enrolled_faces': Student.objects.filter(
                    is_active=True, face_enrollments__model_name=configured_model_name(),
                ).distinct().count(),
            },
            'models': {
                'face': configured_model_name(),
                'pose': settings.BEHAVIOR_POSE_MODEL.name,
                'objects': settings.BEHAVIOR_OBJECT_MODEL.name,
            },
        })


def attendance_pdf(rows: list[dict], filters: dict, generated_by: str) -> bytes:
    """Attendance report as a PDF table."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
        title='Attendance report', author='Nunarvu AI',
    )
    styles = getSampleStyleSheet()
    described = ', '.join(f'{key.replace("_", " ")}: {value}' for key, value in filters.items()) or 'none'
    story = [
        Paragraph('Attendance report', styles['Title']),
        Paragraph(f'Filters: {described}', styles['Normal']),
        Paragraph(
            f'Generated {timezone.localtime():%d %b %Y %H:%M} by {generated_by}. '
            'Late and left-early count as attended. Records pending teacher review are excluded from the percentage.',
            styles['Normal'],
        ),
        Spacer(1, 6 * mm),
    ]
    header = ['Roll no.', 'Name', 'Sessions', 'Present', 'Late', 'Left early', 'Absent', 'Pending', 'Attendance']
    body = [
        [row['roll_number'], row['full_name'], row['sessions'], row['present'], row['late'], row['left_early'],
         row['absent'], row['pending'], '-' if row['attendance_percent'] is None else f"{row['attendance_percent']}%"]
        for row in rows
    ] or [['No attendance recorded for these filters.'] + [''] * 8]
    table = Table([header] + body, repeatRows=1, colWidths=[28 * mm, 70 * mm] + [22 * mm] * 6 + [26 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16202e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f6f7f9')]),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#e2e5ea')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    document.build(story)
    return buffer.getvalue()


def pdf_response(request, rows: list[dict]) -> HttpResponse:
    filters = {key: value for key, value in request.query_params.items() if key != 'export' and value}
    response = HttpResponse(attendance_pdf(rows, filters, request.user.username), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.pdf"'
    record(request, 'export_attendance_report', request.user, {'rows': len(rows), 'format': 'pdf', 'filters': filters})
    return response

