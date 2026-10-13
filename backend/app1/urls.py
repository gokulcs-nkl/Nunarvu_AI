from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),  # Landing page
    path('login/', views.user_login, name='login'),  # Login page
    path('capture_student/', views.capture_student, name='capture_student'),
    path('home/', views.advanced_dashboard, name='home'),  # Main dashboard
    path('selfie-success/', views.selfie_success, name='selfie_success'),
    path('capture-and-recognize/', views.capture_and_recognize, name='capture_and_recognize'),
    path('process-face-recognition/', views.process_face_recognition, name='process_face_recognition'),
    path('manual-check-in-out/', views.manual_check_in_out, name='manual_check_in_out'),
    path('students/attendance/', views.student_attendance_list, name='student_attendance_list'),
    path('students/attendance/export/', views.export_attendance_csv, name='export_attendance_csv'),
    path('object-detection-report/', views.object_detection_report, name='object_detection_report'),
    path('students/', views.student_list, name='manage-student-list'),
    path('students/<int:pk>/', views.student_detail, name='manage-student-detail'),
    path('students/<int:pk>/authorize/', views.student_authorize, name='manage-student-authorize'),
    path('students/<int:pk>/delete/', views.student_delete, name='manage-student-delete'),
    path('logout/', views.user_logout, name='logout'),
    path('camera-config/', views.camera_configuration, name='camera_configuration'),
    path('attendance-flow-documentation/', views.attendance_flow_documentation, name='attendance_flow_documentation'),
    path('start-video-analysis/', views.start_video_analysis, name='start_video_analysis'),
    path('camera-config-old/', views.camera_config_create, name='camera_config_create'),
    path('camera-config-old/list/', views.camera_config_list, name='camera_config_list'),
    path('camera-config-old/update/<int:pk>/', views.camera_config_update, name='camera_config_update'),
    path('camera-config-old/delete/<int:pk>/', views.camera_config_delete, name='camera_config_delete'),
    path('dashboard/', views.advanced_dashboard, name='advanced_dashboard'),
    
    # Behavior Analysis Dashboard URLs
    path('', include('app1.behavior_dashboard_urls')),
]