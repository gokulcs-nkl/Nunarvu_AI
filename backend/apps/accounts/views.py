from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import AuditedModelViewSetMixin
from .models import AuditLog, NotificationPreference
from .permissions import ADMIN_ONLY, RolePermission
from .serializers import AuditLogSerializer, NotificationPreferenceSerializer, UserSerializer

User = get_user_model()


class UserViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    """User and role management (administrators only)."""
    queryset = User.objects.order_by('username')
    serializer_class = UserSerializer
    permission_classes = [RolePermission]
    read_roles = ADMIN_ONLY
    write_roles = ADMIN_ONLY


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('actor')
    serializer_class = AuditLogSerializer
    permission_classes = [RolePermission]
    read_roles = ADMIN_ONLY

    def get_queryset(self):
        queryset = super().get_queryset()
        target_type = self.request.query_params.get('target_type')
        if target_type:
            queryset = queryset.filter(target_type=target_type)
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Current user with effective role."""
    return Response(UserSerializer(request.user).data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
    if request.method == 'PUT':
        serializer = NotificationPreferenceSerializer(preference, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    return Response(NotificationPreferenceSerializer(preference).data)
