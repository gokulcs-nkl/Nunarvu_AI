"""
Behavior Analysis Serializers
==============================

DRF serializers for behavior analysis models.
Used for REST API endpoints.
"""

from rest_framework import serializers
from .models import (
    StudentSeat, BehaviourEvent, AttentionScore,
    BehaviourAlert, ClassroomSession
)
from django.contrib.auth.models import User


class StudentSeatSerializer(serializers.ModelSerializer):
    """Serializer for StudentSeat model"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    
    class Meta:
        model = StudentSeat
        fields = [
            'id', 'student', 'student_name', 'classroom_name', 'seat_number',
            'position_x', 'position_y', 'position_radius', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class BehaviourEventSerializer(serializers.ModelSerializer):
    """Serializer for BehaviourEvent model"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = BehaviourEvent
        fields = [
            'id', 'student', 'student_name', 'timestamp', 'event_type',
            'event_type_display', 'confidence', 'duration', 'metadata'
        ]
        read_only_fields = ['timestamp']


class AttentionScoreSerializer(serializers.ModelSerializer):
    """Serializer for AttentionScore model"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    
    class Meta:
        model = AttentionScore
        fields = [
            'id', 'student', 'student_name', 'timestamp',
            'drowsiness_score', 'head_pose_score', 'phone_usage_score',
            'posture_score', 'attendance_score', 'overall_score',
            'is_drowsy', 'is_looking_away', 'is_using_phone', 'has_bad_posture'
        ]
        read_only_fields = ['timestamp']


class BehaviourAlertSerializer(serializers.ModelSerializer):
    """Serializer for BehaviourAlert model"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = BehaviourAlert
        fields = [
            'id', 'student', 'student_name', 'timestamp', 'alert_type',
            'alert_type_display', 'severity', 'severity_display',
            'duration_in_seconds', 'message', 'acknowledged',
            'acknowledged_by', 'acknowledged_at'
        ]
        read_only_fields = ['timestamp']


class ClassroomSessionSerializer(serializers.ModelSerializer):
    """Serializer for ClassroomSession model"""
    camera_config_name = serializers.CharField(source='camera_configuration.name', read_only=True)
    
    class Meta:
        model = ClassroomSession
        fields = [
            'id', 'classroom_name', 'camera_configuration', 'camera_config_name',
            'date', 'start_time', 'end_time', 'is_active',
            'total_students_tracked', 'total_events_logged',
            'total_alerts_generated', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'total_events_logged', 'total_alerts_generated']


class AttentionSummarySerializer(serializers.Serializer):
    """Serializer for attention score summary"""
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    overall_score = serializers.FloatField()
    level = serializers.CharField()
    drowsiness_score = serializers.FloatField()
    head_pose_score = serializers.FloatField()
    phone_usage_score = serializers.FloatField()
    posture_score = serializers.FloatField()
    is_drowsy = serializers.BooleanField()
    is_looking_away = serializers.BooleanField()
    is_using_phone = serializers.BooleanField()
    has_bad_posture = serializers.BooleanField()
    last_updated = serializers.DateTimeField()


class BehaviorStatsSerializer(serializers.Serializer):
    """Serializer for aggregated behavior statistics"""
    classroom_name = serializers.CharField()
    date = serializers.DateField()
    total_students = serializers.IntegerField()
    avg_attention_score = serializers.FloatField()
    min_attention_score = serializers.FloatField()
    max_attention_score = serializers.FloatField()
    total_alerts = serializers.IntegerField()
    critical_alerts = serializers.IntegerField()
    drowsiness_events = serializers.IntegerField()
    phone_usage_events = serializers.IntegerField()
    distraction_events = serializers.IntegerField()
    posture_events = serializers.IntegerField()


class AlertSummarySerializer(serializers.Serializer):
    """Serializer for alert summary"""
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    alert_type = serializers.CharField()
    severity = serializers.CharField()
    message = serializers.CharField()
    timestamp = serializers.DateTimeField()
    acknowledged = serializers.BooleanField()
    acknowledged_by = serializers.CharField(allow_null=True)
