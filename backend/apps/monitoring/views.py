import hmac
import time

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import BaseParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import AuditedModelViewSetMixin
from apps.accounts.permissions import ADMIN_ONLY, STAFF_ROLES, RolePermission
from vision.capture import open_capture

from . import live
from .models import Camera
from .serializers import CameraSerializer
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
