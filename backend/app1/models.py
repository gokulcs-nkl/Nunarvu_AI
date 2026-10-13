from django.db import models
from django.utils import timezone

class Student(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=15)
    student_class = models.CharField(max_length=100)
    image = models.ImageField(upload_to='students/')
    authorized = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date', '-check_in_time']

    def __str__(self):
        status = "Checked In" if self.check_in_time and not self.check_out_time else "Checked Out" if self.check_out_time else "Pending"
        return f"{self.student.name} - {self.date} - {status}"

    def mark_checked_in(self):
        self.check_in_time = timezone.now()
        self.save()

    def mark_checked_out(self):
        if self.check_in_time:
            self.check_out_time = timezone.now()
            self.save()
        else:
            raise ValueError("Cannot mark check-out without check-in.")

    def calculate_duration(self):
        if self.check_in_time and self.check_out_time:
            duration = self.check_out_time - self.check_in_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        return None

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            self.date = timezone.now().date()
        super().save(*args, **kwargs)




class CameraConfiguration(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Give a name to this camera configuration")
    camera_source = models.CharField(max_length=255, help_text="Camera index (0 for default webcam or RTSP/HTTP URL for IP camera)")
    threshold = models.FloatField(default=0.6, help_text="Face recognition confidence threshold")

    def __str__(self):
        return self.name

class ClassroomObjectDetection(models.Model):
    """Model to track detected prohibited objects in the classroom"""
    OBJECT_TYPES = [
        ('mobile_phone', 'Mobile Phone'),
        ('laptop', 'Laptop'),
        ('tablet', 'Tablet'),
        ('smartwatch', 'Smartwatch'),
        ('headphones', 'Headphones'),
        ('camera', 'Camera'),
        ('other_gadget', 'Other Electronic Gadget'),
    ]
    
    date_detected = models.DateTimeField(auto_now_add=True)
    object_type = models.CharField(max_length=50, choices=OBJECT_TYPES)
    confidence_score = models.FloatField(default=0.0, help_text="Detection confidence (0-1)")
    camera_configuration = models.ForeignKey(CameraConfiguration, on_delete=models.SET_NULL, null=True, blank=True)
    location_x = models.IntegerField(null=True, blank=True, help_text="X coordinate of detected object")
    location_y = models.IntegerField(null=True, blank=True, help_text="Y coordinate of detected object")
    width = models.IntegerField(null=True, blank=True, help_text="Object bounding box width")
    height = models.IntegerField(null=True, blank=True, help_text="Object bounding box height")
    image_snapshot = models.ImageField(upload_to='detections/', null=True, blank=True, help_text="Snapshot of detected object")
    notes = models.TextField(blank=True, help_text="Additional notes about the detection")

    class Meta:
        ordering = ['-date_detected']

    def __str__(self):
        return f"{self.get_object_type_display()} detected at {self.date_detected.strftime('%Y-%m-%d %H:%M:%S')}"


# ============================================================================
# BEHAVIOUR ANALYSIS MODELS - Real-time classroom monitoring
# ============================================================================

class StudentSeat(models.Model):
    """Assign students to fixed seats in a classroom for accurate position tracking"""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='seat_assignment')
    classroom_name = models.CharField(max_length=100, help_text="e.g., 'Room A101', 'CS Lab 2'")
    seat_number = models.IntegerField(help_text="Seat ID within classroom (1, 2, 3...)")
    # Position in frame (for video-based tracking)
    position_x = models.IntegerField(null=True, blank=True, help_text="Expected X pixel position in classroom camera feed")
    position_y = models.IntegerField(null=True, blank=True, help_text="Expected Y pixel position in classroom camera feed")
    position_radius = models.IntegerField(default=50, help_text="Search radius in pixels for face detection at seat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('classroom_name', 'seat_number')
        ordering = ['classroom_name', 'seat_number']

    def __str__(self):
        return f"{self.student.name} - {self.classroom_name} Seat #{self.seat_number}"


class BehaviourEvent(models.Model):
    """Unified log of all detected behaviour events (drowsiness, head pose, phone usage, posture)"""
    EVENT_TYPES = [
        ('drowsiness', 'Drowsiness Detected'),
        ('head_pose', 'Looking Away'),
        ('phone_usage', 'Phone Usage'),
        ('posture', 'Bad Posture'),
        ('absence', 'Student Absent from Seat'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='behaviour_events')
    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    confidence = models.FloatField(default=0.0, help_text="Detection confidence (0-1)")
    duration = models.FloatField(default=0.0, help_text="Duration of event in seconds")
    
    # Metadata stored as JSON for flexibility
    metadata = models.JSONField(default=dict, blank=True, help_text="Event-specific data (e.g., EAR value, head angles, etc.)")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['student', '-timestamp']),
            models.Index(fields=['event_type', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.get_event_type_display()} at {self.timestamp.strftime('%H:%M:%S')}"


class AttentionScore(models.Model):
    """Real-time attention score for each student (updated every 5 seconds)"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attention_scores')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Component scores (0-100, where 100 = fully attentive)
    drowsiness_score = models.FloatField(default=100.0, help_text="100 = alert, 0 = severely drowsy")
    head_pose_score = models.FloatField(default=100.0, help_text="100 = looking forward, 0 = looking away")
    phone_usage_score = models.FloatField(default=100.0, help_text="100 = no phone, 0 = actively using phone")
    posture_score = models.FloatField(default=100.0, help_text="100 = upright posture, 0 = severely slouched")
    attendance_score = models.FloatField(default=100.0, help_text="100 = continuous presence, 0 = absent")
    
    # Overall weighted attention score
    overall_score = models.FloatField(default=100.0, help_text="Weighted average of all scores (0-100)")
    
    # Component status for quick lookup
    is_drowsy = models.BooleanField(default=False)
    is_looking_away = models.BooleanField(default=False)
    is_using_phone = models.BooleanField(default=False)
    has_bad_posture = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['student', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.student.name} - Attention: {self.overall_score:.1f}% at {self.timestamp.strftime('%H:%M:%S')}"


class BehaviourAlert(models.Model):
    """Critical alerts when behaviour exceeds thresholds"""
    ALERT_TYPES = [
        ('drowsiness', 'Sustained Drowsiness Alert'),
        ('distraction', 'Prolonged Looking Away Alert'),
        ('phone_usage', 'Phone Usage Alert'),
        ('posture', 'Bad Posture Alert'),
        ('absence', 'Sustained Absence Alert'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low - Monitor'),
        ('medium', 'Medium - Attention Needed'),
        ('high', 'High - Immediate Action Required'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='behaviour_alerts')
    timestamp = models.DateTimeField(auto_now_add=True)
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='medium')
    
    # Event details
    duration_in_seconds = models.FloatField(help_text="How long the problematic behaviour lasted")
    message = models.CharField(max_length=255, help_text="Human-readable alert message")
    
    # Tracking
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.CharField(max_length=100, null=True, blank=True, help_text="Teacher/admin name who acknowledged")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['student', '-timestamp']),
            models.Index(fields=['acknowledged', '-timestamp']),
        ]

    def __str__(self):
        status = "✓" if self.acknowledged else "⚠"
        return f"{status} {self.student.name} - {self.get_alert_type_display()} ({self.get_severity_display()})"

    def acknowledge_alert(self, acknowledged_by="Auto"):
        """Mark alert as acknowledged by teacher"""
        self.acknowledged = True
        self.acknowledged_by = acknowledged_by
        self.acknowledged_at = timezone.now()
        self.save()


class ClassroomSession(models.Model):
    """Track recording sessions and bulk behavior analysis runs"""
    classroom_name = models.CharField(max_length=100)
    camera_configuration = models.ForeignKey(CameraConfiguration, on_delete=models.SET_NULL, null=True, blank=True)
    
    date = models.DateField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Session metadata
    total_students_tracked = models.IntegerField(default=0)
    total_events_logged = models.IntegerField(default=0)
    total_alerts_generated = models.IntegerField(default=0)
    
    # Processing details
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Session notes (e.g., special circumstances)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-start_time']
        indexes = [
            models.Index(fields=['date', '-start_time']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        end = self.end_time.strftime('%H:%M') if self.end_time else "Ongoing"
        return f"{self.classroom_name} - {self.date} ({self.start_time.strftime('%H:%M')} - {end})"

    def mark_ended(self):
        """Mark session as ended"""
        self.end_time = timezone.now()
        self.is_active = False
        self.save()
# Import configuration models for Django to recognize them
from .configuration_models import (
    BehaviorConfig,
    OptimizationConfig,
    DetectorConfig,
    ThresholdConfig,
    ConfigurationAudit,
)
