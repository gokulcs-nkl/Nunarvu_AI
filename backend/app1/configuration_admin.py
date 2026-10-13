"""
Django Admin Configuration
==========================

Admin interface for managing behavior analysis system configurations.
Provides user-friendly forms and validation for all settings.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from .configuration_models import (
    BehaviorConfig, OptimizationConfig, DetectorConfig,
    ThresholdConfig, ConfigurationAudit
)


@admin.register(BehaviorConfig)
class BehaviorConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for system behavior configuration.
    
    Manages global settings for behavior analysis.
    """
    
    fieldsets = (
        ('System Control', {
            'fields': ('system_enabled', 'processing_mode'),
            'description': 'Control overall system behavior'
        }),
        ('Frame Processing', {
            'fields': ('min_fps', 'target_fps'),
            'description': 'Frame rate and processing settings'
        }),
        ('Database Storage', {
            'fields': ('store_events', 'store_scores', 'store_alerts'),
            'description': 'Choose what data to persist'
        }),
        ('Notifications', {
            'fields': ('enable_alerts', 'alert_via_email', 'alert_via_websocket'),
            'description': 'Alert delivery methods'
        }),
        ('Logging', {
            'fields': ('log_level', 'log_to_file'),
            'description': 'Log detail and storage'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'updated_by')
    list_display = ('get_status', 'processing_mode', 'min_fps', 'target_fps', 'updated_at')
    
    def get_status(self, obj):
        """Display system status with color coding."""
        status_text = "✓ Enabled" if obj.system_enabled else "✗ Disabled"
        color = '#28a745' if obj.system_enabled else '#dc3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status_text
        )
    
    get_status.short_description = 'System Status'
    
    def save_model(self, request, obj, form, change):
        """Track who made changes."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        # Log to audit trail if changed
        if change:
            for field in form.changed_data:
                ConfigurationAudit.objects.create(
                    config_type='system',
                    changed_by=request.user,
                    changed_field=field,
                    new_value=str(getattr(obj, field)),
                    reason='Updated via admin interface'
                )


@admin.register(OptimizationConfig)
class OptimizationConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for performance optimization configuration.
    
    Controls frame skipping, resolution adaptation, memory pooling,
    and CPU throttling parameters.
    """
    
    fieldsets = (
        ('Frame Skipping', {
            'fields': ('frame_skip_enabled', 'initial_skip_rate', 'max_skip_rate'),
            'description': 'Adaptive frame skipping strategy'
        }),
        ('Resolution Adaptation', {
            'fields': ('resolution_adapt_enabled', 'cpu_threshold_low', 'cpu_threshold_mid', 'cpu_threshold_high'),
            'description': 'Dynamic resolution scaling based on CPU load'
        }),
        ('Memory Pooling', {
            'fields': ('memory_pool_enabled', 'memory_pool_size'),
            'description': 'Pre-allocated frame buffers'
        }),
        ('CPU Throttling', {
            'fields': ('cpu_throttle_enabled', 'cpu_throttle_max'),
            'description': 'Maintain stable FPS with throttling'
        }),
        ('Caching', {
            'fields': ('cache_enabled', 'cache_ttl_scores', 'cache_ttl_alerts', 'cache_ttl_stats'),
            'description': 'Query result caching configuration'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'updated_by')
    list_display = ('get_optimization_status', 'frame_skip_enabled', 'resolution_adapt_enabled', 'cpu_throttle_enabled')
    
    def get_optimization_status(self, obj):
        """Show optimization status summary."""
        enabled_count = sum([
            obj.frame_skip_enabled,
            obj.resolution_adapt_enabled,
            obj.memory_pool_enabled,
            obj.cpu_throttle_enabled,
        ])
        return format_html(
            '<span style="background-color: #e8f4f8; padding: 5px 10px; border-radius: 3px;">{}/4 Optimizations Active</span>',
            enabled_count
        )
    
    get_optimization_status.short_description = 'Optimization Status'
    
    def save_model(self, request, obj, form, change):
        """Track configuration changes."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        if change:
            for field in form.changed_data:
                ConfigurationAudit.objects.create(
                    config_type='optimization',
                    changed_by=request.user,
                    changed_field=field,
                    new_value=str(getattr(obj, field)),
                    reason='Updated via admin interface'
                )


@admin.register(DetectorConfig)
class DetectorConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for individual detector configurations.
    
    Manage parameters for each behavior detector.
    """
    
    fieldsets = (
        ('Detector', {
            'fields': ('detector_type', 'enabled'),
        }),
        ('General Parameters', {
            'fields': ('confidence_threshold', 'min_consecutive_frames'),
        }),
        ('Drowsiness Detector', {
            'fields': ('eye_aspect_ratio_threshold',),
            'classes': ('collapse',),
        }),
        ('Head Pose Detector', {
            'fields': ('head_pose_yaw_threshold', 'head_pose_pitch_threshold'),
            'classes': ('collapse',),
        }),
        ('Phone Detector', {
            'fields': ('phone_presence_threshold',),
            'classes': ('collapse',),
        }),
        ('Posture Detector', {
            'fields': ('posture_confidence_threshold',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'updated_by')
    list_display = ('detector_type', 'get_enabled_badge', 'confidence_threshold')
    list_filter = ('detector_type', 'enabled')
    
    def get_enabled_badge(self, obj):
        """Display enabled status as badge."""
        color = '#28a745' if obj.enabled else '#dc3545'
        text = 'Enabled' if obj.enabled else 'Disabled'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            text
        )
    
    get_enabled_badge.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Track configuration changes."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        if change:
            for field in form.changed_data:
                ConfigurationAudit.objects.create(
                    config_type='detector',
                    changed_by=request.user,
                    changed_field=field,
                    new_value=str(getattr(obj, field)),
                    reason=f'Updated {obj.get_detector_type_display()} via admin'
                )


@admin.register(ThresholdConfig)
class ThresholdConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for alert thresholds.
    
    Configure scoring thresholds for attention levels and
    component-specific alert triggers.
    """
    
    fieldsets = (
        ('Overall Attention Score Thresholds', {
            'fields': ('attention_excellent_threshold', 'attention_good_threshold',
                      'attention_fair_threshold', 'attention_poor_threshold'),
            'description': 'Score ranges for attention level classification'
        }),
        ('Component Alert Thresholds', {
            'fields': ('drowsiness_alert_threshold', 'phone_usage_alert_threshold',
                      'distraction_alert_threshold', 'posture_alert_threshold',
                      'absence_alert_threshold'),
            'description': 'Scores that trigger alerts for each component'
        }),
        ('Alert Durations', {
            'fields': ('drowsiness_alert_duration',),
            'description': 'How long a condition must persist to trigger alert'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'updated_by')
    list_display = ('get_threshold_summary',)
    
    def get_threshold_summary(self, obj):
        """Show threshold summary."""
        return format_html(
            'Excellent: {}+ | Good: {}+ | Fair: {}+ | Poor: {}+',
            obj.attention_excellent_threshold,
            obj.attention_good_threshold,
            obj.attention_fair_threshold,
            obj.attention_poor_threshold,
        )
    
    get_threshold_summary.short_description = 'Attention Thresholds'
    
    def save_model(self, request, obj, form, change):
        """Track configuration changes."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        if change:
            for field in form.changed_data:
                ConfigurationAudit.objects.create(
                    config_type='threshold',
                    changed_by=request.user,
                    changed_field=field,
                    new_value=str(getattr(obj, field)),
                    reason='Updated via admin interface'
                )


@admin.register(ConfigurationAudit)
class ConfigurationAuditAdmin(admin.ModelAdmin):
    """
    Admin interface for configuration audit trail.
    
    Read-only view of all configuration changes for compliance.
    """
    
    list_display = ('created_at', 'config_type', 'changed_by', 'changed_field', 'old_value', 'new_value')
    list_filter = ('config_type', 'created_at', 'changed_by')
    search_fields = ('changed_field', 'changed_by__username', 'reason')
    readonly_fields = ('config_type', 'changed_by', 'changed_field', 'old_value', 'new_value', 'reason', 'created_at')
    
    fieldsets = (
        ('Change Information', {
            'fields': ('config_type', 'changed_by', 'changed_field'),
        }),
        ('Values', {
            'fields': ('old_value', 'new_value'),
        }),
        ('Details', {
            'fields': ('reason', 'created_at'),
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual audit entries."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting audit entries."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing audit entries."""
        return False


# Custom admin site configuration
class BehaviorAnalysisAdminSite(admin.AdminSite):
    """Custom admin site for behavior analysis system."""
    
    site_header = 'Behavior Analysis System Administration'
    site_title = 'Behavior Analysis Admin'
    index_title = 'Configuration Management'
    
    def index(self, request, extra_context=None):
        """Custom admin index with system status."""
        extra_context = extra_context or {}
        
        # Add status information
        try:
            behavior_config = BehaviorConfig.objects.first()
            optimization_config = OptimizationConfig.objects.first()
            
            extra_context['system_status'] = {
                'system_enabled': behavior_config.system_enabled if behavior_config else False,
                'processing_mode': behavior_config.processing_mode if behavior_config else 'realtime',
                'optimization_count': sum([
                    optimization_config.frame_skip_enabled,
                    optimization_config.resolution_adapt_enabled,
                    optimization_config.memory_pool_enabled,
                    optimization_config.cpu_throttle_enabled,
                ]) if optimization_config else 0,
            }
        except Exception as e:
            print(f"Error loading admin status: {e}")
        
        return super().index(request, extra_context)
