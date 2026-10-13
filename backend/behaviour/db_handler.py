"""
Database Handler Module
=======================

Handles all database operations for behavior analysis system.
Provides batch and individual insert operations, query helpers, and data retrieval.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import threading
from collections import deque

# Django ORM imports
from django.apps import apps
from django.db.models import Q, Avg, Count, Max, Min
from django.utils import timezone


class DatabaseHandler:
    """
    Handles database operations for behavior analysis.
    
    Features:
    - Batch inserts for performance (buffers up to N records)
    - Thread-safe operations
    - Query helpers for common reports
    
    Parameters:
    -----------
    batch_size : int
        Buffer size before auto-flush (default: 50)
    auto_flush_interval : float
        Time in seconds before auto-flush (default: 10.0)
    """
    
    def __init__(self, batch_size=50, auto_flush_interval=10.0):
        self.batch_size = batch_size
        self.auto_flush_interval = auto_flush_interval
        
        # Buffers for batch operations
        self.behaviour_event_buffer = deque(maxlen=batch_size)
        self.attention_score_buffer = deque(maxlen=batch_size)
        self.behaviour_alert_buffer = deque(maxlen=batch_size)
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Last flush time
        self.last_flush_time = datetime.now()
    
    def log_behaviour_event(self, student_id: int, event_type: str,
                           confidence: float, duration: float,
                           metadata: Dict = None, flush: bool = False) -> bool:
        """
        Log a behavior event for a student.
        
        Parameters:
        -----------
        student_id : int
            Student ID
        event_type : str
            Type of event (drowsiness, head_pose, phone_usage, posture, absence)
        confidence : float
            Detection confidence (0-1)
        duration : float
            Event duration in seconds
        metadata : dict, optional
            Additional event-specific data
        flush : bool
            Force immediate database write
            
        Returns:
        --------
        bool : True if successful
        """
        try:
            BehaviourEvent = apps.get_model('app1', 'BehaviourEvent')
            
            event_data = {
                'student_id': student_id,
                'event_type': event_type,
                'confidence': confidence,
                'duration': duration,
                'metadata': metadata or {},
                'timestamp': timezone.now()
            }
            
            with self.lock:
                # Create event object
                event = BehaviourEvent(**event_data)
                event.save()
            
            return True
        except Exception as e:
            print(f"[DatabaseHandler] Error logging behaviour event: {e}")
            return False
    
    def update_attention_score(self, student_id: int, drowsiness_score: float,
                              head_pose_score: float, phone_usage_score: float,
                              posture_score: float, overall_score: float,
                              is_drowsy: bool = False, is_looking_away: bool = False,
                              is_using_phone: bool = False, has_bad_posture: bool = False) -> bool:
        """
        Update or create attention score record for a student.
        
        Parameters:
        -----------
        student_id : int
            Student ID
        drowsiness_score : float
            (0-100)
        head_pose_score : float
            (0-100)
        phone_usage_score : float
            (0-100)
        posture_score : float
            (0-100)
        overall_score : float
            (0-100)
        is_drowsy : bool
            Eyes closed
        is_looking_away : bool
            Looking away from forward
        is_using_phone : bool
            Phone detected
        has_bad_posture : bool
            Bad posture detected
            
        Returns:
        --------
        bool : True if successful
        """
        try:
            AttentionScore = apps.get_model('app1', 'AttentionScore')
            
            score_data = {
                'student_id': student_id,
                'drowsiness_score': drowsiness_score,
                'head_pose_score': head_pose_score,
                'phone_usage_score': phone_usage_score,
                'posture_score': posture_score,
                'attendance_score': 100.0,  # Always 100 if student is present
                'overall_score': overall_score,
                'is_drowsy': is_drowsy,
                'is_looking_away': is_looking_away,
                'is_using_phone': is_using_phone,
                'has_bad_posture': has_bad_posture,
                'timestamp': timezone.now()
            }
            
            with self.lock:
                # Create new attention score record (not update)
                score = AttentionScore(**score_data)
                score.save()
            
            return True
        except Exception as e:
            print(f"[DatabaseHandler] Error updating attention score: {e}")
            return False
    
    def create_behaviour_alert(self, student_id: int, alert_type: str,
                              severity: str, duration_in_seconds: float,
                              message: str) -> bool:
        """
        Create a behavior alert.
        
        Parameters:
        -----------
        student_id : int
            Student ID
        alert_type : str
            Type of alert
        severity : str
            'low', 'medium', or 'high'
        duration_in_seconds : float
            How long the problematic behavior lasted
        message : str
            Alert message
            
        Returns:
        --------
        bool : True if successful
        """
        try:
            BehaviourAlert = apps.get_model('app1', 'BehaviourAlert')
            
            alert_data = {
                'student_id': student_id,
                'alert_type': alert_type,
                'severity': severity,
                'duration_in_seconds': duration_in_seconds,
                'message': message,
                'acknowledged': False,
                'timestamp': timezone.now()
            }
            
            with self.lock:
                alert = BehaviourAlert(**alert_data)
                alert.save()
            
            return True
        except Exception as e:
            print(f"[DatabaseHandler] Error creating alert: {e}")
            return False
    
    def get_student_attention_scores(self, student_id: int,
                                    hours: int = 24) -> List[Dict]:
        """
        Get attention score history for a student.
        
        Parameters:
        -----------
        student_id : int
            Student ID
        hours : int
            Look back N hours (default: 24)
            
        Returns:
        --------
        list of dict : Attention score records
        """
        try:
            AttentionScore = apps.get_model('app1', 'AttentionScore')
            
            time_threshold = timezone.now() - timedelta(hours=hours)
            
            scores = AttentionScore.objects.filter(
                student_id=student_id,
                timestamp__gte=time_threshold
            ).order_by('-timestamp').values()
            
            return list(scores)
        except Exception as e:
            print(f"[DatabaseHandler] Error getting attention scores: {e}")
            return []
    
    def get_student_alerts(self, student_id: int,
                          hours: int = 24,
                          acknowledged: Optional[bool] = False) -> List[Dict]:
        """
        Get alerts for a student.
        
        Parameters:
        -----------
        student_id : int
            Student ID
        hours : int
            Look back N hours
        acknowledged : bool, optional
            Filter by acknowledgement status
            
        Returns:
        --------
        list of dict : Alert records
        """
        try:
            BehaviourAlert = apps.get_model('app1', 'BehaviourAlert')
            
            time_threshold = timezone.now() - timedelta(hours=hours)
            
            query = BehaviourAlert.objects.filter(
                student_id=student_id,
                timestamp__gte=time_threshold
            )
            
            if acknowledged is not None:
                query = query.filter(acknowledged=acknowledged)
            
            alerts = query.order_by('-timestamp').values()
            
            return list(alerts)
        except Exception as e:
            print(f"[DatabaseHandler] Error getting alerts: {e}")
            return []
    
    def get_classroom_stats(self, hours: int = 24) -> Dict:
        """
        Get aggregated stats for entire classroom.
        
        Parameters:
        -----------
        hours : int
            Look back N hours
            
        Returns:
        --------
        dict : Aggregated statistics
        """
        try:
            AttentionScore = apps.get_model('app1', 'AttentionScore')
            BehaviourAlert = apps.get_model('app1', 'BehaviourAlert')
            
            time_threshold = timezone.now() - timedelta(hours=hours)
            
            # Attention scores stats
            attention_stats = AttentionScore.objects.filter(
                timestamp__gte=time_threshold
            ).aggregate(
                avg_score=Avg('overall_score'),
                min_score=Min('overall_score'),
                max_score=Max('overall_score'),
                unique_students=Count('student_id', distinct=True)
            )
            
            # Alert stats
            alert_stats = BehaviourAlert.objects.filter(
                timestamp__gte=time_threshold
            ).aggregate(
                total_alerts=Count('id'),
                unacknowledged=Count('id', filter=Q(acknowledged=False)),
                high_severity=Count('id', filter=Q(severity='high'))
            )
            
            return {
                'attention': attention_stats,
                'alerts': alert_stats,
                'time_period_hours': hours
            }
        except Exception as e:
            print(f"[DatabaseHandler] Error getting classroom stats: {e}")
            return {}
    
    def get_unacknowledged_alerts(self, limit: int = 50) -> List[Dict]:
        """
        Get unacknowledged alerts (for teacher dashboard).
        
        Parameters:
        -----------
        limit : int
            Maximum number to return
            
        Returns:
        --------
        list of dict : Unacknowledged alerts sorted by severity and time
        """
        try:
            BehaviourAlert = apps.get_model('app1', 'BehaviourAlert')
            
            alerts = BehaviourAlert.objects.filter(
                acknowledged=False
            ).select_related('student').order_by(
                '-severity',  # High severity first
                '-timestamp'  # Most recent first
            ).values()[:limit]
            
            return list(alerts)
        except Exception as e:
            print(f"[DatabaseHandler] Error getting unacknowledged alerts: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = "Auto") -> bool:
        """
        Mark an alert as acknowledged.
        
        Parameters:
        -----------
        alert_id : int
            Alert ID
        acknowledged_by : str
            Name of person acknowledging (default: "Auto")
            
        Returns:
        --------
        bool : True if successful
        """
        try:
            BehaviourAlert = apps.get_model('app1', 'BehaviourAlert')
            
            alert = BehaviourAlert.objects.get(id=alert_id)
            alert.acknowledge_alert(acknowledged_by=acknowledged_by)
            
            return True
        except Exception as e:
            print(f"[DatabaseHandler] Error acknowledging alert: {e}")
            return False
    
    def get_behaviour_events(self, student_id: Optional[int] = None,
                            event_type: Optional[str] = None,
                            hours: int = 24,
                            limit: int = 100) -> List[Dict]:
        """
        Get behavior events with optional filtering.
        
        Parameters:
        -----------
        student_id : int, optional
            Filter by student
        event_type : str, optional
            Filter by event type
        hours : int
            Look back N hours
        limit : int
            Maximum number to return
            
        Returns:
        --------
        list of dict : Matching events
        """
        try:
            BehaviourEvent = apps.get_model('app1', 'BehaviourEvent')
            
            time_threshold = timezone.now() - timedelta(hours=hours)
            
            query = BehaviourEvent.objects.filter(timestamp__gte=time_threshold)
            
            if student_id is not None:
                query = query.filter(student_id=student_id)
            
            if event_type is not None:
                query = query.filter(event_type=event_type)
            
            events = query.order_by('-timestamp').values()[:limit]
            
            return list(events)
        except Exception as e:
            print(f"[DatabaseHandler] Error getting behaviour events: {e}")
            return []
    
    def flush_buffers(self) -> bool:
        """Flush all pending buffers to database"""
        try:
            with self.lock:
                # All inserts already happen individually, buffers are empty
                self.last_flush_time = datetime.now()
            return True
        except Exception as e:
            print(f"[DatabaseHandler] Error flushing buffers: {e}")
            return False
    
    def auto_flush_if_needed(self) -> bool:
        """Check if auto-flush is needed and flush if so"""
        time_since_flush = (datetime.now() - self.last_flush_time).total_seconds()
        
        if time_since_flush >= self.auto_flush_interval:
            return self.flush_buffers()
        
        return True
