from django.contrib import admin
from .models import (
    Student, Attendance, CameraConfiguration, ClassroomObjectDetection,
    StudentSeat, BehaviourEvent, AttentionScore, BehaviourAlert, ClassroomSession
)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone_number', 'student_class', 'authorized']
    list_filter = ['student_class', 'authorized']
    search_fields = ['name', 'email']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'check_in_time', 'check_out_time']
    list_filter = ['date']
    search_fields = ['student__name']

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return ['student', 'date', 'check_in_time', 'check_out_time']
        else:  # Adding a new object
            return ['date', 'check_in_time', 'check_out_time']

    def save_model(self, request, obj, form, change):
        if change:  # Editing an existing object
            # Ensure check-in and check-out times cannot be modified via admin
            obj.check_in_time = Attendance.objects.get(id=obj.id).check_in_time
            obj.check_out_time = Attendance.objects.get(id=obj.id).check_out_time
        super().save_model(request, obj, form, change)


@admin.register(CameraConfiguration)
class CameraConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'camera_source', 'threshold']
    search_fields = ['name']


@admin.register(ClassroomObjectDetection)
class ClassroomObjectDetectionAdmin(admin.ModelAdmin):
    list_display = ['object_type', 'date_detected', 'confidence_score', 'camera_configuration']
    list_filter = ['object_type', 'date_detected', 'camera_configuration']
    search_fields = ['notes']
    readonly_fields = ['date_detected', 'confidence_score', 'location_x', 'location_y', 'width', 'height']
    
    fieldsets = (
        ('Detection Information', {
            'fields': ('object_type', 'date_detected', 'confidence_score', 'camera_configuration')
        }),
        ('Location Details', {
            'fields': ('location_x', 'location_y', 'width', 'height')
        }),
        ('Snapshot', {
            'fields': ('image_snapshot',)
        }),
        ('Additional Notes', {
            'fields': ('notes',)
        }),
    )


# ============================================================================
# BEHAVIOUR ANALYSIS ADMIN INTERFACE
# ============================================================================

@admin.register(StudentSeat)
class StudentSeatAdmin(admin.ModelAdmin):
    list_display = ['student', 'classroom_name', 'seat_number', 'created_at']
    list_filter = ['classroom_name']
    search_fields = ['student__name', 'classroom_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Student Assignment', {
            'fields': ('student', 'classroom_name', 'seat_number')
        }),
        ('Position in Frame (Optional)', {
            'fields': ('position_x', 'position_y', 'position_radius'),
            'description': 'X, Y pixel coordinates and search radius for precise seat tracking in video feed'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BehaviourEvent)
class BehaviourEventAdmin(admin.ModelAdmin):
    list_display = ['student', 'event_type', 'timestamp', 'confidence', 'duration']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['student__name']
    readonly_fields = ['timestamp', 'metadata']
    
    fieldsets = (
        ('Event Details', {
            'fields': ('student', 'event_type', 'timestamp', 'confidence', 'duration')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',),
            'description': 'Event-specific data (e.g., Eye Aspect Ratio, head angles, etc.)'
        }),
    )
    
    def has_add_permission(self, request):
        # Events are auto-generated, prevent manual creation
        return False


@admin.register(AttentionScore)
class AttentionScoreAdmin(admin.ModelAdmin):
    list_display = ['student', 'timestamp', 'overall_score', 'is_drowsy', 'is_looking_away', 'is_using_phone']
    list_filter = ['timestamp', 'is_drowsy', 'is_looking_away', 'is_using_phone']
    search_fields = ['student__name']
    readonly_fields = ['timestamp']
    
    fieldsets = (
        ('Student & Timestamp', {
            'fields': ('student', 'timestamp')
        }),
        ('Component Scores', {
            'fields': ('drowsiness_score', 'head_pose_score', 'phone_usage_score', 'posture_score', 'attendance_score', 'overall_score')
        }),
        ('Status Flags', {
            'fields': ('is_drowsy', 'is_looking_away', 'is_using_phone', 'has_bad_posture'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Scores are auto-calculated, prevent manual creation
        return False


@admin.register(BehaviourAlert)
class BehaviourAlertAdmin(admin.ModelAdmin):
    list_display = ['student', 'alert_type', 'severity', 'timestamp', 'acknowledged']
    list_filter = ['alert_type', 'severity', 'acknowledged', 'timestamp']
    search_fields = ['student__name', 'message']
    readonly_fields = ['timestamp']
    
    actions = ['mark_acknowledged']
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('student', 'alert_type', 'severity', 'duration_in_seconds', 'timestamp', 'message')
        }),
        ('Acknowledgement', {
            'fields': ('acknowledged', 'acknowledged_by', 'acknowledged_at'),
            'classes': ('collapse',)
        }),
    )
    
    def mark_acknowledged(self, request, queryset):
        """Admin action to acknowledge multiple alerts"""
        count = 0
        for alert in queryset:
            if not alert.acknowledged:
                alert.acknowledge_alert(acknowledged_by=request.user.username)
                count += 1
        self.message_user(request, f'{count} alert(s) acknowledged.')
    
    mark_acknowledged.short_description = "Mark selected alerts as acknowledged"


@admin.register(ClassroomSession)
class ClassroomSessionAdmin(admin.ModelAdmin):
    list_display = ['classroom_name', 'date', 'start_time', 'end_time', 'is_active', 'total_students_tracked']
    list_filter = ['date', 'classroom_name', 'is_active']
    search_fields = ['classroom_name', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'total_events_logged', 'total_alerts_generated']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('classroom_name', 'camera_configuration', 'date', 'start_time', 'end_time', 'is_active')
        }),
        ('Statistics', {
            'fields': ('total_students_tracked', 'total_events_logged', 'total_alerts_generated'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_session_ended']
    
    def mark_session_ended(self, request, queryset):
        """Admin action to end active sessions"""
        count = 0
        for session in queryset.filter(is_active=True):
            session.mark_ended()
            count += 1
        self.message_user(request, f'{count} session(s) marked as ended.')
    
    mark_session_ended.short_description = "Mark selected sessions as ended"


# ============================================================================
# CONFIGURATION MANAGEMENT ADMIN INTERFACE (Phase 9)
# ============================================================================

from .configuration_admin import (
    BehaviorConfigAdmin,
    OptimizationConfigAdmin,
    DetectorConfigAdmin,
    ThresholdConfigAdmin,
    ConfigurationAuditAdmin,
)
