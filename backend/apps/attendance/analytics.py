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
from apps.accounts.permissions import ADMIN_ONLY, STAFF_ROLES, RolePermission
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



class ForecastView(APIView):
    """
    Attendance shortage forecast for a term. For each student and subject it says how many of the
    remaining classes the student must still attend to finish at or above the minimum.
    Query: term (id, default the current term), class_group, subject, status (at_risk|cannot_reach|...).
    Teachers see only the classes and subjects they teach.
    """
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES

    def get(self, request):
        from datetime import date as date_type

        from apps.academics.models import Term
        from .forecast import AT_RISK, CANNOT_REACH, forecast as build_forecast

        term_id = request.query_params.get('term')
        if term_id:
            if not str(term_id).isdigit():
                raise ValidationError({'term': 'Not a valid id.'})
            term = Term.objects.filter(pk=term_id).first()
            if term is None:
                raise ValidationError({'term': 'No such term.'})
        else:
            term = Term.current()
            if term is None:
                return Response({'term': None, 'detail': 'No term covers today. Create a term to see the forecast.', 'rows': []})

        today = date_type.today()
        if request.query_params.get('as_of'):
            parsed = parse_date(request.query_params['as_of'])
            if parsed is None:
                raise ValidationError({'as_of': 'Use YYYY-MM-DD.'})
            today = parsed

        def ids(name):
            value = request.query_params.get(name)
            if not value:
                return None
            parts = [part for part in value.split(',') if part.strip().isdigit()]
            if not parts:
                raise ValidationError({name: 'Use comma-separated ids.'})
            return [int(part) for part in parts]

        teacher_user = request.user if get_role(request.user) == Role.TEACHER else None
        rows = build_forecast(term, today, class_group_ids=ids('class_group'), subject_ids=ids('subject'), teacher_user=teacher_user)

        wanted = request.query_params.get('status')
        if wanted:
            rows = [row for row in rows if row.status == wanted]

        from .forecast import as_dicts
        return Response({
            'term': {'id': term.id, 'name': term.name, 'start_date': term.start_date, 'end_date': term.end_date,
                     'minimum_attendance': term.minimum_attendance},
            'as_of': today,
            'counts': {
                'at_risk': sum(1 for row in rows if row.status == AT_RISK),
                'cannot_reach': sum(1 for row in rows if row.status == CANNOT_REACH),
                'total': len(rows),
            },
            'rows': as_dicts(rows),
        })


class ParticipationHeatmapView(APIView):
    """
    Where in the room a chosen kind of observation happened, as counts on a grid. It describes the
    room, not individuals, so no student is named. Query: kind (default hand_raise), class_group,
    subject, date_from, date_to, grid (cells per side, 3-10, default 6).
    """
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES

    def get(self, request):
        kind = request.query_params.get('kind', ClassroomEvent.Kind.HAND_RAISE)
        if kind not in ClassroomEvent.Kind.values:
            raise ValidationError({'kind': f'Use one of {", ".join(ClassroomEvent.Kind.values)}.'})
        try:
            grid = min(max(int(request.query_params.get('grid', 6)), 3), 10)
        except ValueError:
            raise ValidationError({'grid': 'Use a whole number.'})

        events = ClassroomEvent.objects.filter(kind=kind, position_x__isnull=False, position_y__isnull=False)
        if get_role(request.user) == Role.TEACHER:
            events = events.filter(session__teacher__user=request.user)
        for param, lookup in (('class_group', 'session__class_group'), ('subject', 'session__subject')):
            value = request.query_params.get(param)
            if value:
                if not value.isdigit():
                    raise ValidationError({param: 'Not a valid id.'})
                events = events.filter(**{lookup: value})
        for param, lookup in (('date_from', 'session__date__gte'), ('date_to', 'session__date__lte')):
            value = request.query_params.get(param)
            if value:
                parsed = parse_date(value)
                if parsed is None:
                    raise ValidationError({param: 'Use YYYY-MM-DD.'})
                events = events.filter(**{lookup: parsed})

        cells = [[0] * grid for _ in range(grid)]
        total = 0
        for x, y in events.values_list('position_x', 'position_y'):
            column = min(int(x * grid), grid - 1)
            row = min(int(y * grid), grid - 1)
            cells[row][column] += 1
            total += 1
        peak = max((value for line in cells for value in line), default=0)
        return Response({'kind': kind, 'grid': grid, 'total': total, 'peak': peak, 'cells': cells})


class RiskView(APIView):
    """
    Early warning list: students whose attendance pattern suggests they may be disengaging,
    with the reasons that produced each score. Query: term, class_group, band (low|medium|high).
    Teachers see only their own classes.
    """
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES

    def get(self, request):
        from datetime import date as date_type

        from apps.academics.models import Term

        from .risk import as_dicts, assess

        term_id = request.query_params.get('term')
        term = Term.objects.filter(pk=term_id).first() if (term_id or '').isdigit() else Term.current()
        if term is None:
            return Response({'term': None, 'detail': 'No term covers today. Create a term to see early warnings.', 'rows': []})

        today = date_type.today()
        if request.query_params.get('as_of'):
            parsed = parse_date(request.query_params['as_of'])
            if parsed is None:
                raise ValidationError({'as_of': 'Use YYYY-MM-DD.'})
            today = parsed

        groups = request.query_params.get('class_group')
        class_group_ids = [int(part) for part in groups.split(',') if part.strip().isdigit()] if groups else None
        teacher_user = request.user if get_role(request.user) == Role.TEACHER else None
        rows = assess(term, today, class_group_ids=class_group_ids, teacher_user=teacher_user)

        band = request.query_params.get('band')
        if band:
            rows = [row for row in rows if row.band == band]
        return Response({
            'term': {'id': term.id, 'name': term.name, 'minimum_attendance': term.minimum_attendance},
            'as_of': today,
            'counts': {
                'high': sum(1 for row in rows if row.band == 'high'),
                'medium': sum(1 for row in rows if row.band == 'medium'),
                'total': len(rows),
            },
            'rows': as_dicts(rows),
        })


class GuardianNoticeView(APIView):
    """
    Notices to guardians about attendance. GET previews who would be told and lists what was
    already sent; POST sends them. Administrators only for sending.
    """
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES
    write_roles = ADMIN_ONLY

    def _term(self, request):
        from apps.academics.models import Term

        term_id = request.query_params.get('term') or request.data.get('term')
        if term_id and str(term_id).isdigit():
            return Term.objects.filter(pk=term_id).first()
        return Term.current()

    def get(self, request):
        from apps.academics.models import PrivacySettings

        from .models import GuardianNotice
        from .notices import pending_notices

        term = self._term(request)
        if term is None:
            return Response({'term': None, 'detail': 'No term covers today.', 'pending': [], 'sent': []})
        teacher_user = request.user if get_role(request.user) == Role.TEACHER else None
        pending = pending_notices(term, teacher_user=teacher_user)
        sent = GuardianNotice.objects.filter(term=term).select_related('student')[:50]
        return Response({
            'term': {'id': term.id, 'name': term.name},
            'enabled': PrivacySettings.load().guardian_notices_enabled,
            'pending': [
                {'student': row.student, 'roll_number': row.roll_number, 'full_name': row.full_name,
                 'to': row.guardian_contact, 'score': row.score, 'percent': row.percent}
                for row in pending
            ],
            'sent': [
                {'id': notice.id, 'roll_number': notice.student.roll_number, 'to': notice.sent_to,
                 'subject': notice.subject, 'sent_at': notice.sent_at, 'attendance_percent': notice.attendance_percent}
                for notice in sent
            ],
        })

    def post(self, request):
        from .notices import send_notices

        term = self._term(request)
        if term is None:
            raise ValidationError({'term': 'No term covers today.'})
        dry_run = bool(request.data.get('dry_run'))
        result = send_notices(term, sent_by=request.user, dry_run=dry_run)
        if not dry_run:
            record(request, 'send_guardian_notices', request.user, {'term': term.name, 'sent': result['sent'], 'failed': result['failed']})
        return Response(result)
