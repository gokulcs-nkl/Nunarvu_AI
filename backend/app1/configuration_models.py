"""
Configuration Models for Behavior Analysis System
==================================================

Stores configurable parameters for detectors, thresholds, and optimization strategies.

Models:
- BehaviorConfig - Global behavior detection configuration
- OptimizationConfig - Performance optimization settings
- DetectorConfig - Individual detector parameters
- ThresholdConfig - Alert thresholds
- ConfigurationAudit - Track configuration changes
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime


class BehaviorConfig(models.Model):
    """
    Global configuration for behavior analysis system.
    
    Stores system-wide settings like enable/disable features,
    overall processing modes, and default parameters.
    """
    
    # System Control
    PROCESSING_MODE_CHOICES = [
        ('realtime', 'Real-time'),
        ('batch', 'Batch Processing'),
        ('hybrid', 'Hybrid (Real-time + Batch)'),
    ]
    
    system_enabled = models.BooleanField(
        default=True,
        help_text="Enable/disable entire behavior analysis system"
    )
    
    processing_mode = models.CharField(
        max_length=20,
        choices=PROCESSING_MODE_CHOICES,
        default='realtime',
        help_text="Choose processing mode"
    )
    
    # Frame Processing
    min_fps = models.IntegerField(
        default=15,
        validators=[MinValueValidator(5), MaxValueValidator(60)],
        help_text="Minimum FPS to maintain"
    )
    
    target_fps = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(60)],
        help_text="Target FPS for processing"
    )
    
    # Database
    store_events = models.BooleanField(
        default=True,
        help_text="Store all behavior events in database"
    )
    
    store_scores = models.BooleanField(
        default=True,
        help_text="Store attention scores"
    )
    
    store_alerts = models.BooleanField(
        default=True,
        help_text="Store behavior alerts"
    )
    
    # Notifications
    enable_alerts = models.BooleanField(
        default=True,
        help_text="Enable alert notifications"
    )
    
    alert_via_email = models.BooleanField(
        default=False,
        help_text="Send alerts via email"
    )
    
    alert_via_websocket = models.BooleanField(
        default=True,
        help_text="Send alerts via WebSocket"
    )
    
    # Logging
    log_level = models.CharField(
        max_length=10,
        choices=[
            ('DEBUG', 'Debug'),
            ('INFO', 'Info'),
            ('WARNING', 'Warning'),
            ('ERROR', 'Error'),
        ],
        default='INFO',
        help_text="Logging detail level"
    )
    
    log_to_file = models.BooleanField(
        default=True,
        help_text="Log to file"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    
    class Meta:
        verbose_name = "Behavior System Configuration"
        verbose_name_plural = "Behavior System Configuration"
    
    def __str__(self):
        return f"System Config ({self.processing_mode} mode)"


class OptimizationConfig(models.Model):
    """
    Performance optimization configuration.
    
    Controls frame skipping, resolution adaptation, memory pooling,
    and CPU throttling parameters.
    """
    
    # Frame Skipping
    frame_skip_enabled = models.BooleanField(
        default=True,
        help_text="Enable adaptive frame skipping"
    )
    
    initial_skip_rate = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Initial skip rate (1=no skip, 5=process every 5th frame)"
    )
    
    max_skip_rate = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Maximum skip rate"
    )
    
    # Resolution Adaptation
    resolution_adapt_enabled = models.BooleanField(
        default=True,
        help_text="Enable resolution adaptation based on CPU"
    )
    
    cpu_threshold_low = models.FloatField(
        default=60.0,
        validators=[MinValueValidator(10), MaxValueValidator(90)],
        help_text="Low CPU threshold % (below this = full resolution)"
    )
    
    cpu_threshold_mid = models.FloatField(
        default=75.0,
        validators=[MinValueValidator(10), MaxValueValidator(90)],
        help_text="Mid CPU threshold % (use HD resolution)"
    )
    
    cpu_threshold_high = models.FloatField(
        default=85.0,
        validators=[MinValueValidator(10), MaxValueValidator(95)],
        help_text="High CPU threshold % (use SD resolution)"
    )
    
    # Memory Pooling
    memory_pool_enabled = models.BooleanField(
        default=True,
        help_text="Enable memory pooling for frames"
    )
    
    memory_pool_size = models.IntegerField(
        default=10,
        validators=[MinValueValidator(5), MaxValueValidator(50)],
        help_text="Number of pre-allocated buffers"
    )
    
    # CPU Throttling
    cpu_throttle_enabled = models.BooleanField(
        default=True,
        help_text="Enable CPU throttling"
    )
    
    cpu_throttle_max = models.FloatField(
        default=80.0,
        validators=[MinValueValidator(50), MaxValueValidator(95)],
        help_text="Maximum CPU % before throttling"
    )
    
    # Cache Settings
    cache_enabled = models.BooleanField(
        default=True,
        help_text="Enable query result caching"
    )
    
    cache_ttl_scores = models.IntegerField(
        default=60,
        validators=[MinValueValidator(10), MaxValueValidator(600)],
        help_text="Cache TTL for student scores (seconds)"
    )
    
    cache_ttl_alerts = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(300)],
        help_text="Cache TTL for alerts (seconds)"
    )
    
    cache_ttl_stats = models.IntegerField(
        default=300,
        validators=[MinValueValidator(60), MaxValueValidator(1800)],
        help_text="Cache TTL for statistics (seconds)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='optimization_configs')
    
    class Meta:
        verbose_name = "Optimization Configuration"
        verbose_name_plural = "Optimization Configuration"
    
    def __str__(self):
        return "Optimization Settings"


class DetectorConfig(models.Model):
    """
    Configuration for individual behavior detectors.
    
    Drowsiness, head pose, phone, posture, and absence detectors.
    """
    
    DETECTOR_CHOICES = [
        ('drowsiness', 'Drowsiness Detector'),
        ('head_pose', 'Head Pose Detector'),
        ('phone', 'Phone Detector'),
        ('posture', 'Posture Detector'),
        ('absence', 'Absence Detector'),
    ]
    
    detector_type = models.CharField(
        max_length=20,
        choices=DETECTOR_CHOICES,
        unique=True,
        help_text="Type of detector"
    )
    
    enabled = models.BooleanField(
        default=True,
        help_text="Enable this detector"
    )
    
    # Common parameters
    confidence_threshold = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Confidence threshold for detections (0.0-1.0)"
    )
    
    min_consecutive_frames = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text="Min consecutive frames to confirm detection"
    )
    
    # Drowsiness specific
    eye_aspect_ratio_threshold = models.FloatField(
        default=0.2,
        validators=[MinValueValidator(0.1), MaxValueValidator(0.5)],
        help_text="EAR threshold for drowsiness (0.1-0.5)"
    )
    
    # Head Pose specific
    head_pose_yaw_threshold = models.FloatField(
        default=30.0,
        validators=[MinValueValidator(10), MaxValueValidator(60)],
        help_text="Yaw angle threshold for distraction (degrees)"
    )
    
    head_pose_pitch_threshold = models.FloatField(
        default=30.0,
        validators=[MinValueValidator(10), MaxValueValidator(60)],
        help_text="Pitch angle threshold (degrees)"
    )
    
    # Phone specific
    phone_presence_threshold = models.FloatField(
        default=0.6,
        validators=[MinValueValidator(0.3), MaxValueValidator(0.9)],
        help_text="Confidence threshold for phone detection"
    )
    
    # Posture specific
    posture_confidence_threshold = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.3), MaxValueValidator(0.9)],
        help_text="Confidence threshold for posture detection"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='detector_configs')
    
    class Meta:
        verbose_name = "Detector Configuration"
        verbose_name_plural = "Detector Configurations"
    
    def __str__(self):
        return f"{self.get_detector_type_display()} Config"


class ThresholdConfig(models.Model):
    """
    Alert thresholds for different behavior metrics.
    
    Determines when to generate alerts based on attention scores
    and behavior component values.
    """
    
    ALERT_LEVEL_CHOICES = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('critical', 'Critical'),
    ]
    
    # Overall Attention Score Thresholds
    attention_excellent_threshold = models.FloatField(
        default=85.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score >= this = Excellent"
    )
    
    attention_good_threshold = models.FloatField(
        default=70.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score >= this = Good"
    )
    
    attention_fair_threshold = models.FloatField(
        default=55.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score >= this = Fair"
    )
    
    attention_poor_threshold = models.FloatField(
        default=40.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score >= this = Poor"
    )
    
    # Component Thresholds (0-100 for each)
    drowsiness_alert_threshold = models.FloatField(
        default=60.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Drowsiness score to trigger alert"
    )
    
    phone_usage_alert_threshold = models.FloatField(
        default=70.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Phone usage score to trigger alert"
    )
    
    distraction_alert_threshold = models.FloatField(
        default=65.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Distraction score to trigger alert"
    )
    
    posture_alert_threshold = models.FloatField(
        default=70.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Poor posture score to trigger alert"
    )
    
    absence_alert_threshold = models.FloatField(
        default=80.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Absence score to trigger alert"
    )
    
    # Alert durations (seconds)
    drowsiness_alert_duration = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(300)],
        help_text="Duration threshold for drowsiness alert"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='threshold_configs')
    
    class Meta:
        verbose_name = "Threshold Configuration"
        verbose_name_plural = "Threshold Configuration"
    
    def __str__(self):
        return "Alert Thresholds"


class ConfigurationAudit(models.Model):
    """
    Audit trail for all configuration changes.
    
    Tracks who changed what and when for compliance and debugging.
    """
    
    CONFIG_TYPE_CHOICES = [
        ('system', 'System Config'),
        ('optimization', 'Optimization Config'),
        ('detector', 'Detector Config'),
        ('threshold', 'Threshold Config'),
    ]
    
    config_type = models.CharField(
        max_length=20,
        choices=CONFIG_TYPE_CHOICES,
        help_text="Type of configuration changed"
    )
    
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who made the change"
    )
    
    changed_field = models.CharField(
        max_length=200,
        help_text="Field that was changed"
    )
    
    old_value = models.TextField(
        blank=True,
        help_text="Previous value"
    )
    
    new_value = models.TextField(
        help_text="New value"
    )
    
    reason = models.TextField(
        blank=True,
        help_text="Reason for change"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Configuration Audit"
        verbose_name_plural = "Configuration Audits"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['config_type']),
            models.Index(fields=['changed_by']),
        ]
    
    def __str__(self):
        return f"{self.get_config_type_display()} changed by {self.changed_by} at {self.created_at}"


# Global configuration getters (for easy access)
def get_behavior_config():
    """Get or create default behavior configuration."""
    config, _ = BehaviorConfig.objects.get_or_create(pk=1)
    return config


def get_optimization_config():
    """Get or create default optimization configuration."""
    config, _ = OptimizationConfig.objects.get_or_create(pk=1)
    return config


def get_threshold_config():
    """Get or create default threshold configuration."""
    config, _ = ThresholdConfig.objects.get_or_create(pk=1)
    return config


def get_detector_config(detector_type):
    """Get detector configuration by type."""
    try:
        return DetectorConfig.objects.get(detector_type=detector_type)
    except DetectorConfig.DoesNotExist:
        # Create default config
        config = DetectorConfig.objects.create(detector_type=detector_type)
        return config
