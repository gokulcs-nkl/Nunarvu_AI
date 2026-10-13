from rest_framework import viewsets

from apps.accounts.audit import AuditedModelViewSetMixin
from apps.accounts.permissions import STAFF_ROLES, RolePermission

from .models import Camera
from .serializers import CameraSerializer


class CameraViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    """Camera devices. Stream URLs can embed credentials, so viewers cannot read them."""
    queryset = Camera.objects.select_related('room')
    serializer_class = CameraSerializer
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES
