"""
Performance Optimization Module for Behavior Analysis
======================================================

Implements frame skipping, resolution adaptation, memory pooling,
and CPU throttling to maximize system efficiency and FPS.

Features:
- Frame skipping (process every Nth frame)
- Dynamic resolution adaptation based on CPU load
- Memory pooling to reduce garbage collection overhead
- CPU monitoring and throttling
- Real-time performance metrics collection
- Adaptive processing strategy
"""

import cv2
import numpy as np
import psutil
import threading
import time
from collections import deque
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta


class PerformanceMonitor:
    """
    Real-time performance monitoring and metrics collection.
    
    Tracks CPU usage, memory consumption, frame processing time,
    and provides adaptive recommendations for optimization.
    """
    
    def __init__(self, window_size: int = 30):
        """
        Initialize performance monitor.
        
        Parameters:
        -----------
        window_size : int
            Number of measurements to keep in rolling window
        """
        self.window_size = window_size
        
        # Metrics collections (rolling window)
        self.frame_times = deque(maxlen=window_size)
        self.cpu_usage = deque(maxlen=window_size)
        self.memory_usage = deque(maxlen=window_size)
        self.queue_sizes = deque(maxlen=window_size)
        
        # Current measurements
        self.current_fps = 0
        self.current_cpu = 0
        self.current_memory = 0
        self.current_queue_size = 0
        
        # Statistics
        self.last_update = time.time()
        self.measurements_count = 0
        self.process = psutil.Process()
        
        # Lock for thread-safe access
        self.lock = threading.Lock()
    
    def record_frame_time(self, frame_time: float):
        """Record frame processing time and update FPS."""
        with self.lock:
            self.frame_times.append(frame_time)
            if len(self.frame_times) > 0:
                self.current_fps = 1.0 / np.mean(self.frame_times) if np.mean(self.frame_times) > 0 else 0
            self.measurements_count += 1
    
    def record_cpu_usage(self, cpu_percent: float):
        """Record CPU usage percentage."""
        with self.lock:
            self.cpu_usage.append(cpu_percent)
            self.current_cpu = np.mean(self.cpu_usage) if len(self.cpu_usage) > 0 else 0
    
    def record_memory_usage(self, memory_percent: float):
        """Record memory usage percentage."""
        with self.lock:
            self.memory_usage.append(memory_percent)
            self.current_memory = np.mean(self.memory_usage) if len(self.memory_usage) > 0 else 0
    
    def record_queue_size(self, queue_size: int):
        """Record current queue size."""
        with self.lock:
            self.queue_sizes.append(queue_size)
            self.current_queue_size = int(np.mean(self.queue_sizes)) if len(self.queue_sizes) > 0 else 0
    
    def get_metrics(self) -> Dict:
        """Get current performance metrics."""
        with self.lock:
            return {
                'fps': round(self.current_fps, 2),
                'cpu_percent': round(self.current_cpu, 2),
                'memory_percent': round(self.current_memory, 2),
                'queue_size': self.current_queue_size,
                'total_frames': self.measurements_count,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_status_string(self) -> str:
        """Get human-readable status string."""
        metrics = self.get_metrics()
        return (f"FPS: {metrics['fps']} | CPU: {metrics['cpu_percent']}% | "
                f"Memory: {metrics['memory_percent']}% | Queue: {metrics['queue_size']}")
    
    def is_high_cpu_load(self, threshold: float = 80.0) -> bool:
        """Check if CPU load exceeds threshold."""
        return self.current_cpu > threshold
    
    def is_high_memory_usage(self, threshold: float = 75.0) -> bool:
        """Check if memory usage exceeds threshold."""
        return self.current_memory > threshold
    
    def is_queue_backed_up(self, threshold: int = 20) -> bool:
        """Check if queue size indicates backlog."""
        return self.current_queue_size > threshold
    
    def get_system_metrics(self) -> Dict:
        """Get system metrics (alias for get_metrics for compatibility)."""
        return self.get_metrics()


class FrameSkipManager:
    """
    Manages adaptive frame skipping based on system load.
    
    Dynamically adjusts which frames to process vs skip to maintain
    consistent FPS and prevent queue buildup.
    """
    
    def __init__(self, initial_skip_rate: int = 1, max_skip_rate: int = 5):
        """
        Initialize frame skip manager.
        
        Parameters:
        -----------
        initial_skip_rate : int
            Initial skip rate (1 = process every frame, 2 = skip every 2nd, etc.)
        max_skip_rate : int
            Maximum skip rate to apply
        """
        self.skip_rate = initial_skip_rate
        self.max_skip_rate = max_skip_rate
        self.frame_counter = 0
        self.lock = threading.Lock()
        
        # Statistics
        self.frames_processed = 0
        self.frames_skipped = 0
    
    def should_process_frame(self) -> bool:
        """Determine if current frame should be processed."""
        with self.lock:
            self.frame_counter += 1
            
            if self.frame_counter % self.skip_rate == 0:
                self.frames_processed += 1
                return True
            else:
                self.frames_skipped += 1
                return False
    
    def set_skip_rate(self, skip_rate: int):
        """Set new skip rate (bounded by max)."""
        with self.lock:
            self.skip_rate = min(max(1, skip_rate), self.max_skip_rate)
    
    def increase_skip_rate(self):
        """Increase skip rate (skip more frames)."""
        self.set_skip_rate(self.skip_rate + 1)
    
    def decrease_skip_rate(self):
        """Decrease skip rate (process more frames)."""
        self.set_skip_rate(self.skip_rate - 1)
    
    def get_skip_rate(self) -> int:
        """Get current skip rate."""
        return self.skip_rate
    
    def get_stats(self) -> Dict:
        """Get frame skipping statistics."""
        with self.lock:
            total = self.frames_processed + self.frames_skipped
            return {
                'skip_rate': self.skip_rate,
                'frames_processed': self.frames_processed,
                'frames_skipped': self.frames_skipped,
                'total_frames': total,
                'process_ratio': round(100 * self.frames_processed / max(1, total), 2)
            }


class ResolutionAdapter:
    """
    Dynamically adjusts frame resolution based on CPU load.
    
    Reduces resolution for analysis when CPU is high, maintains
    original resolution for video display.
    """
    
    # Resolution presets: (height, width) -> (description, scale_factor)
    RESOLUTIONS = {
        (1080, 1920): ('Full HD', 1.0),
        (720, 1280): ('HD', 0.67),
        (480, 854): ('SD', 0.44),
        (360, 640): ('Low', 0.33),
    }
    
    def __init__(self, default_resolution: Tuple[int, int] = (480, 854), 
                 cpu_threshold_low: float = 30.0,
                 cpu_threshold_mid: float = 60.0,
                 cpu_threshold_high: float = 85.0):
        """
        Initialize resolution adapter.
        
        Parameters:
        -----------
        default_resolution : tuple
            Default (height, width) for analysis frames
        cpu_threshold_low : float
            CPU threshold for low optimization
        cpu_threshold_mid : float
            CPU threshold for medium optimization
        cpu_threshold_high : float
            CPU threshold for high optimization
        """
        self.current_resolution = default_resolution
        self.default_resolution = default_resolution
        self.scale_factor = 1.0
        self.lock = threading.Lock()
        self.enabled = True
        self.cpu_threshold_low = cpu_threshold_low
        self.cpu_threshold_mid = cpu_threshold_mid
        self.cpu_threshold_high = cpu_threshold_high
        
        # Statistics
        self.resolution_changes = 0
        self.last_change_time = time.time()
    
    def adapt_frame(self, frame: np.ndarray) -> np.ndarray:
        """Resize frame to current resolution."""
        if self.scale_factor >= 1.0:
            return frame  # No need to resize
        
        height, width = int(frame.shape[0] * self.scale_factor), int(frame.shape[1] * self.scale_factor)
        return cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)
    
    def upscale_for_display(self, frame: np.ndarray, target_resolution: Tuple[int, int]) -> np.ndarray:
        """Upscale frame back to original resolution for display."""
        if frame.shape[0] == target_resolution[0]:
            return frame  # Already correct size
        return cv2.resize(frame, (target_resolution[1], target_resolution[0]), interpolation=cv2.INTER_LINEAR)
    
    def set_resolution(self, resolution: Tuple[int, int]):
        """Set analysis resolution."""
        with self.lock:
            height, width = resolution
            # Calculate scale factor
            self.scale_factor = height / 480.0  # Assume base resolution is 480p
            self.current_resolution = resolution
            self.resolution_changes += 1
            self.last_change_time = time.time()
    
    def adapt_to_cpu_load(self, cpu_percent: float):
        """Adapt resolution based on CPU load."""
        if cpu_percent > self.cpu_threshold_high:
            self.set_resolution((360, 640))  # Very low
        elif cpu_percent > self.cpu_threshold_mid:
            self.set_resolution((480, 854))  # Low
        elif cpu_percent > self.cpu_threshold_low:
            self.set_resolution((720, 1280))  # Medium
        else:
            self.set_resolution(self.default_resolution)  # Full
    
    def get_current_resolution(self) -> Tuple[int, int]:
        """Get current resolution."""
        return self.current_resolution
    
    def get_scale_factor(self) -> float:
        """Get current scale factor."""
        return self.scale_factor
    
    def get_stats(self) -> Dict:
        """Get resolution adaptation statistics."""
        with self.lock:
            return {
                'current_resolution': self.current_resolution,
                'scale_factor': round(self.scale_factor, 2),
                'resolution_changes': self.resolution_changes,
                'time_since_change': round(time.time() - self.last_change_time, 2)
            }
    
    def enable(self):
        """Enable resolution adaptation."""
        self.enabled = True
    
    def disable(self):
        """Disable resolution adaptation."""
        self.enabled = False


class MemoryPool:
    """
    Manages reusable frame buffers to reduce memory allocation overhead.
    
    Maintains a pool of pre-allocated numpy arrays that can be reused
    instead of allocating new memory for each frame.
    """
    
    def __init__(self, pool_size: int = 10, frame_shape: Tuple[int, int, int] = (480, 854, 3)):
        """
        Initialize memory pool.
        
        Parameters:
        -----------
        pool_size : int
            Number of buffers to maintain
        frame_shape : tuple
            Shape of each buffer (height, width, channels)
        """
        self.pool_size = pool_size
        self.frame_shape = frame_shape
        
        # Initialize buffer pool
        self.available_buffers = deque(maxlen=pool_size)
        self.used_buffers = set()
        
        for _ in range(pool_size):
            self.available_buffers.append(np.zeros(frame_shape, dtype=np.uint8))
        
        self.lock = threading.Lock()
        
        # Statistics
        self.allocations = 0
        self.deallocations = 0
        self.max_used = 0
    
    def acquire_buffer(self) -> np.ndarray:
        """
        Get a reusable buffer from the pool.
        
        Returns:
        --------
        np.ndarray : Pre-allocated buffer
        """
        with self.lock:
            if len(self.available_buffers) > 0:
                buffer = self.available_buffers.popleft()
            else:
                # Pool exhausted, allocate new buffer
                buffer = np.zeros(self.frame_shape, dtype=np.uint8)
                self.allocations += 1
            
            self.used_buffers.add(id(buffer))
            self.max_used = max(self.max_used, len(self.used_buffers))
            return buffer
    
    def release_buffer(self, buffer: np.ndarray):
        """Return buffer to the pool."""
        with self.lock:
            buffer_id = id(buffer)
            if buffer_id in self.used_buffers:
                self.used_buffers.discard(buffer_id)
                self.deallocations += 1
                
                # Only add back if pool isn't full
                if len(self.available_buffers) < self.pool_size:
                    buffer.fill(0)  # Clear for next use
                    self.available_buffers.append(buffer)
    
    def get_buffer(self) -> np.ndarray:
        """Get a buffer from the pool (alias for acquire_buffer)."""
        return self.acquire_buffer()
    
    def get_stats(self) -> Dict:
        """Get memory pool statistics."""
        with self.lock:
            return {
                'pool_size': self.pool_size,
                'available': len(self.available_buffers),
                'in_use': len(self.used_buffers),
                'allocations': self.allocations,
                'deallocations': self.deallocations,
                'max_concurrent_use': self.max_used
            }


class CPUThrottler:
    """
    Manages CPU throttling to maintain stable frame rates.
    
    Implements exponential backoff when CPU is overloaded and
    scales processing intensity based on available resources.
    """
    
    def __init__(self, target_fps: float = 30.0, max_cpu: float = 80.0):
        """
        Initialize CPU throttler.
        
        Parameters:
        -----------
        target_fps : float
            Target frames per second
        max_cpu : float
            Maximum CPU percentage threshold
        """
        self.target_fps = target_fps
        self.target_frame_time = 1.0 / target_fps
        self.max_cpu = max_cpu
        
        self.current_throttle = 0  # 0 = no throttle, 1.0 = maximum
        self.throttle_duration = 0
        self.lock = threading.Lock()
        self.enabled = True
        
        # Statistics
        self.throttle_events = 0
        self.total_throttle_time = 0
    
    def calculate_throttle_factor(self, cpu_percent: float) -> float:
        """
        Calculate throttle factor based on CPU load.
        
        Returns:
        --------
        float : Throttle factor (0.0 to 1.0)
        """
        if cpu_percent <= self.max_cpu * 0.7:
            return 0.0  # No throttle
        elif cpu_percent <= self.max_cpu * 0.85:
            return (cpu_percent - self.max_cpu * 0.7) / (self.max_cpu * 0.15)  # Linear ramp
        else:
            return 1.0  # Maximum throttle
    
    def apply_throttle(self, cpu_percent: float) -> float:
        """
        Apply throttling based on CPU load.
        
        Returns:
        --------
        float : Delay to apply (in seconds)
        """
        with self.lock:
            throttle_factor = self.calculate_throttle_factor(cpu_percent)
            
            if throttle_factor > 0:
                delay = throttle_factor * self.target_frame_time
                self.throttle_events += 1
                self.total_throttle_time += delay
                return delay
            return 0.0
    
    def set_target_fps(self, fps: float):
        """Set target FPS."""
        self.target_fps = fps
        self.target_frame_time = 1.0 / fps
    
    def get_stats(self) -> Dict:
        """Get throttling statistics."""
        with self.lock:
            return {
                'target_fps': self.target_fps,
                'max_cpu': self.max_cpu,
                'throttle_events': self.throttle_events,
                'total_throttle_time': round(self.total_throttle_time, 2),
                'avg_throttle_per_event': round(
                    self.total_throttle_time / max(1, self.throttle_events), 4
                )
            }
    
    def enable(self):
        """Enable CPU throttling."""
        self.enabled = True
    
    def disable(self):
        """Disable CPU throttling."""
        self.enabled = False


class AdaptiveOptimizer:
    """
    Master optimizer that coordinates all optimization strategies.
    
    Makes decisions about frame skipping, resolution adaptation,
    and throttling based on real-time performance metrics.
    """
    
    def __init__(self, enable_frame_skip: bool = True, 
                 enable_resolution_adapt: bool = True,
                 enable_cpu_throttle: bool = True):
        """
        Initialize adaptive optimizer.
        
        Parameters:
        -----------
        enable_frame_skip : bool
            Enable frame skipping optimization
        enable_resolution_adapt : bool
            Enable resolution adaptation
        enable_cpu_throttle : bool
            Enable CPU throttling
        """
        self.monitor = PerformanceMonitor()
        self.frame_skipper = FrameSkipManager()
        self.resolution_adapter = ResolutionAdapter()
        self.memory_pool = MemoryPool()
        self.cpu_throttler = CPUThrottler()
        
        self.enable_frame_skip = enable_frame_skip
        self.enable_resolution_adapt = enable_resolution_adapt
        self.enable_cpu_throttle = enable_cpu_throttle
        
        # Optimization strategy
        self.last_adaptation_time = time.time()
        self.adaptation_interval = 5.0  # seconds
        
        self.lock = threading.Lock()
    
    def update_metrics(self, frame_time: float, queue_size: int):
        """Update performance metrics."""
        self.monitor.record_frame_time(frame_time)
        self.monitor.record_queue_size(queue_size)
        
        try:
            self.monitor.record_cpu_usage(psutil.cpu_percent(interval=0.01))
            process = psutil.Process()
            memory_info = process.memory_info()
            total_memory = psutil.virtual_memory().total
            memory_percent = (memory_info.rss / total_memory) * 100
            self.monitor.record_memory_usage(memory_percent)
        except Exception as e:
            print(f"[AdaptiveOptimizer] Error reading system metrics: {e}")
    
    def should_process_frame(self) -> bool:
        """Determine if frame should be processed."""
        if not self.enable_frame_skip:
            return True
        return self.frame_skipper.should_process_frame()
    
    def optimize_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply resolution optimization to frame."""
        if not self.enable_resolution_adapt:
            return frame
        return self.resolution_adapter.adapt_frame(frame)
    
    def apply_adaptive_throttle(self) -> float:
        """Apply adaptive CPU throttling."""
        if not self.enable_cpu_throttle:
            return 0.0
        
        metrics = self.monitor.get_metrics()
        return self.cpu_throttler.apply_throttle(metrics['cpu_percent'])
    
    def adapt_strategy(self):
        """
        Adapt optimization strategy based on current metrics.
        Called periodically to adjust parameters.
        """
        now = time.time()
        if now - self.last_adaptation_time < self.adaptation_interval:
            return
        
        self.last_adaptation_time = now
        metrics = self.monitor.get_metrics()
        
        # Adapt resolution
        if self.enable_resolution_adapt:
            self.resolution_adapter.adapt_to_cpu_load(metrics['cpu_percent'])
        
        # Adapt frame skipping
        if self.enable_frame_skip:
            if metrics['queue_size'] > 20:
                self.frame_skipper.increase_skip_rate()
            elif metrics['queue_size'] < 5 and metrics['fps'] > 20:
                self.frame_skipper.decrease_skip_rate()
    
    def get_optimization_status(self) -> Dict:
        """Get current optimization status."""
        return {
            'frame_skip_enabled': self.enable_frame_skip,
            'resolution_adapt_enabled': self.enable_resolution_adapt,
            'cpu_throttle_enabled': self.enable_cpu_throttle,
            'metrics': self.monitor.get_metrics(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_full_metrics(self) -> Dict:
        """Get comprehensive metrics from all components."""
        return {
            'performance': self.monitor.get_metrics(),
            'frame_skipping': self.frame_skipper.get_stats(),
            'resolution': self.resolution_adapter.get_stats(),
            'memory_pool': self.memory_pool.get_stats(),
            'cpu_throttle': self.cpu_throttler.get_stats(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary of optimization state."""
        metrics = self.get_full_metrics()
        perf = metrics['performance']
        frame_skip = metrics['frame_skipping']
        resolution = metrics['resolution']
        
        return (f"[Phase 8 Optimizer] FPS: {perf['fps']} | CPU: {perf['cpu_percent']}% | "
                f"Memory: {perf['memory_percent']}% | Queue: {perf['queue_size']} | "
                f"Skip Rate: {frame_skip['skip_rate']}x | Resolution: {resolution['current_resolution']}")


# Global optimizer instance
_optimizer = None
_optimizer_lock = threading.Lock()


def get_optimizer() -> AdaptiveOptimizer:
    """Get or create global optimizer instance."""
    global _optimizer
    if _optimizer is None:
        with _optimizer_lock:
            if _optimizer is None:
                _optimizer = AdaptiveOptimizer()
    return _optimizer


def initialize_optimizer(enable_frame_skip: bool = True,
                        enable_resolution_adapt: bool = True,
                        enable_cpu_throttle: bool = True) -> AdaptiveOptimizer:
    """Initialize and return global optimizer instance."""
    global _optimizer
    with _optimizer_lock:
        _optimizer = AdaptiveOptimizer(
            enable_frame_skip=enable_frame_skip,
            enable_resolution_adapt=enable_resolution_adapt,
            enable_cpu_throttle=enable_cpu_throttle
        )
    return _optimizer
