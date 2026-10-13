import csv

import cv2
import numpy as np
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import ClassSession, Student
from apps.academics.views import teacher_class_group_ids
from apps.accounts.audit import record
from apps.accounts.models import Role, get_role
from apps.accounts.permissions import STAFF_ROLES, RolePermission
from vision.face import matcher
from vision.face.engine import ModelNotAvailable, configured_model_name, get_engine

from .embeddings import encrypt_embedding, gallery_for_class
from .models import AttendanceRecord, FaceEnrollment
from .serializers import AttendanceRecordSerializer
from .services import Sighting, record_sightings

MAX_IMAGE_BYTES = 8 * 1024 * 1024


class FaceServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Face recognition is not available on this server.'


def _engine():
    try:
        return get_engine()
    except ModelNotAvailable as error:
        raise FaceServiceUnavailable(f'Face models are not installed: {error}')


def _read_image(request) -> np.ndarray:
    """The uploaded image, or the latest frame of a worker-run camera when `camera` is given instead."""
    upload = request.FILES.get('image')
    if upload is None and request.data.get('camera'):
        from apps.monitoring import live

        try:
            jpeg = live.latest_frame(int(request.data['camera']))
        except (TypeError, ValueError):
            raise ValidationError({'camera': 'Not a valid camera.'})
        if jpeg is None:
            raise ValidationError({'camera': 'That camera is not sending frames right now.'})
        data = jpeg
    elif upload is None:
        raise ValidationError({'image': 'Attach an image file in the "image" field.'})
    elif upload.size > MAX_IMAGE_BYTES:
        raise ValidationError({'image': 'Image is larger than 8 MB.'})
    else:
        data = upload.read()
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValidationError({'image': 'The file is not a readable image.'})
    return image


def _student_for(request, pk) -> Student:
    student = get_object_or_404(Student, pk=pk)
    if get_role(request.user) == Role.TEACHER and not student.class_groups.filter(
        id__in=teacher_class_group_ids(request.user)
    ).exists():
        raise PermissionDenied('This student is not in one of your classes.')
    return student


class FaceEnrollmentView(APIView):
    """
    Enrol, count or remove a student's face data.

    POST takes one image containing exactly one clear face. The image is used to compute an
    embedding and is then discarded. Enrolment is refused unless the student's consent is recorded.
    """
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES
    write_roles = STAFF_ROLES
    parser_classes = [MultiPartParser, JSONParser]

    def get(self, request, pk):
        student = _student_for(request, pk)
        return Response({'student': student.id, 'count': student.face_enrollments.filter(model_name=configured_model_name()).count()})

    def post(self, request, pk):
        student = _student_for(request, pk)
        if not student.consent_given:
            return Response(
                {'detail': 'Consent has not been recorded for this student, so their face cannot be enrolled.'},
                status=status.HTTP_409_CONFLICT,
            )
        engine = _engine()
        current = student.face_enrollments.filter(model_name=engine.model_name)
        if current.count() >= settings.FACE_ENROLL_MAX_PER_STUDENT:
            raise ValidationError({'detail': f'This student already has {settings.FACE_ENROLL_MAX_PER_STUDENT} captures. Remove them to re-enrol.'})
        faces = engine.analyze(_read_image(request))
        if not faces:
            raise ValidationError({'image': 'No face found. Face the camera in good light.'})
        if len(faces) > 1:
            raise ValidationError({'image': 'More than one face found. Only the student should be in view.'})
        face = faces[0]
        if min(face.width, face.height) < settings.FACE_ENROLL_MIN_SIZE:
            raise ValidationError({'image': 'The face is too small. Move closer to the camera.'})
        if face.score < settings.FACE_ENROLL_MIN_SCORE:
            raise ValidationError({'image': 'The face is not clear enough. Check lighting and remove anything covering it.'})

        try:
            blob = encrypt_embedding(face.embedding)
        except ImproperlyConfigured as error:
            raise FaceServiceUnavailable(str(error))
        # Captures made with a different model can never match again; do not keep them.
        student.face_enrollments.exclude(model_name=engine.model_name).delete()
        enrollment = FaceEnrollment.objects.create(
            student=student, embedding=blob, model_name=engine.model_name,
            detection_score=face.score, created_by=request.user,
        )
        record(request, 'enroll_face', student, {'enrollment': enrollment.id})
        return Response(
            {'id': enrollment.id, 'count': current.count(), 'detection_score': round(face.score, 3)},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, pk):
        student = _student_for(request, pk)
        removed, _ = student.face_enrollments.all().delete()
        record(request, 'delete_face_data', student, {'removed': removed})
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecognizeView(APIView):
    """
    Recognise the faces in one frame for an active session and update attendance.
    The frame is processed in memory and not stored.
    """
    permission_classes = [RolePermission]
    write_roles = STAFF_ROLES
    parser_classes = [MultiPartParser]

    def post(self, request, pk):
        session = get_object_or_404(ClassSession.objects.select_related('class_group', 'teacher'), pk=pk)
        if get_role(request.user) == Role.TEACHER and not (session.teacher and session.teacher.user_id == request.user.id):
            raise PermissionDenied('Not your session.')
        if session.status != ClassSession.Status.ACTIVE:
            return Response({'detail': f'Session is {session.status}; start it first.'}, status=status.HTTP_409_CONFLICT)

        engine = _engine()
        faces = engine.analyze(_read_image(request))
        try:
            gallery = gallery_for_class(session.class_group, engine.model_name)
        except ImproperlyConfigured as error:
            raise FaceServiceUnavailable(str(error))
        matches = matcher.match_faces(
            [face.embedding for face in faces], gallery,
            settings.FACE_MATCH_CONFIRM, settings.FACE_MATCH_REVIEW, settings.FACE_MATCH_MARGIN,
        )
        sightings = [
            Sighting(match.student_id, match.band, match.score, match.reason)
            for match in matches if match.student_id is not None
        ]
        changed = record_sightings(session, sightings)

        names = dict(Student.objects.filter(id__in=[s.student_id for s in sightings]).values_list('id', 'full_name'))
        return Response({
            'faces': [
                {
                    'box': face.box,
                    'band': match.band,
                    'student': match.student_id,
                    'student_name': names.get(match.student_id),
                    'score': round(match.score, 3),
                    'reason': match.reason,
                }
                for face, match in zip(faces, matches)
            ],
            'enrolled_students': len(gallery),
            'changed': AttendanceRecordSerializer(changed, many=True).data,
        })


class AttendanceReportView(APIView):
    """
    Attendance totals per student from stored records.
    Filters: class_group, subject, student, date_from, date_to. Add `?export=csv` to download.
    """
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES

    def get(self, request):
        records = AttendanceRecord.objects.all()
        if get_role(request.user) == Role.TEACHER:
            records = records.filter(session__teacher__user=request.user)
        params = request.query_params
        filters = {
            'class_group': 'session__class_group', 'subject': 'session__subject', 'student': 'student',
            'date_from': 'session__date__gte', 'date_to': 'session__date__lte',
        }
        for param, lookup in filters.items():
            if params.get(param):
                records = records.filter(**{lookup: params[param]})

        def tally(value):
            return Count('id', filter=Q(status=value))

        try:
            rows = list(
                records.values('student', 'student__roll_number', 'student__full_name')
                .annotate(
                    sessions=Count('id'),
                    present=tally(AttendanceRecord.Status.PRESENT),
                    late=tally(AttendanceRecord.Status.LATE),
                    left_early=tally(AttendanceRecord.Status.LEFT_EARLY),
                    absent=tally(AttendanceRecord.Status.ABSENT),
                    pending=tally(AttendanceRecord.Status.PENDING),
                )
                .order_by('student__roll_number')
            )
        except (ValueError, TypeError):
            raise ValidationError({'detail': 'A filter value is not valid.'})

        report = []
        for row in rows:
            decided = row['sessions'] - row['pending']
            attended = row['present'] + row['late'] + row['left_early']
            report.append({
                'student': row['student'],
                'roll_number': row['student__roll_number'],
                'full_name': row['student__full_name'],
                'sessions': row['sessions'],
                'present': row['present'],
                'late': row['late'],
                'left_early': row['left_early'],
                'absent': row['absent'],
                'pending': row['pending'],
                # Pending records are excluded until a teacher decides them.
                'attendance_percent': round(100 * attended / decided, 1) if decided else None,
            })

        if params.get('export') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'
            writer = csv.writer(response)
            columns = ['roll_number', 'full_name', 'sessions', 'present', 'late', 'left_early', 'absent', 'pending', 'attendance_percent']
            writer.writerow(['Roll number', 'Name', 'Sessions', 'Present', 'Late', 'Left early', 'Absent', 'Pending review', 'Attendance %'])
            for row in report:
                writer.writerow(['' if row[column] is None else row[column] for column in columns])
            record(request, 'export_attendance_report', request.user, {'rows': len(report), 'filters': dict(params.items())})
            return response
        return Response(report)
