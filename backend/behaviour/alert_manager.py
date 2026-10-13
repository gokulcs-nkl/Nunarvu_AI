"""
Alert Manager Module
====================

Manages behavior alerts based on thresholds.
Generates critical alerts when behaviors exceed configured limits.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json


class AlertManager:
    """
    Monitors behavior events and generates alerts when thresholds are exceeded.
    
    Alert Thresholds:
    - Sustained Drowsiness: >10 seconds
    - Prolonged Looking Away: >25 seconds
    - Phone Usage: >5 seconds continuous
    - Bad Posture: >15 seconds continuous
    - Sustained Absence: >30 seconds
    
    Parameters:
    -----------
    drowsiness_threshold : float
        Duration in seconds (default: 10.0)
    looking_away_threshold : float
        Duration in seconds (default: 25.0)
    phone_usage_threshold : float
        Duration in seconds (default: 5.0)
    posture_threshold : float
        Duration in seconds (default: 15.0)
    absence_threshold : float
        Duration in seconds (default: 30.0)
    """
    
    ALERT_TYPES = {
        'drowsiness': 'Sustained Drowsiness Alert',
        'distraction': 'Prolonged Looking Away Alert',
        'phone_usage': 'Phone Usage Alert',
        'posture': 'Bad Posture Alert',
        'absence': 'Sustained Absence Alert'
    }
    
    SEVERITY_LEVELS = {
        'low': 'Low - Monitor',
        'medium': 'Medium - Attention Needed',
        'high': 'High - Immediate Action Required'
    }
    
    def __init__(self, drowsiness_threshold=10.0, looking_away_threshold=25.0,
                 phone_usage_threshold=5.0, posture_threshold=15.0,
                 absence_threshold=30.0):
        self.drowsiness_threshold = drowsiness_threshold
        self.looking_away_threshold = looking_away_threshold
        self.phone_usage_threshold = phone_usage_threshold
        self.posture_threshold = posture_threshold
        self.absence_threshold = absence_threshold
        
        # Track ongoing alerts per student
        self.ongoing_alerts = {}  # {student_id: {alert_type: {'start_time': float, 'last_reported': float}}}
        
        # History of generated alerts
        self.alert_history = []
        self.max_history_size = 10000  # Keep last 10k alerts in memory
    
    def check_behaviors(self, student_id: int, student_name: str, behaviors: Dict) -> List[Dict]:
        """
        Check student behaviors against thresholds and generate alerts.
        
        Parameters:
        -----------
        student_id : int
            Student ID
        student_name : str
            Student name
        behaviors : dict
            Behavior data with scores and durations
            
        Returns:
        --------
        list of dict : Generated critical alerts
            [{
                'alert_type': str,
                'severity': str,
                'student_id': int,
                'student_name': str,
                'duration': float,
                'message': str,
                'timestamp': float
            }, ...]
        """
        alerts = []
        current_time = time.time()
        
        # Initialize student tracking if needed
        if student_id not in self.ongoing_alerts:
            self.ongoing_alerts[student_id] = {}
        
        # Check drowsiness
        drowsiness_result = behaviors.get('drowsiness', {})
        if drowsiness_result.get('is_drowsy'):
            alert = self._check_sustained_behavior(
                student_id, student_name, 'drowsiness',
                self.drowsiness_threshold, 'high',
                f"Student {student_name} is drowsy (eyes closed)",
                current_time
            )
            if alert:
                alerts.append(alert)
        else:
            # Clear ongoing drowsiness alert if eyes are open
            self._clear_ongoing_alert(student_id, 'drowsiness')
        
        # Check head pose (looking away)
        head_pose_result = behaviors.get('head_pose', {})
        if head_pose_result.get('is_looking_away'):
            looking_away_duration = head_pose_result.get('looking_away_duration', 0)
            direction = head_pose_result.get('looking_direction', 'unknown')
            
            alert = self._check_sustained_behavior(
                student_id, student_name, 'distraction',
                self.looking_away_threshold, 'medium',
                f"Student {student_name} looking {direction} for {looking_away_duration:.1f}s",
                current_time
            )
            if alert:
                alerts.append(alert)
        else:
            self._clear_ongoing_alert(student_id, 'distraction')
        
        # Check phone usage
        phone_usage_result = behaviors.get('phone_usage', {})
        if phone_usage_result.get('is_using_phone'):
            phone_duration = phone_usage_result.get('duration', 0)
            
            alert = self._check_sustained_behavior(
                student_id, student_name, 'phone_usage',
                self.phone_usage_threshold, 'high',
                f"Student {student_name} using phone for {phone_duration:.1f}s",
                current_time
            )
            if alert:
                alerts.append(alert)
        else:
            self._clear_ongoing_alert(student_id, 'phone_usage')
        
        # Check posture
        posture_result = behaviors.get('posture', {})
        if posture_result.get('has_bad_posture'):
            posture_type = posture_result.get('posture_type', 'unknown')
            
            alert = self._check_sustained_behavior(
                student_id, student_name, 'posture',
                self.posture_threshold, 'low',
                f"Student {student_name} has bad posture ({posture_type})",
                current_time
            )
            if alert:
                alerts.append(alert)
        else:
            self._clear_ongoing_alert(student_id, 'posture')
        
        # Store alerts in history
        for alert in alerts:
            self._add_to_history(alert)
        
        return alerts
    
    def _check_sustained_behavior(self, student_id: int, student_name: str,
                                 alert_type: str, threshold: float, severity: str,
                                 message: str, current_time: float) -> Optional[Dict]:
        """Check if behavior has been sustained long enough to alert"""
        ongoing = self.ongoing_alerts[student_id]
        
        if alert_type not in ongoing:
            # Start tracking this behavior
            ongoing[alert_type] = {
                'start_time': current_time,
                'last_reported': current_time
            }
            return None  # Don't alert immediately, wait for threshold
        
        # Calculate duration
        duration = current_time - ongoing[alert_type]['start_time']
        
        # Check if threshold exceeded
        if duration >= threshold:
            # Check if we should report again (report every threshold seconds)
            time_since_report = current_time - ongoing[alert_type]['last_reported']
            
            if time_since_report >= threshold:
                # Generate alert
                alert = {
                    'alert_type': alert_type,
                    'severity': severity,
                    'student_id': student_id,
                    'student_name': student_name,
                    'duration_in_seconds': duration,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Update last reported time
                ongoing[alert_type]['last_reported'] = current_time
                
                return alert
        
        return None
    
    def _clear_ongoing_alert(self, student_id: int, alert_type: str):
        """Clear ongoing alert tracking"""
        if student_id in self.ongoing_alerts:
            if alert_type in self.ongoing_alerts[student_id]:
                del self.ongoing_alerts[student_id][alert_type]
    
    def _add_to_history(self, alert: Dict):
        """Add alert to history"""
        self.alert_history.append(alert)
        
        # Keep history size limited
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]
    
    def get_alert_history(self, student_id: Optional[int] = None,
                         alert_type: Optional[str] = None,
                         limit: int = 100) -> List[Dict]:
        """
        Get alert history with optional filtering.
        
        Parameters:
        -----------
        student_id : int, optional
            Filter by student ID
        alert_type : str, optional
            Filter by alert type
        limit : int
            Maximum number of alerts to return
            
        Returns:
        --------
        list of dict : Matching alerts (most recent first)
        """
        filtered = self.alert_history
        
        if student_id is not None:
            filtered = [a for a in filtered if a['student_id'] == student_id]
        
        if alert_type is not None:
            filtered = [a for a in filtered if a['alert_type'] == alert_type]
        
        # Return most recent first, limited
        return filtered[-limit:][::-1]
    
    def get_ongoing_alerts(self) -> Dict:
        """Get currently ongoing alerts across all students"""
        ongoing = {}
        
        for student_id, alerts in self.ongoing_alerts.items():
            if alerts:  # Only include students with ongoing alerts
                ongoing[student_id] = list(alerts.keys())
        
        return ongoing
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert (mark as seen)"""
        # Would need to enhance alert structure with IDs for this
        pass
    
    def reset_student(self, student_id: int):
        """Reset tracking for a student (e.g., when leaving classroom)"""
        if student_id in self.ongoing_alerts:
            del self.ongoing_alerts[student_id]
    
    def reset_all(self):
        """Reset all ongoing alerts"""
        self.ongoing_alerts.clear()
