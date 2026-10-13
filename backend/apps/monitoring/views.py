import hmac
import time

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import BaseParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import AuditedModelViewSetMixin, record
from apps.accounts.models import Role, get_role
from apps.accounts.permissions import ADMIN_ONLY, STAFF_ROLES, RolePermission
from vision.capture import open_capture

from . import live
from .models import Camera, ClassroomEvent, ObservationSettings
from .serializers import CameraSerializer, ClassroomEventSerializer, ObservationSettingsSerializer
from .worker import encode_preview

MAX_FRAME_BYTES = 2 * 1024 * 1024
TEST_TIMEOUT_SECONDS = 6


class CameraViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    """Camera devices. Stream URLs can embed credentials, so viewers cannot read them."""
    queryset = Camera.objects.select_related('room')
    serializer_class = CameraSerializer
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES


class JpegParser(BaseParser):
    media_type = 'image/jpeg'

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read(MAX_FRAME_BYTES + 1)


def _require_worker(request) -> None:
    token = settings.WORKER_TOKEN
    supplied = request.headers.get('X-Worker-Token', '')
    if not token or not hmac.compare_digest(token, supplied):
        raise PermissionDenied('Invalid worker token.')


class WorkerStateView(APIView):
    """Receives live state from the camera worker and forwards it to connected browsers."""
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk):
        _require_worker(request)
        payload = dict(request.data)
        payload['camera'] = pk
        live.broadcast(payload)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkerFrameView(APIView):
    """Receives a preview frame from the camera worker. Kept in memory only."""
    authentication_classes = []
    permission_classes = []
    parser_classes = [JpegParser]

    def post(self, request, pk):
        _require_worker(request)
        body = request.data
        if not isinstance(body, bytes) or not body or len(body) > MAX_FRAME_BYTES:
            raise ValidationError('Expected a JPEG body of at most 2 MB.')
        live.store_frame(pk, body)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CameraSnapshotView(APIView):
    """Latest preview frame from a running camera worker."""
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES

    def get(self, request, pk):
        get_object_or_404(Camera, pk=pk)
        frame = live.latest_frame(pk)
        if frame is None:
            return Response({'detail': 'No recent frame from this camera.'}, status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(frame, content_type='image/jpeg')
        response['Cache-Control'] = 'no-store'
        return response


class CameraTestView(APIView):
    """
    Check that a camera can deliver a frame. Uses the running worker's latest frame if there is
    one; otherwise opens the camera briefly from the web server.
    """
    permission_classes = [RolePermission]
    write_roles = ADMIN_ONLY

    def post(self, request, pk):
        camera = get_object_or_404(Camera, pk=pk)
        if live.latest_frame(pk) is not None:
            return Response({'ok': True, 'source': 'worker', 'detail': 'The worker is receiving frames from this camera.'})

        capture = None
        try:
            capture = open_capture(camera.source_type, camera.source)
            if capture is None or not capture.isOpened():
                return Response({
                    'ok': False,
                    'detail': 'The camera could not be opened. Check the source and that nothing else is using it.',
                })
            frame = None
            deadline = time.time() + TEST_TIMEOUT_SECONDS
            while time.time() < deadline:
                ok, candidate = capture.read()
                if ok and candidate is not None:
                    frame = candidate
                    break
            if frame is None:
                return Response({'ok': False, 'detail': 'The camera opened but sent no frames.'})
        except Exception as error:  # camera drivers raise assorted errors
            return Response({'ok': False, 'detail': f'The camera failed: {error}'})
        finally:
            if capture is not None:
                capture.release()

        live.store_frame(pk, encode_preview(frame))
        height, width = frame.shape[:2]
        return Response({'ok': True, 'source': 'direct', 'detail': f'Received a {width}x{height} frame.'})


class ClassroomEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Classroom observations. Teachers see events from their own sessions. An event is changed
    only through `review`, which records who confirmed or dismissed it.
    """
    queryset = ClassroomEvent.objects.select_related('student', 'reviewed_by', 'session')
    serializer_class = ClassroomEventSerializer
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES
    write_roles = STAFF_ROLES

    def get_queryset(self):
        queryset = super().get_queryset()
        if get_role(self.request.user) == Role.TEACHER:
            queryset = queryset.filter(session__teacher__user=self.request.user)
        params = self.request.query_params
        for field in ('session', 'kind', 'review_status', 'student'):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        if params.get('date'):
            queryset = queryset.filter(session__date=params['date'])
        return queryset

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        event = self.get_object()
        decision = request.data.get('status')
        if decision not in ClassroomEvent.Review.values:
            raise ValidationError({'status': 'Use confirmed, dismissed or unreviewed.'})
        previous = event.review_status
        event.review_status = decision
        reviewed = decision != ClassroomEvent.Review.UNREVIEWED
        event.reviewed_by = request.user if reviewed else None
        event.reviewed_at = timezone.now() if reviewed else None
        event.save(update_fields=['review_status', 'reviewed_by', 'reviewed_at'])
        record(request, 'review_event', event, {'from': previous, 'to': decision})
        return Response(self.get_serializer(event).data)


class ObservationSettingsView(APIView):
    """Which observations are on and how long each must last. Staff can read; administrators change."""
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES
    write_roles = ADMIN_ONLY

    def get(self, request):
        return Response(ObservationSettingsSerializer(ObservationSettings.load()).data)

    def put(self, request):
        config = ObservationSettings.load()
        serializer = ObservationSettingsSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record(request, 'update_observation_settings', config, {'fields': sorted(serializer.validated_data)})
        return Response(serializer.data)
