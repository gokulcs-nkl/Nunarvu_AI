from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.academics import views as academics
from apps.accounts import auth_views, views as accounts
from apps.attendance import views as attendance
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
router.register('timetable', academics.TimetableEntryViewSet)
router.register('sessions', academics.ClassSessionViewSet)
router.register('attendance', attendance.AttendanceRecordViewSet)
router.register('cameras', monitoring.CameraViewSet)

urlpatterns = [
    path('auth/csrf/', auth_views.CsrfView.as_view(), name='v1-csrf'),
    path('auth/login/', auth_views.LoginView.as_view(), name='v1-login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='v1-logout'),
    path('me/', accounts.me, name='v1-me'),
    path('me/notifications/', accounts.notification_preferences, name='v1-notification-preferences'),
    path('', include(router.urls)),
]
