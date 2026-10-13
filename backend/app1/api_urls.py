from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views
from . import behavior_api_views
from . import configuration_api

# Create router for ViewSets
router = DefaultRouter()
router.register(r'students', api_views.StudentViewSet)
router.register(r'attendance', api_views.AttendanceViewSet)
router.register(r'cameras', api_views.CameraConfigurationViewSet)
router.register(r'object-detection', api_views.ClassroomObjectDetectionViewSet)

# Behavior analysis routes
router.register(r'student-seats', behavior_api_views.StudentSeatViewSet)
router.register(r'behaviour-events', behavior_api_views.BehaviourEventViewSet, basename='behaviour-event')
router.register(r'attention-scores', behavior_api_views.AttentionScoreViewSet, basename='attention-score')
router.register(r'behaviour-alerts', behavior_api_views.BehaviourAlertViewSet, basename='behaviour-alert')
router.register(r'classroom-sessions', behavior_api_views.ClassroomSessionViewSet)
router.register(r'behavior-stats', behavior_api_views.BehaviorStatsViewSet, basename='behavior-stats')

# Configuration management routes (Phase 9)
router.register(r'config/behavior', configuration_api.BehaviorConfigViewSet, basename='behavior-config')
router.register(r'config/optimization', configuration_api.OptimizationConfigViewSet, basename='optimization-config')
router.register(r'config/detectors', configuration_api.DetectorConfigViewSet, basename='detector-config')
router.register(r'config/thresholds', configuration_api.ThresholdConfigViewSet, basename='threshold-config')
router.register(r'config/audit', configuration_api.ConfigurationAuditViewSet, basename='configuration-audit')

# API URL patterns
urlpatterns = [
    # Router URLs (includes all CRUD operations for ViewSets)
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('auth/login/', api_views.login_api, name='api_login'),
    path('auth/logout/', api_views.logout_api, name='api_logout'),
    path('auth/user/', api_views.user_profile, name='api_user_profile'),
    
    # Face recognition API
    path('face-recognition/', api_views.face_recognition_api, name='api_face_recognition'),
    
    # Manual attendance API
    path('manual-attendance/', api_views.manual_attendance_api, name='api_manual_attendance'),
    
    # Health check
    path('health/', api_views.health_check, name='api_health'),
    
    # Camera testing
    path('test-camera/', api_views.test_camera, name='api_test_camera'),
]