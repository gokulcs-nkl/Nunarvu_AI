"""
Optimized Behavior Analysis Thread with Performance Features
=============================================================

Enhanced version of behavior_thread.py with:
- Frame skipping for reduced processing load
- Resolution adaptation based on CPU load
- Memory pooling for frame buffers
- Adaptive CPU throttling
- Real-time performance monitoring
"""

import threading
import queue
import time
import sys
import os
import numpy as np
import cv2
from datetime import datetime

# Add parent directory to Python path for behavior modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import behavior modules
from behaviour.behavior_analyzer import BehaviorAnalyzer
from behaviour.alert_manager import AlertManager
from behaviour.attention_calculator import AttentionCalculator
from behaviour.db_handler import DatabaseHandler

# Import performance optimization
from .performance_optimizer import (
    AdaptiveOptimizer, get_optimizer, initialize_optimizer
)


class OptimizedBehaviorAnalysisThread:
    """
    Enhanced behavior analysis thread with performance optimization.
    
    Adds frame skipping, resolution adaptation, memory pooling, and
    CPU throttling to the base behavior analysis thread.
    """
    
    def __init__(self, max_queue_size=30, enable_optimization=True):
        """
        Initialize optimized behavior analysis thread.
        
        Parameters:
        -----------
        max_queue_size : int
            Maximum frames in queue before dropping oldest
        enable_optimization : bool
            Enable performance optimization features
        """
        self.max_queue_size = max_queue_size
        self.enable_optimization = enable_optimization
        
        # Frame queue
        self.frame_queue = queue.Queue(maxsize=max_queue_size)
        
        # Control
        self.stop_event = threading.Event()
        self.is_running = False
        
        # Core components
        self.behavior_analyzer = BehaviorAnalyzer(enable_mediapipe=True, frame_skip=1)
        self.alert_manager = AlertManager()
        self.attention_calculator = AttentionCalculator()
        self.db_handler = DatabaseHandler()
        
        # Performance optimization
        if enable_optimization:
            self.optimizer = initialize_optimizer(
                enable_frame_skip=True,
                enable_resolution_adapt=True,
                enable_cpu_throttle=True
            )
        else:
            self.optimizer = None
        
        # Stats
        self.frame_count = 0
        self.processed_frames = 0
        self.skipped_frames = 0
        self.processing_time_avg = 0
        self.last_fps = 0
        self.fps_history = []
        
        # Thread
        self.thread = None
        
        # Logging
        self.last_log_time = time.time()
        self.log_interval = 10.0  # seconds
    
    def start(self):
        """Start optimized behavior analysis thread"""
        if self.is_running:
            print("[OptimizedBehaviorThread] Already running")
            return
        
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.is_running = True
        print("[OptimizedBehaviorThread] Started successfully")
        if self.optimizer:
            print(f"[OptimizedBehaviorThread] Optimization enabled")
    
    def stop(self):
        """Stop optimized behavior analysis thread"""
        if not self.is_running:
            return
        
        self.stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=5.0)
        
        self.is_running = False
        print("[OptimizedBehaviorThread] Stopped")
    
    def put_frame(self, frame, detected_faces=None):
        """
        Add frame to analysis queue with optimization.
        
        Parameters:
        -----------
        frame : np.ndarray
            Video frame (BGR)
        detected_faces : list, optional
            Pre-detected faces from face recognition system
            
        Returns:
        --------
        bool : True if frame was queued, False if queue is full
        """
        try:
            self.frame_count += 1
            
            # Check if frame should be processed (frame skipping)
            if self.optimizer and not self.optimizer.should_process_frame():
                self.skipped_frames += 1
                return True  # Frame dropped silently due to skipping
            
            # Apply resolution optimization if enabled
            if self.optimizer:
                frame = self.optimizer.optimize_frame(frame)
            
            self.processed_frames += 1
            
            # Non-blocking put - drop frame if queue is full
            self.frame_queue.put_nowait({
                'frame': frame,
                'detected_faces': detected_faces,
                'timestamp': time.time()
            })
            return True
        except queue.Full:
            # Queue is full, drop frame silently
            return False
    
    def _run(self):
        """Main optimized thread loop"""
        print("[OptimizedBehaviorThread] Analysis loop started")
        
        try:
            while not self.stop_event.is_set():
                try:
                    # Wait for frame with timeout
                    frame_data = self.frame_queue.get(timeout=1.0)
                    
                    frame = frame_data['frame']
                    detected_faces = frame_data.get('detected_faces', [])
                    
                    if frame is None:
                        continue
                    
                    # Process frame with timing
                    process_start = time.time()
                    result = self._analyze_frame(frame, detected_faces)
                    process_time = time.time() - process_start
                    
                    # Update optimizer metrics
                    if self.optimizer:
                        queue_size = self.frame_queue.qsize()
                        self.optimizer.update_metrics(process_time, queue_size)
                        self.optimizer.adapt_strategy()
                    
                    # Update stats
                    if process_time > 0:
                        fps = 1.0 / process_time
                        self.fps_history.append(fps)
                        if len(self.fps_history) > 30:
                            self.fps_history.pop(0)
                        self.last_fps = np.mean(self.fps_history)
                    
                    # Apply adaptive throttling if enabled
                    if self.optimizer:
                        throttle_delay = self.optimizer.apply_adaptive_throttle()
                        if throttle_delay > 0:
                            time.sleep(throttle_delay)
                    
                    # Periodic logging
                    now = time.time()
                    if now - self.last_log_time > self.log_interval:
                        self._log_performance()
                        self.last_log_time = now
                        
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[OptimizedBehaviorThread] Error processing frame: {e}")
        
        except Exception as e:
            print(f"[OptimizedBehaviorThread] Fatal error: {e}")
        finally:
            print("[OptimizedBehaviorThread] Analysis loop ended")
    
    def _analyze_frame(self, frame, detected_faces=None):
        """
        Analyze frame with all detectors.
        
        Parameters:
        -----------
        frame : np.ndarray
            Video frame to analyze
        detected_faces : list, optional
            Pre-detected faces
            
        Returns:
        --------
        dict : Analysis results
        """
        try:
            # Run behavior analyzer
            behaviors = self.behavior_analyzer.analyze(frame, detected_faces)
            
            # Calculate attention scores
            if behaviors:
                attention_scores = self.attention_calculator.calculate(behaviors)
                
                # Check for alerts
                alerts = self.alert_manager.check_alerts(attention_scores)
                
                # Store in database
                self.db_handler.store_behavior_data(behaviors, attention_scores, alerts)
                
                return {
                    'behaviors': behaviors,
                    'attention_scores': attention_scores,
                    'alerts': alerts,
                    'frame_count': self.frame_count
                }
        except Exception as e:
            print(f"[OptimizedBehaviorThread] Error analyzing frame: {e}")
        
        return None
    
    def _log_performance(self):
        """Log performance metrics."""
        if self.optimizer:
            summary = self.optimizer.get_summary()
            print(f"[OptimizedBehaviorThread] {summary}")
            
            # Log detailed metrics every 30 seconds
            if (self.frame_count % 300) == 0:
                metrics = self.optimizer.get_full_metrics()
                print(f"[OptimizedBehaviorThread] Detailed metrics: {metrics}")
        else:
            print(f"[OptimizedBehaviorThread] Processed: {self.processed_frames} | "
                  f"Skipped: {self.skipped_frames} | FPS: {self.last_fps:.2f}")
    
    def get_performance_stats(self):
        """Get performance statistics."""
        stats = {
            'frames_submitted': self.frame_count,
            'frames_processed': self.processed_frames,
            'frames_skipped': self.skipped_frames,
            'current_fps': round(self.last_fps, 2),
            'queue_size': self.frame_queue.qsize(),
        }
        
        if self.optimizer:
            stats['optimization'] = self.optimizer.get_full_metrics()
        
        return stats
    
    def get_optimization_status(self):
        """Get optimization status and recommendations."""
        if not self.optimizer:
            return {'optimization_enabled': False}
        
        metrics = self.optimizer.get_full_metrics()
        perf = metrics['performance']
        frame_skip = metrics['frame_skipping']
        
        status = {
            'optimization_enabled': True,
            'current_fps': perf['fps'],
            'cpu_percent': perf['cpu_percent'],
            'memory_percent': perf['memory_percent'],
            'frame_skip_rate': frame_skip['skip_rate'],
            'process_ratio': frame_skip['process_ratio'],
            'resolution': metrics['resolution']['current_resolution'],
        }
        
        # Add recommendations
        recommendations = []
        
        if perf['cpu_percent'] > 85:
            recommendations.append("CRITICAL: CPU overload - consider increasing skip rate")
        elif perf['cpu_percent'] > 75:
            recommendations.append("WARNING: High CPU usage - frame skipping may increase")
        
        if perf['memory_percent'] > 80:
            recommendations.append("WARNING: High memory usage - check for memory leaks")
        
        if perf['queue_size'] > 20:
            recommendations.append("WARNING: Frame queue backing up - processing too slow")
        
        if perf['fps'] < 15:
            recommendations.append("WARNING: FPS dropping below 15 - consider increasing skip rate")
        
        status['recommendations'] = recommendations
        return status


# Backward compatibility - maintain original class structure
class BehaviorAnalysisThread(OptimizedBehaviorAnalysisThread):
    """
    Backward compatible wrapper for BehaviorAnalysisThread.
    
    Inherits from OptimizedBehaviorAnalysisThread with optimization enabled by default.
    """
    
    def __init__(self, max_queue_size=30):
        super().__init__(max_queue_size=max_queue_size, enable_optimization=True)


# Global instances
_thread = None
_thread_lock = threading.Lock()


def start_behavior_analysis(max_queue_size=30):
    """Start behavior analysis thread."""
    global _thread
    
    with _thread_lock:
        if _thread is None or not _thread.is_running:
            _thread = OptimizedBehaviorAnalysisThread(max_queue_size=max_queue_size)
            _thread.start()
    
    return _thread


def stop_behavior_analysis():
    """Stop behavior analysis thread."""
    global _thread
    
    with _thread_lock:
        if _thread and _thread.is_running:
            _thread.stop()


def submit_frame_to_analysis(frame, detected_faces=None):
    """Submit frame to analysis queue."""
    global _thread
    
    if _thread and _thread.is_running:
        return _thread.put_frame(frame, detected_faces)
    
    return False


def get_analysis_thread():
    """Get current behavior analysis thread instance."""
    return _thread


def get_performance_stats():
    """Get performance statistics from analysis thread."""
    global _thread
    
    if _thread:
        return _thread.get_performance_stats()
    
    return None


def get_optimization_status():
    """Get optimization status from analysis thread."""
    global _thread
    
    if _thread:
        return _thread.get_optimization_status()
    
    return None
