"""
Unit Tests for Configuration Models
====================================

Tests for Phase 9 configuration management models.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from app1.configuration_models import (
    BehaviorConfig, OptimizationConfig, DetectorConfig, ThresholdConfig,
    ConfigurationAudit, get_behavior_config, get_optimization_config,
    get_threshold_config, get_detector_config
)


class BehaviorConfigTestCase(TestCase):
    """Test BehaviorConfig model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_get_behavior_config_creates_default(self):
        """Test that get_behavior_config creates default if missing."""
        # Should auto-create with defaults
        config = get_behavior_config()
        self.assertIsNotNone(config)
        self.assertTrue(config.system_enabled)
        self.assertEqual(config.processing_mode, 'realtime')
    
    def test_behavior_config_field_values(self):
        """Test BehaviorConfig field defaults."""
        config = get_behavior_config()
        
        self.assertTrue(config.system_enabled)
        self.assertEqual(config.min_fps, 15)
        self.assertEqual(config.target_fps, 30)
        self.assertTrue(config.store_events)
        self.assertTrue(config.store_scores)
        self.assertTrue(config.store_alerts)
        self.assertTrue(config.enable_alerts)
        self.assertFalse(config.alert_via_email)
        self.assertTrue(config.alert_via_websocket)
    
    def test_behavior_config_update_tracking(self):
        """Test that updates are tracked with user."""
        config = get_behavior_config()
        config.target_fps = 60
        config.updated_by = self.user
        config.save()
        
        updated = get_behavior_config()
        self.assertEqual(updated.target_fps, 60)
        self.assertEqual(updated.updated_by, self.user)
    
    def test_behavior_config_singleton(self):
        """Test that BehaviorConfig behaves as singleton."""
        config1 = get_behavior_config()
        config1.target_fps = 45
        config1.save()
        
        config2 = get_behavior_config()
        self.assertEqual(config2.target_fps, 45)
        self.assertEqual(config1.id, config2.id)  # Same record


class OptimizationConfigTestCase(TestCase):
    """Test OptimizationConfig model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_get_optimization_config_creates_default(self):
        """Test that get_optimization_config creates default if missing."""
        config = get_optimization_config()
        self.assertIsNotNone(config)
        self.assertTrue(config.frame_skip_enabled)
        self.assertEqual(config.initial_skip_rate, 1)
    
    def test_optimization_config_field_values(self):
        """Test OptimizationConfig field defaults."""
        config = get_optimization_config()
        
        self.assertTrue(config.frame_skip_enabled)
        self.assertEqual(config.initial_skip_rate, 1)
        self.assertEqual(config.max_skip_rate, 5)
        self.assertTrue(config.resolution_adapt_enabled)
        self.assertTrue(config.memory_pool_enabled)
        self.assertEqual(config.memory_pool_size, 10)
        self.assertTrue(config.cpu_throttle_enabled)
        self.assertTrue(config.cache_enabled)
    
    def test_optimization_config_thresholds(self):
        """Test CPU threshold values."""
        config = get_optimization_config()
        
        self.assertLessEqual(config.cpu_threshold_low, config.cpu_threshold_mid)
        self.assertLessEqual(config.cpu_threshold_mid, config.cpu_threshold_high)
    
    def test_optimization_config_cache_ttls(self):
        """Test cache TTL values are positive."""
        config = get_optimization_config()
        
        self.assertGreater(config.cache_ttl_scores, 0)
        self.assertGreater(config.cache_ttl_alerts, 0)
        self.assertGreater(config.cache_ttl_stats, 0)


class DetectorConfigTestCase(TestCase):
    """Test DetectorConfig model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_detector_config_all_types(self):
        """Test that all 5 detector types can be configured."""
        detector_types = ['drowsiness', 'head_pose', 'phone', 'posture', 'absence']
        
        for detector_type in detector_types:
            detector, created = DetectorConfig.objects.get_or_create(
                detector_type=detector_type,
                defaults={'enabled': True, 'updated_by': self.user}
            )
            self.assertIsNotNone(detector)
            self.assertTrue(detector.enabled)
    
    def test_detector_config_confidence_threshold(self):
        """Test detector confidence threshold."""
        detector, _ = DetectorConfig.objects.get_or_create(
            detector_type='drowsiness',
            defaults={'enabled': True, 'updated_by': self.user}
        )
        
        self.assertGreaterEqual(detector.confidence_threshold, 0)
        self.assertLessEqual(detector.confidence_threshold, 1.0)
    
    def test_detector_config_min_frames(self):
        """Test minimum consecutive frames."""
        detector, _ = DetectorConfig.objects.get_or_create(
            detector_type='drowsiness',
            defaults={'enabled': True, 'updated_by': self.user}
        )
        
        self.assertGreaterEqual(detector.min_consecutive_frames, 1)
        self.assertLessEqual(detector.min_consecutive_frames, 100)


class ThresholdConfigTestCase(TestCase):
    """Test ThresholdConfig model."""
    
    def test_get_threshold_config_creates_default(self):
        """Test that get_threshold_config creates default if missing."""
        config = get_threshold_config()
        self.assertIsNotNone(config)
    
    def test_threshold_config_attention_levels(self):
        """Test attention level thresholds are in ascending order."""
        config = get_threshold_config()
        
        self.assertLessEqual(
            config.attention_poor_threshold,
            config.attention_fair_threshold
        )
        self.assertLessEqual(
            config.attention_fair_threshold,
            config.attention_good_threshold
        )
        self.assertLessEqual(
            config.attention_good_threshold,
            config.attention_excellent_threshold
        )
    
    def test_threshold_config_values_in_range(self):
        """Test that alert thresholds are in valid range."""
        config = get_threshold_config()
        
        thresholds = [
            config.drowsiness_alert_threshold,
            config.phone_usage_alert_threshold,
            config.distraction_alert_threshold,
            config.posture_alert_threshold,
            config.absence_alert_threshold,
        ]
        
        for threshold in thresholds:
            self.assertGreaterEqual(threshold, 0)
            self.assertLessEqual(threshold, 100)


class ConfigurationAuditTestCase(TestCase):
    """Test ConfigurationAudit model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_create_audit_record(self):
        """Test creating audit record."""
        audit = ConfigurationAudit.objects.create(
            config_type='optimization',
            changed_by=self.user,
            changed_field='initial_skip_rate',
            old_value='1',
            new_value='2',
            reason='Testing'
        )
        
        self.assertEqual(audit.config_type, 'optimization')
        self.assertEqual(audit.changed_by, self.user)
        self.assertEqual(audit.changed_field, 'initial_skip_rate')
        self.assertEqual(audit.old_value, '1')
        self.assertEqual(audit.new_value, '2')
    
    def test_audit_record_timestamp(self):
        """Test that audit records have timestamps."""
        audit = ConfigurationAudit.objects.create(
            config_type='system',
            changed_by=self.user,
            changed_field='system_enabled',
            old_value='False',
            new_value='True'
        )
        
        self.assertIsNotNone(audit.created_at)
    
    def test_audit_trail_ordering(self):
        """Test that audit records are ordered by timestamp."""
        audit1 = ConfigurationAudit.objects.create(
            config_type='system',
            changed_by=self.user,
            changed_field='field1',
            old_value='1',
            new_value='2'
        )
        
        audit2 = ConfigurationAudit.objects.create(
            config_type='system',
            changed_by=self.user,
            changed_field='field2',
            old_value='a',
            new_value='b'
        )
        
        audits = ConfigurationAudit.objects.all().order_by('-created_at')
        self.assertEqual(audits.first().id, audit2.id)
        self.assertEqual(audits.last().id, audit1.id)
    
    def test_audit_by_config_type(self):
        """Test filtering audit records by config type."""
        ConfigurationAudit.objects.create(
            config_type='system',
            changed_by=self.user,
            changed_field='field1',
            old_value='1',
            new_value='2'
        )
        
        ConfigurationAudit.objects.create(
            config_type='optimization',
            changed_by=self.user,
            changed_field='field2',
            old_value='a',
            new_value='b'
        )
        
        system_audits = ConfigurationAudit.objects.filter(config_type='system')
        self.assertEqual(system_audits.count(), 1)
        
        opt_audits = ConfigurationAudit.objects.filter(config_type='optimization')
        self.assertEqual(opt_audits.count(), 1)


class HelperFunctionsTestCase(TestCase):
    """Test helper functions."""
    
    def test_get_behavior_config_idempotent(self):
        """Test that get_behavior_config is idempotent."""
        config1 = get_behavior_config()
        config2 = get_behavior_config()
        self.assertEqual(config1.id, config2.id)
    
    def test_get_optimization_config_idempotent(self):
        """Test that get_optimization_config is idempotent."""
        config1 = get_optimization_config()
        config2 = get_optimization_config()
        self.assertEqual(config1.id, config2.id)
    
    def test_get_threshold_config_idempotent(self):
        """Test that get_threshold_config is idempotent."""
        config1 = get_threshold_config()
        config2 = get_threshold_config()
        self.assertEqual(config1.id, config2.id)
    
    def test_get_detector_config_by_type(self):
        """Test getting detector config by type."""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        detector = DetectorConfig.objects.create(
            detector_type='drowsiness',
            enabled=True,
            updated_by=user
        )
        
        retrieved = get_detector_config('drowsiness')
        self.assertEqual(retrieved.id, detector.id)
    
    def test_get_detector_config_creates_if_missing(self):
        """Test that get_detector_config creates if missing."""
        # This depends on implementation - adjust based on your code
        detector = get_detector_config('phone')
        self.assertIsNotNone(detector)
        self.assertEqual(detector.detector_type, 'phone')
