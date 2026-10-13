"""
Management command to populate default configuration
"""

from django.core.management.base import BaseCommand
from app1.configuration_models import (
    BehaviorConfig, OptimizationConfig, DetectorConfig,
    ThresholdConfig, ConfigurationAudit,
    get_behavior_config, get_optimization_config, get_threshold_config
)


class Command(BaseCommand):
    help = 'Populate default configuration records'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 Populating default configurations...\n'))
        
        # 1. BehaviorConfig
        try:
            config = get_behavior_config()
            self.stdout.write(self.style.SUCCESS('✓ BehaviorConfig: Default created/loaded'))
            self.stdout.write(f'  - System enabled: {config.system_enabled}')
            self.stdout.write(f'  - Processing mode: {config.processing_mode}')
            self.stdout.write(f'  - Target FPS: {config.target_fps}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ BehaviorConfig error: {e}'))
        
        # 2. OptimizationConfig  
        try:
            config = get_optimization_config()
            self.stdout.write(self.style.SUCCESS('✓ OptimizationConfig: Default created/loaded'))
            self.stdout.write(f'  - Frame skip enabled: {config.frame_skip_enabled}')
            self.stdout.write(f'  - Resolution adapt: {config.resolution_adapt_enabled}')
            self.stdout.write(f'  - Cache enabled: {config.cache_enabled}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ OptimizationConfig error: {e}'))
        
        # 3. DetectorConfig (5 detectors)
        detector_types = [
            ('drowsiness', 'Drowsiness Detection'),
            ('head_pose', 'Head Pose Estimation'),
            ('phone', 'Phone Usage Detection'),
            ('posture', 'Posture Analysis'),
            ('absence', 'Student Absence Detection'),
        ]
        
        for detector_type, display_name in detector_types:
            try:
                config, created = DetectorConfig.objects.get_or_create(
                    detector_type=detector_type,
                    defaults={
                        'enabled': True,
                        'confidence_threshold': 0.7,
                        'min_consecutive_frames': 5,
                    }
                )
                status = '(created)' if created else '(existing)'
                self.stdout.write(self.style.SUCCESS(f'✓ DetectorConfig {display_name}: {status}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ DetectorConfig {display_name} error: {e}'))
        
        # 4. ThresholdConfig
        try:
            config = get_threshold_config()
            self.stdout.write(self.style.SUCCESS('✓ ThresholdConfig: Default created/loaded'))
            self.stdout.write(f'  - Attention excellent: {config.attention_excellent_threshold}%')
            self.stdout.write(f'  - Attention good: {config.attention_good_threshold}%')
            self.stdout.write(f'  - Drowsiness alert: {config.drowsiness_alert_threshold}%')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ ThresholdConfig error: {e}'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Configuration population complete!\n'))
