"""
Behavior Analysis Thread Module
================================

Runs behavior analysis in a separate thread to avoid blocking video capture.
Processes frames asynchronously from the attendance capture thread.
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


class BehaviorAnalysisThread:
    """
    Manages behavior analysis in a separate thread.
    
    Receives frames from the main capture thread via queue.
    Runs all detectors, calculates attention scores, generates alerts,
    and stores results in database without blocking video capture.
    """
    
    def __init__(self, max_queue_size=30):
        """
        Initialize behavior analysis thread.
        
        Parameters:
        -----------
        max_queue_size : int
            Maximum frames in queue before dropping oldest (default: 30)
        """
        self.max_queue_size = max_queue_size
        
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
        
        # Stats
        self.frame_count = 0
        self.processing_time_avg = 0
        self.last_fps = 0
        self.fps_history = []
        
        # Thread
        self.thread = None
    
    def start(self):
        """Start behavior analysis thread"""
        if self.is_running:
            print("[BehaviorAnalysisThread] Already running")
            return
        
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.is_running = True
        print("[BehaviorAnalysisThread] Started successfully")
    
    def stop(self):
        """Stop behavior analysis thread"""
        if not self.is_running:
            return
        
        self.stop_event.set()
        
        # Wait for thread to finish
        if self.thread:
            self.thread.join(timeout=5.0)
        
        self.is_running = False
        print("[BehaviorAnalysisThread] Stopped")
    
    def put_frame(self, frame, detected_faces=None):
        """
        Add frame to analysis queue.
        
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
            # Non-blocking put - drop frame if queue is full
            self.frame_queue.put_nowait({
                'frame': frame,
                'detected_faces': detected_faces,
                'timestamp': time.time()
            })
            return True
        except queue.Full:
            # Queue is full, drop oldest frame silently
            return False
    
    def _run(self):
        """Main thread loop for behavior analysis"""
        print("[BehaviorAnalysisThread] Analysis loop started")
        
        try:
            while not self.stop_event.is_set():
                try:
                    # Wait for frame with timeout
                    frame_data = self.frame_queue.get(timeout=1.0)
                    
                    frame = frame_data['frame']
                    detected_faces = frame_data.get('detected_faces', [])
                    
                    if frame is None:
                        continue
                    
                    # Process frame
                    process_start = time.time()
                    result = self._analyze_frame(frame, detected_faces)
                    process_time = time.time() - process_start
                    
                    # Update stats
                    self.frame_count += 1
                    if process_time > 0:
                        fps = 1.0 / process_time
                        self.fps_history.append(fps)
                        if len(self.fps_history) > 30:  # Keep last 30 measurements
                            self.fps_history.pop(0)
                        self.last_fps = np.mean(self.fps_history)
                    
                    # Periodic logging
                    if self.frame_count % 60 == 0:  # Log every 60 frames (~2 sec at 30 FPS)
                        print(f"[BehaviorAnalysis] Processed {self.frame_count} frames, "
                              f"Last FPS: {self.last_fps:.1f}, Queue: {self.frame_queue.qsize()}")
                
                except queue.Empty:
                    # No frame available, continue
                    continue
                except Exception as e:
                    print(f"[BehaviorAnalysisThread] Error processing frame: {e}")
                    continue
        
        except Exception as e:
            print(f"[BehaviorAnalysisThread] Fatal error: {e}")
        finally:
            print("[BehaviorAnalysisThread] Analysis loop ended")
    
    def _analyze_frame(self, frame, detected_faces):
        """
        Analyze single frame for behaviors.
        
        Returns analyzed data and stores results in database.
        """
        if frame is None or frame.size == 0:
            return None
        
        try:
            # Convert BGR to RGB for MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Run behavior analyzer
            analysis_result = self.behavior_analyzer.analyze_frame(
                frame,
                detected_faces=detected_faces,
                fps=25  # Assume 25 FPS (can make configurable)
            )
            
            if analysis_result is None:
                return None
            
            # Process results for each student
            for student_id, behaviors in analysis_result['students'].items():
                # Calculate attention score
                attention_result = self.attention_calculator.calculate(behaviors)
                overall_score = attention_result['overall_score']
                component_scores = attention_result['component_scores']
                
                # Get student name from detected faces
                student_name = 'Unknown'
                for face in detected_faces or []:
                    if face.get('student_id') == student_id:
                        student_name = face.get('name', f'Student {student_id}')
                        break
                
                # Store attention score in database
                self.db_handler.update_attention_score(
                    student_id=student_id,
                    drowsiness_score=component_scores.get('drowsiness', 100),
                    head_pose_score=component_scores.get('head_pose', 100),
                    phone_usage_score=component_scores.get('phone_usage', 100),
                    posture_score=component_scores.get('posture', 100),
                    overall_score=overall_score,
                    is_drowsy=behaviors.get('drowsiness', {}).get('is_drowsy', False),
                    is_looking_away=behaviors.get('head_pose', {}).get('is_looking_away', False),
                    is_using_phone=behaviors.get('phone_usage', {}).get('is_using_phone', False),
                    has_bad_posture=behaviors.get('posture', {}).get('has_bad_posture', False)
                )
                
                # Check for critical alerts
                alerts = self.alert_manager.check_behaviors(student_id, student_name, behaviors)
                
                # Store alerts in database
                for alert in alerts:
                    self.db_handler.create_behaviour_alert(
                        student_id=alert['student_id'],
                        alert_type=alert['alert_type'],
                        severity=alert['severity'],
                        duration_in_seconds=alert['duration_in_seconds'],
                        message=alert['message']
                    )
                    print(f"[ALERT] {alert['message']} ({alert['severity']})")
                
                # Store behavior events (optional - sample events for storage efficiency)
                # Store only critical events to avoid database bloat
                if behaviors.get('drowsiness', {}).get('is_drowsy'):
                    self.db_handler.log_behaviour_event(
                        student_id=student_id,
                        event_type='drowsiness',
                        confidence=1.0 - (component_scores.get('drowsiness', 100) / 100),
                        duration=0,  # Duration updated on subsequent detections
                        metadata={'ear': behaviors.get('drowsiness', {}).get('ear', 0)}
                    )
            
            return analysis_result
        
        except Exception as e:
            print(f"[BehaviorAnalysis] Error analyzing frame: {e}")
            return None
    
    def get_stats(self):
        """Get thread statistics"""
        return {
            'is_running': self.is_running,
            'frame_count': self.frame_count,
            'last_fps': self.last_fps,
            'queue_size': self.frame_queue.qsize(),
            'queue_max_size': self.max_queue_size
        }
    
    def reset(self):
        """Reset analyzer and clear queue"""
        # Clear queue
        try:
            while True:
                self.frame_queue.get_nowait()
        except queue.Empty:
            pass
        
        # Reset components
        self.behavior_analyzer.reset()
        self.alert_manager.reset_all()
        self.frame_count = 0
        self.fps_history.clear()
        self.last_fps = 0


# Global thread instance
_behavior_thread_instance = None


def get_behavior_analysis_thread(create_if_missing=True):
    """Get or create global behavior analysis thread instance"""
    global _behavior_thread_instance
    
    if _behavior_thread_instance is None and create_if_missing:
        _behavior_thread_instance = BehaviorAnalysisThread()
    
    return _behavior_thread_instance


def start_behavior_analysis():
    """Start global behavior analysis thread"""
    thread = get_behavior_analysis_thread()
    if thread:
        thread.start()


def stop_behavior_analysis():
    """Stop global behavior analysis thread"""
    global _behavior_thread_instance
    
    if _behavior_thread_instance:
        _behavior_thread_instance.stop()
        _behavior_thread_instance = None


def submit_frame_to_analysis(frame, detected_faces=None):
    """
    Submit frame for behavior analysis.
    
    Parameters:
    -----------
    frame : np.ndarray
        Video frame
    detected_faces : list, optional
        Detected faces from recognition system
        
    Returns:
    --------
    bool : True if frame was queued
    """
    thread = get_behavior_analysis_thread()
    if thread and thread.is_running:
        return thread.put_frame(frame, detected_faces)
    return False
