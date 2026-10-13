"""
Configuration Forms
==================

Django forms for configuration management in templates.
"""

from django import forms
from .configuration_models import (
    BehaviorConfig, OptimizationConfig, DetectorConfig,
    ThresholdConfig
)


class BehaviorConfigForm(forms.ModelForm):
    """Form for system behavior configuration."""
    
    class Meta:
        model = BehaviorConfig
        fields = [
            'system_enabled', 'processing_mode',
            'min_fps', 'target_fps',
            'store_events', 'store_scores', 'store_alerts',
            'enable_alerts', 'alert_via_email', 'alert_via_websocket',
            'log_level', 'log_to_file'
        ]
        widgets = {
            'system_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'processing_mode': forms.Select(attrs={'class': 'form-select'}),
            'min_fps': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'max': 60}),
            'target_fps': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'max': 60}),
            'store_events': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'store_scores': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'store_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'alert_via_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'alert_via_websocket': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'log_level': forms.Select(attrs={'class': 'form-select'}),
            'log_to_file': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'system_enabled': 'System Enabled',
            'processing_mode': 'Processing Mode',
            'min_fps': 'Minimum FPS',
            'target_fps': 'Target FPS',
            'store_events': 'Store Behavior Events',
            'store_scores': 'Store Attention Scores',
            'store_alerts': 'Store Alerts',
            'enable_alerts': 'Enable Alerts',
            'alert_via_email': 'Email Notifications',
            'alert_via_websocket': 'WebSocket Notifications',
            'log_level': 'Logging Level',
            'log_to_file': 'Log to File',
        }


class OptimizationConfigForm(forms.ModelForm):
    """Form for optimization configuration."""
    
    OPTIMIZATION_LEVEL_CHOICES = [
        ('conservative', 'Conservative - Minimal optimization'),
        ('balanced', 'Balanced - Default (Recommended)'),
        ('aggressive', 'Aggressive - Maximum optimization'),
    ]
    
    optimization_level = forms.ChoiceField(
        choices=OPTIMIZATION_LEVEL_CHOICES,
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Quick Preset',
        help_text='Choose a preset or customize below'
    )
    
    class Meta:
        model = OptimizationConfig
        fields = [
            'frame_skip_enabled', 'initial_skip_rate', 'max_skip_rate',
            'resolution_adapt_enabled', 'cpu_threshold_low', 'cpu_threshold_mid', 'cpu_threshold_high',
            'memory_pool_enabled', 'memory_pool_size',
            'cpu_throttle_enabled', 'cpu_throttle_max',
            'cache_enabled', 'cache_ttl_scores', 'cache_ttl_alerts', 'cache_ttl_stats'
        ]
        widgets = {
            'frame_skip_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'initial_skip_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'max_skip_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'resolution_adapt_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cpu_threshold_low': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 90, 'step': 5}),
            'cpu_threshold_mid': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 90, 'step': 5}),
            'cpu_threshold_high': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 95, 'step': 5}),
            'memory_pool_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'memory_pool_size': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'max': 50}),
            'cpu_throttle_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cpu_throttle_max': forms.NumberInput(attrs={'class': 'form-control', 'min': 50, 'max': 95, 'step': 5}),
            'cache_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cache_ttl_scores': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 600}),
            'cache_ttl_alerts': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'max': 300}),
            'cache_ttl_stats': forms.NumberInput(attrs={'class': 'form-control', 'min': 60, 'max': 1800}),
        }
        labels = {
            'frame_skip_enabled': 'Enable Frame Skipping',
            'initial_skip_rate': 'Initial Skip Rate',
            'max_skip_rate': 'Maximum Skip Rate',
            'resolution_adapt_enabled': 'Enable Resolution Adaptation',
            'cpu_threshold_low': 'CPU Threshold - Low %',
            'cpu_threshold_mid': 'CPU Threshold - Mid %',
            'cpu_threshold_high': 'CPU Threshold - High %',
            'memory_pool_enabled': 'Enable Memory Pooling',
            'memory_pool_size': 'Memory Pool Size',
            'cpu_throttle_enabled': 'Enable CPU Throttling',
            'cpu_throttle_max': 'Max CPU % for Throttling',
            'cache_enabled': 'Enable Caching',
            'cache_ttl_scores': 'Cache TTL - Scores (seconds)',
            'cache_ttl_alerts': 'Cache TTL - Alerts (seconds)',
            'cache_ttl_stats': 'Cache TTL - Statistics (seconds)',
        }


class DetectorConfigForm(forms.ModelForm):
    """Form for detector configuration."""
    
    class Meta:
        model = DetectorConfig
        fields = [
            'detector_type', 'enabled', 'confidence_threshold', 'min_consecutive_frames',
            'eye_aspect_ratio_threshold', 'head_pose_yaw_threshold', 'head_pose_pitch_threshold',
            'phone_presence_threshold', 'posture_confidence_threshold'
        ]
        widgets = {
            'detector_type': forms.Select(attrs={'class': 'form-select', 'disabled': True}),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'confidence_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.0, 'max': 1.0, 'step': 0.05}),
            'min_consecutive_frames': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
            'eye_aspect_ratio_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.1, 'max': 0.5, 'step': 0.05}),
            'head_pose_yaw_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 60}),
            'head_pose_pitch_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 60}),
            'phone_presence_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.3, 'max': 0.9, 'step': 0.05}),
            'posture_confidence_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.3, 'max': 0.9, 'step': 0.05}),
        }
        labels = {
            'detector_type': 'Detector Type',
            'enabled': 'Enabled',
            'confidence_threshold': 'General Confidence Threshold',
            'min_consecutive_frames': 'Min Consecutive Frames',
            'eye_aspect_ratio_threshold': 'Eye Aspect Ratio Threshold (Drowsiness)',
            'head_pose_yaw_threshold': 'Yaw Threshold (Head Pose)',
            'head_pose_pitch_threshold': 'Pitch Threshold (Head Pose)',
            'phone_presence_threshold': 'Phone Confidence Threshold',
            'posture_confidence_threshold': 'Posture Confidence Threshold',
        }


class ThresholdConfigForm(forms.ModelForm):
    """Form for threshold configuration."""
    
    class Meta:
        model = ThresholdConfig
        fields = [
            'attention_excellent_threshold', 'attention_good_threshold',
            'attention_fair_threshold', 'attention_poor_threshold',
            'drowsiness_alert_threshold', 'phone_usage_alert_threshold',
            'distraction_alert_threshold', 'posture_alert_threshold',
            'absence_alert_threshold', 'drowsiness_alert_duration'
        ]
        widgets = {
            'attention_excellent_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'attention_good_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'attention_fair_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'attention_poor_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'drowsiness_alert_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'phone_usage_alert_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'distraction_alert_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'posture_alert_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'absence_alert_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'drowsiness_alert_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'max': 300}),
        }
        labels = {
            'attention_excellent_threshold': 'Excellent Threshold (≥ score)',
            'attention_good_threshold': 'Good Threshold (≥ score)',
            'attention_fair_threshold': 'Fair Threshold (≥ score)',
            'attention_poor_threshold': 'Poor Threshold (≥ score)',
            'drowsiness_alert_threshold': 'Drowsiness Alert Threshold',
            'phone_usage_alert_threshold': 'Phone Usage Alert Threshold',
            'distraction_alert_threshold': 'Distraction Alert Threshold',
            'posture_alert_threshold': 'Posture Alert Threshold',
            'absence_alert_threshold': 'Absence Alert Threshold',
            'drowsiness_alert_duration': 'Drowsiness Duration for Alert (seconds)',
        }
