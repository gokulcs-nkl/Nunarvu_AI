from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.academics import views as academics
from apps.accounts import auth_views, views as accounts
from apps.attendance import analytics, face_views, views as attendance
from apps.monitoring import views as monitoring

router = DefaultRouter()
router.register('users', accounts.UserViewSet)
router.register('audit-log', accounts.AuditLogViewSet)
router.register('teachers', academics.TeacherViewSet)
router.register('class-groups', academics.ClassGroupViewSet)
router.register('subjects', academics.SubjectViewSet)
router.register('rooms', academics.RoomViewSet)
router.register('students', academics.StudentViewSet)
router.register('enrollments', academics.EnrollmentViewSet)
router.register('periods', academics.PeriodViewSet)
router.register('holidays', academics.HolidayViewSet)
router.register('terms', academics.TermViewSet)
router.register('timetable', academics.TimetableEntryViewSet)
router.register('sessions', academics.ClassSessionViewSet)
router.register('attendance', attendance.AttendanceRecordViewSet)
router.register('cameras', monitoring.CameraViewSet)
router.register('events', monitoring.ClassroomEventViewSet)

urlpatterns = [
    path('auth/csrf/', auth_views.CsrfView.as_view(), name='v1-csrf'),
    path('auth/login/', auth_views.LoginView.as_view(), name='v1-login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='v1-logout'),
    path('me/', accounts.me, name='v1-me'),
    path('me/notifications/', accounts.notification_preferences, name='v1-notification-preferences'),
    path('students/<int:pk>/face-enrollments/', face_views.FaceEnrollmentView.as_view(), name='v1-face-enrollments'),
    path('sessions/<int:pk>/recognize/', face_views.RecognizeView.as_view(), name='v1-recognize'),
    path('reports/attendance/', face_views.AttendanceReportView.as_view(), name='v1-attendance-report'),
    path('reports/summary/', analytics.AttendanceSummaryView.as_view(), name='v1-attendance-summary'),
    path('reports/observations/', analytics.ObservationSummaryView.as_view(), name='v1-observation-summary'),
    path('reports/forecast/', analytics.ForecastView.as_view(), name='v1-forecast'),
    path('reports/risk/', analytics.RiskView.as_view(), name='v1-risk'),
    path('notices/guardian/', analytics.GuardianNoticeView.as_view(), name='v1-guardian-notices'),
    path('reports/participation/', analytics.ParticipationHeatmapView.as_view(), name='v1-participation'),
    path('system/health/', analytics.SystemHealthView.as_view(), name='v1-system-health'),
    path('settings/observations/', monitoring.ObservationSettingsView.as_view(), name='v1-observation-settings'),
    path('compliance/', academics.ComplianceView.as_view(), name='v1-compliance'),
    path('settings/privacy/', academics.PrivacySettingsView.as_view(), name='v1-privacy-settings'),
    path('cameras/<int:pk>/snapshot/', monitoring.CameraSnapshotView.as_view(), name='v1-camera-snapshot'),
    path('cameras/<int:pk>/test/', monitoring.CameraTestView.as_view(), name='v1-camera-test'),
    path('internal/cameras/<int:pk>/state/', monitoring.WorkerStateView.as_view(), name='v1-worker-state'),
    path('internal/cameras/<int:pk>/frame/', monitoring.WorkerFrameView.as_view(), name='v1-worker-frame'),
    path('', include(router.urls)),
]
