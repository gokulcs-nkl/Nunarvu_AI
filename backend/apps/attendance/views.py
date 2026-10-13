from rest_framework import viewsets

from apps.accounts.audit import record
from apps.accounts.models import Role, get_role
from apps.accounts.permissions import STAFF_ROLES, RolePermission

from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    """
    Attendance per session. Teachers may mark and correct attendance for their own sessions;
    every manual change is audited.
    """
    queryset = AttendanceRecord.objects.select_related('student', 'session')
    serializer_class = AttendanceRecordSerializer
    permission_classes = [RolePermission]
    write_roles = STAFF_ROLES

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if get_role(user) == Role.TEACHER:
            queryset = queryset.filter(session__teacher__user=user)
        params = self.request.query_params
        for field in ('session', 'student', 'status'):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        if params.get('date'):
            queryset = queryset.filter(session__date=params['date'])
        if params.get('class_group'):
            queryset = queryset.filter(session__class_group=params['class_group'])
        return queryset

    def _check_session_access(self, session):
        user = self.request.user
        if get_role(user) == Role.TEACHER and not (session.teacher and session.teacher.user_id == user.id):
            self.permission_denied(self.request, message='Not your session.')

    def perform_create(self, serializer):
        self._check_session_access(serializer.validated_data['session'])
        instance = serializer.save(source=AttendanceRecord.Source.MANUAL, marked_by=self.request.user)
        record(self.request, 'mark_attendance', instance, {'status': instance.status})

    def perform_update(self, serializer):
        previous = serializer.instance.status
        instance = serializer.save(source=AttendanceRecord.Source.MANUAL, marked_by=self.request.user)
        record(self.request, 'correct_attendance', instance, {'from': previous, 'to': instance.status})

    def perform_destroy(self, instance):
        record(self.request, 'delete_attendance', instance, {'status': instance.status})
        instance.delete()
