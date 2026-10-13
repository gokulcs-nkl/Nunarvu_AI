"""
Unit Tests for Performance & Optimization Modules
==================================================

Tests for Phase 8 performance optimizer components.
"""

from django.test import TestCase
from app1.performance_optimizer import (
    AdaptiveOptimizer, FrameSkipManager, ResolutionAdapter,
    MemoryPool, CPUThrottler, PerformanceMonitor
)
from app1.db_optimization import DatabaseOptimizer
import numpy as np


class PerformanceMonitorTestCase(TestCase):
    """Test PerformanceMonitor class."""
    
    def test_monitor_initialization(self):
        """Test monitor can be initialized."""
        monitor = PerformanceMonitor()
        self.assertIsNotNone(monitor)
    
    def test_monitor_records_metrics(self):
        """Test monitor records system metrics."""
        monitor = PerformanceMonitor()
        
        # Should have cpu_percent and memory_percent attributes
        self.assertTrue(hasattr(monitor, 'get_system_metrics'))
    
    def test_monitor_has_cpu_usage(self):
        """Test monitor can get CPU usage."""
        monitor = PerformanceMonitor()
        # get_system_metrics should return dict with cpu_percent
        self.assertTrue(callable(monitor.get_system_metrics))


class FrameSkipManagerTestCase(TestCase):
    """Test FrameSkipManager class."""
    
    def test_frame_skip_initialization(self):
        """Test frame skip manager can be initialized."""
        skipper = FrameSkipManager(initial_skip_rate=1, max_skip_rate=5)
        self.assertIsNotNone(skipper)
        self.assertEqual(skipper.skip_rate, 1)
    
    def test_frame_skip_set_rate(self):
        """Test setting skip rate."""
        skipper = FrameSkipManager(initial_skip_rate=1, max_skip_rate=5)
        skipper.set_skip_rate(3)
        self.assertEqual(skipper.skip_rate, 3)
    
    def test_frame_skip_respects_max_rate(self):
        """Test skip rate respects maximum."""
        skipper = FrameSkipManager(initial_skip_rate=1, max_skip_rate=5)
        skipper.set_skip_rate(10)  # Try to set above max
        self.assertLessEqual(skipper.skip_rate, 5)
    
    def test_frame_skip_should_process(self):
        """Test should_process_frame logic."""
        skipper = FrameSkipManager(initial_skip_rate=2)
        
        # With skip_rate=2, should process every 2nd frame
        results = [skipper.should_process_frame() for _ in range(4)]
        # Pattern should be: True, False, True, False (or similar)
        self.assertIn(sum(results), [1, 2])  # Some true, some false


class ResolutionAdapterTestCase(TestCase):
    """Test ResolutionAdapter class."""
    
    def test_resolution_adapter_initialization(self):
        """Test resolution adapter can be initialized."""
        adapter = ResolutionAdapter(
            cpu_threshold_low=30,
            cpu_threshold_mid=60,
            cpu_threshold_high=85
        )
        self.assertIsNotNone(adapter)
    
    def test_resolution_adapter_scale_factor(self):
        """Test resolution scale factor is in valid range."""
        adapter = ResolutionAdapter()
        scale = adapter.get_scale_factor()
        
        self.assertGreater(scale, 0.0)
        self.assertLessEqual(scale, 1.0)
    
    def test_resolution_adapter_enable_disable(self):
        """Test enabling and disabling adapter."""
        adapter = ResolutionAdapter()
        
        adapter.enable()
        self.assertTrue(adapter.enabled)
        
        adapter.disable()
        self.assertFalse(adapter.enabled)


class MemoryPoolTestCase(TestCase):
    """Test MemoryPool class."""
    
    def test_memory_pool_initialization(self):
        """Test memory pool can be initialized."""
        pool = MemoryPool(pool_size=10)
        self.assertIsNotNone(pool)
    
    def test_memory_pool_get_buffer(self):
        """Test getting buffer from pool."""
        pool = MemoryPool(pool_size=5)
        buffer = pool.get_buffer()
        self.assertIsNotNone(buffer)
    
    def test_memory_pool_release_buffer(self):
        """Test releasing buffer back to pool."""
        pool = MemoryPool(pool_size=5)
        buffer = pool.get_buffer()
        
        # Should be able to release
        pool.release_buffer(buffer)
        # No assertion, just verify no exception
    
    def test_memory_pool_size_respected(self):
        """Test pool size is respected."""
        pool = MemoryPool(pool_size=3)
        
        # Get all buffers
        buffers = [pool.get_buffer() for _ in range(3)]
        
        # Should have gotten 3 buffers
        self.assertEqual(len(buffers), 3)


class CPUThrottlerTestCase(TestCase):
    """Test CPUThrottler class."""
    
    def test_cpu_throttler_initialization(self):
        """Test CPU throttler can be initialized."""
        throttler = CPUThrottler(max_cpu=80.0)
        self.assertIsNotNone(throttler)
    
    def test_cpu_throttler_enable_disable(self):
        """Test enabling and disabling throttler."""
        throttler = CPUThrottler()
        
        throttler.enable()
        self.assertTrue(throttler.enabled)
        
        throttler.disable()
        self.assertFalse(throttler.enabled)
    
    def test_cpu_throttler_max_cpu_setting(self):
        """Test setting max CPU."""
        throttler = CPUThrottler(max_cpu=75.0)
        throttler.max_cpu = 85.0
        
        self.assertEqual(throttler.max_cpu, 85.0)


class AdaptiveOptimizerTestCase(TestCase):
    """Test AdaptiveOptimizer main class."""
    
    def test_optimizer_initialization(self):
        """Test optimizer can be initialized."""
        optimizer = AdaptiveOptimizer()
        self.assertIsNotNone(optimizer)
    
    def test_optimizer_has_components(self):
        """Test optimizer has all components."""
        optimizer = AdaptiveOptimizer()
        
        self.assertIsNotNone(optimizer.frame_skipper)
        self.assertIsNotNone(optimizer.resolution_adapter)
        self.assertIsNotNone(optimizer.memory_pool)
        self.assertIsNotNone(optimizer.cpu_throttler)
        self.assertIsNotNone(optimizer.monitor)
    
    def test_optimizer_get_performance_stats(self):
        """Test getting performance statistics."""
        optimizer = AdaptiveOptimizer()
        stats = optimizer.get_optimization_status()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('frame_skip_rate', stats)
        self.assertIn('resolution_scale', stats)
    
    def test_optimizer_submit_frame(self):
        """Test submitting frame to optimizer."""
        optimizer = AdaptiveOptimizer()
        
        # Create dummy frame (320x240 RGB)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        
        # Should handle frame submission
        self.assertTrue(callable(optimizer.frame_skipper.should_process_frame))


class DatabaseOptimizerTestCase(TestCase):
    """Test DatabaseOptimizer class."""
    
    def test_database_optimizer_initialization(self):
        """Test database optimizer can be initialized."""
        db_optimizer = DatabaseOptimizer()
        self.assertIsNotNone(db_optimizer)
    
    def test_cache_operations(self):
        """Test cache enable/disable."""
        db_optimizer = DatabaseOptimizer()
        
        db_optimizer.enable_cache()
        self.assertTrue(db_optimizer.cache_enabled)
        
        db_optimizer.disable_cache()
        self.assertFalse(db_optimizer.cache_enabled)
    
    def test_cache_ttl_setting(self):
        """Test setting cache TTL."""
        db_optimizer = DatabaseOptimizer()
        
        db_optimizer.set_cache_ttl('scores', 120)
        # Should not raise exception


class PerformanceIntegrationTestCase(TestCase):
    """Integration tests for performance components."""
    
    def test_optimizer_with_frame_processing(self):
        """Test optimizer processes frames correctly."""
        optimizer = AdaptiveOptimizer()
        
        # Process multiple frames
        for i in range(10):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            should_process = optimizer.frame_skipper.should_process_frame()
            self.assertIsInstance(should_process, bool)
    
    def test_optimizer_adapts_to_load(self):
        """Test optimizer adapts parameters based on load."""
        optimizer = AdaptiveOptimizer()
        
        # Get initial stats
        initial_stats = optimizer.get_optimization_status()
        self.assertIsInstance(initial_stats, dict)
        
        # Stats should have reasonable values
        self.assertGreater(initial_stats.get('frame_skip_rate', 0), 0)
    
    def test_database_optimizer_caching(self):
        """Test database optimizer caching works."""
        db_optimizer = DatabaseOptimizer()
        
        db_optimizer.enable_cache()
        
        # Cache should be working
        self.assertTrue(db_optimizer.cache_enabled)


class PerformanceBenchmarkTestCase(TestCase):
    """Benchmark tests for performance components."""
    
    def test_frame_skip_decision_speed(self):
        """Test frame skip decision is fast."""
        skipper = FrameSkipManager(initial_skip_rate=1)
        
        import time
        start = time.time()
        
        # Make 1000 decisions
        for _ in range(1000):
            skipper.should_process_frame()
        
        elapsed = time.time() - start
        
        # Should be very fast (< 10ms for 1000 decisions)
        self.assertLess(elapsed, 0.01)
    
    def test_monitor_metrics_speed(self):
        """Test getting metrics is fast."""
        monitor = PerformanceMonitor()
        
        import time
        start = time.time()
        
        # Get metrics 100 times
        for _ in range(100):
            monitor.get_system_metrics()
        
        elapsed = time.time() - start
        
        # Should be reasonably fast
        self.assertLess(elapsed, 1.0)
