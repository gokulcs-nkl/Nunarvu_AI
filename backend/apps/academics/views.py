from datetime import date

from django.db.models import ProtectedError, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.audit import AuditedModelViewSetMixin, record
from apps.accounts.models import Role, get_role
from apps.accounts.permissions import ADMIN_ONLY, STAFF_ROLES, RolePermission

from .models import (
    Term,
    ClassGroup, ClassSession, Enrollment, Holiday, Period, Room, Student, Subject, Teacher, TimetableEntry,
)
from .serializers import (
    TermSerializer,
    ClassGroupSerializer, ClassSessionSerializer, EnrollmentSerializer, HolidaySerializer, PeriodSerializer,
    RoomSerializer, StudentSerializer, SubjectSerializer, TeacherSerializer, TimetableEntrySerializer,
)
from .services import generate_sessions_for_date, periods_for_date


def teacher_class_group_ids(user):
    """Class groups a teacher is timetabled for or has taught."""
    return ClassGroup.objects.filter(
        Q(timetable_entries__teacher__user=user) | Q(sessions__teacher__user=user)
    ).values_list('id', flat=True).distinct()


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.select_related('user')
    serializer_class = TeacherSerializer
    permission_classes = [RolePermission]


class ClassGroupViewSet(viewsets.ModelViewSet):
    queryset = ClassGroup.objects.all()
    serializer_class = ClassGroupSerializer
    permission_classes = [RolePermission]


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [RolePermission]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'This subject has sessions or timetable entries and cannot be deleted.'},
                status=status.HTTP_409_CONFLICT,
            )


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [RolePermission]


class StudentViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    """Student profiles. Teachers see only students in their own class groups."""
    queryset = Student.objects.prefetch_related('class_groups')
    serializer_class = StudentSerializer
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if get_role(user) == Role.TEACHER:
            queryset = queryset.filter(class_groups__in=teacher_class_group_ids(user)).distinct()
        params = self.request.query_params
        if params.get('class_group'):
            queryset = queryset.filter(class_groups=params['class_group'])
        if params.get('search'):
            term = params['search']
            queryset = queryset.filter(Q(full_name__icontains=term) | Q(roll_number__icontains=term))
        return queryset


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related('student', 'class_group')
    serializer_class = EnrollmentSerializer
    permission_classes = [RolePermission]
    read_roles = ADMIN_ONLY


class PeriodViewSet(viewsets.ModelViewSet):
    """Bell schedule. `?weekday=` or `?date=` narrows to one scope; `?scope=default` to the default."""
    queryset = Period.objects.all()
    serializer_class = PeriodSerializer
    permission_classes = [RolePermission]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get('scope') == 'default':
            queryset = queryset.filter(weekday__isnull=True, specific_date__isnull=True)
        if params.get('weekday') not in (None, ''):
            queryset = queryset.filter(weekday=params['weekday'])
        if params.get('date'):
            queryset = queryset.filter(specific_date=params['date'])
        return queryset

    @action(detail=False, methods=['get'])
    def effective(self, request):
        """Timings that actually apply on `?date=YYYY-MM-DD` (default: today)."""
        try:
            day = date.fromisoformat(request.query_params['date']) if request.query_params.get('date') else timezone.localdate()
        except ValueError:
            return Response({'date': 'Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PeriodSerializer(periods_for_date(day), many=True).data)

    @action(detail=False, methods=['post'], url_path='copy-day')
    def copy_day(self, request):
        """Replace one weekday's timings with a copy of another weekday's (or the default's)."""
        target = request.data.get('to_weekday')
        source = request.data.get('from_weekday')
        if target is None or int(target) not in range(7):
            return Response({'to_weekday': 'Required, 0 (Monday) to 6 (Sunday).'}, status=status.HTTP_400_BAD_REQUEST)
        if source is None:
            source_periods = Period.objects.filter(weekday__isnull=True, specific_date__isnull=True)
        else:
            source_periods = Period.objects.filter(weekday=int(source))
        source_periods = list(source_periods)
        if not source_periods:
            return Response({'from_weekday': 'No periods to copy.'}, status=status.HTTP_400_BAD_REQUEST)
        Period.objects.filter(weekday=int(target)).delete()
        created = Period.objects.bulk_create([
            Period(number=p.number, name=p.name, weekday=int(target), start_time=p.start_time, end_time=p.end_time)
            for p in source_periods
        ])
        return Response(PeriodSerializer(created, many=True).data, status=status.HTTP_201_CREATED)


class HolidayViewSet(viewsets.ModelViewSet):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [RolePermission]


class TermViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES
    write_roles = ADMIN_ONLY


class TimetableEntryViewSet(viewsets.ModelViewSet):
    queryset = TimetableEntry.objects.select_related('class_group', 'subject', 'teacher', 'room')
    serializer_class = TimetableEntrySerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        class_group = self.request.query_params.get('class_group')
        if class_group:
            queryset = queryset.filter(class_group=class_group)
        return queryset


class ClassSessionViewSet(viewsets.ModelViewSet):
    """Class sessions. Teachers see and manage only their own; they may start manual sessions."""
    queryset = ClassSession.objects.select_related('class_group', 'subject', 'teacher', 'room')
    serializer_class = ClassSessionSerializer
    permission_classes = [RolePermission]
    write_roles = STAFF_ROLES

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if get_role(user) == Role.TEACHER:
            queryset = queryset.filter(teacher__user=user)
        params = self.request.query_params
        for field in ('date', 'class_group', 'subject', 'room', 'status'):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        return queryset

    def perform_create(self, serializer):
        extra = {'source': ClassSession.Source.MANUAL}
        if get_role(self.request.user) == Role.TEACHER:
            extra['teacher'] = Teacher.objects.filter(user=self.request.user).first()
        serializer.save(**extra)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Create timetable sessions for `date` (default: today). Administrators only."""
        if get_role(request.user) != Role.ADMIN:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            day = date.fromisoformat(request.data['date']) if request.data.get('date') else timezone.localdate()
        except ValueError:
            return Response({'date': 'Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'date': day, 'created': generate_sessions_for_date(day)})

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        session = self.get_object()
        if session.status != ClassSession.Status.SCHEDULED:
            return Response({'detail': f'Session is {session.status}.'}, status=status.HTTP_409_CONFLICT)
        session.status = ClassSession.Status.ACTIVE
        session.save(update_fields=['status'])
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        from apps.attendance.services import finalize_session

        session = self.get_object()
        if session.status in (ClassSession.Status.CLOSED, ClassSession.Status.CANCELLED):
            return Response({'detail': f'Session is {session.status}.'}, status=status.HTTP_409_CONFLICT)
        session.status = ClassSession.Status.CLOSED
        if session.ends_at is None:
            session.ends_at = timezone.now()
        session.save(update_fields=['status', 'ends_at'])
        absent = finalize_session(session)
        record(request, 'close_session', session, {'marked_absent': absent})
        return Response(self.get_serializer(session).data)
