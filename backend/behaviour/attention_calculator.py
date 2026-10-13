"""
Attention Calculator Module
============================

Calculates weighted attention scores for students based on behavior components.
Provides detailed component breakdown and configuration options.
"""

import numpy as np
from typing import Dict, List


class AttentionCalculator:
    """
    Calculates student attention scores from behavior components.
    
    Supports configurable weights for each behavior component.
    
    Default weights:
    - Drowsiness: 25%
    - Head Pose: 25%
    - Phone Usage: 20%
    - Posture: 15%
    - Attendance Duration: 15%
    
    Parameters:
    -----------
    weights : dict, optional
        Custom weights for each component
        Example: {'drowsiness': 0.25, 'head_pose': 0.25, ...}
    """
    
    DEFAULT_WEIGHTS = {
        'drowsiness': 0.25,
        'head_pose': 0.25,
        'phone_usage': 0.20,
        'posture': 0.15,
        'attendance': 0.15
    }
    
    # Attention level classifications
    ATTENTION_LEVELS = {
        'excellent': (85, 100),      # Green
        'good': (70, 84),            # Light Green
        'fair': (55, 69),            # Yellow
        'poor': (40, 54),            # Orange
        'critical': (0, 39)          # Red
    }
    
    def __init__(self, weights=None):
        """Initialize calculator with optional custom weights"""
        if weights is None:
            self.weights = self.DEFAULT_WEIGHTS.copy()
        else:
            self.weights = weights
            # Normalize weights to sum to 1.0
            total = sum(self.weights.values())
            if total != 1.0:
                self.weights = {k: v / total for k, v in self.weights.items()}
    
    def calculate(self, behaviors: Dict) -> Dict:
        """
        Calculate attention score from behavior components.
        
        Parameters:
        -----------
        behaviors : dict
            Behavior data for a student
            {
                'drowsiness': {'drowsiness_score': float},
                'head_pose': {'head_pose_score': float},
                'phone_usage': {'phone_usage_score': float},
                'posture': {'posture_score': float}
            }
            
        Returns:
        --------
        dict : {
            'overall_score': float (0-100),
            'level': str ('excellent', 'good', 'fair', 'poor', 'critical'),
            'component_scores': dict,
            'weighted_components': dict,
            'alerts': list
        }
        """
        component_scores = self._extract_component_scores(behaviors)
        weighted_components = self._calculate_weighted_scores(component_scores)
        
        # Overall score
        overall_score = sum(weighted_components.values())
        overall_score = max(0, min(100, overall_score))  # Clamp to 0-100
        
        # Determine attention level
        level = self._classify_attention_level(overall_score)
        
        # Generate alerts based on component scores
        alerts = self._generate_alerts(component_scores, behaviors)
        
        return {
            'overall_score': overall_score,
            'level': level,
            'component_scores': component_scores,
            'weighted_components': weighted_components,
            'alerts': alerts,
            'weights': self.weights
        }
    
    def _extract_component_scores(self, behaviors: Dict) -> Dict[str, float]:
        """Extract score for each behavior component"""
        scores = {}
        
        # Drowsiness
        scores['drowsiness'] = behaviors.get('drowsiness', {}).get('drowsiness_score', 100.0)
        
        # Head Pose
        scores['head_pose'] = behaviors.get('head_pose', {}).get('head_pose_score', 100.0)
        
        # Phone Usage
        scores['phone_usage'] = behaviors.get('phone_usage', {}).get('phone_usage_score', 100.0)
        
        # Posture
        scores['posture'] = behaviors.get('posture', {}).get('posture_score', 100.0)
        
        # Attendance (always 100 if present)
        scores['attendance'] = 100.0
        
        return scores
    
    def _calculate_weighted_scores(self, component_scores: Dict[str, float]) -> Dict[str, float]:
        """Apply weights to component scores"""
        weighted = {}
        
        for component, weight in self.weights.items():
            score = component_scores.get(component, 100.0)
            weighted[component] = score * weight
        
        return weighted
    
    def _classify_attention_level(self, score: float) -> str:
        """Classify attention score into level"""
        for level, (min_score, max_score) in self.ATTENTION_LEVELS.items():
            if min_score <= score <= max_score:
                return level
        
        return 'critical' if score < 0 else 'excellent'
    
    def _generate_alerts(self, component_scores: Dict[str, float], behaviors: Dict) -> List[Dict]:
        """Generate alerts for low component scores"""
        alerts = []
        
        # Drowsiness alert
        if component_scores['drowsiness'] < 40:
            severity = 'high' if component_scores['drowsiness'] < 20 else 'medium'
            is_drowsy = behaviors.get('drowsiness', {}).get('is_drowsy', False)
            
            if is_drowsy:
                alerts.append({
                    'type': 'drowsiness',
                    'severity': severity,
                    'message': 'Student is drowsy/eyes closed',
                    'score': component_scores['drowsiness']
                })
        
        # Head Pose alert (looking away)
        if component_scores['head_pose'] < 40:
            is_looking_away = behaviors.get('head_pose', {}).get('is_looking_away', False)
            direction = behaviors.get('head_pose', {}).get('looking_direction', 'unknown')
            
            if is_looking_away:
                alerts.append({
                    'type': 'distraction',
                    'severity': 'medium',
                    'message': f'Student looking {direction} (distracted)',
                    'score': component_scores['head_pose'],
                    'direction': direction
                })
        
        # Phone Usage alert
        if component_scores['phone_usage'] < 50:
            is_using_phone = behaviors.get('phone_usage', {}).get('is_using_phone', False)
            
            if is_using_phone:
                duration = behaviors.get('phone_usage', {}).get('duration', 0)
                alerts.append({
                    'type': 'phone_usage',
                    'severity': 'high',
                    'message': f'Student using phone ({duration:.1f}s)',
                    'score': component_scores['phone_usage'],
                    'duration': duration
                })
        
        # Posture alert
        if component_scores['posture'] < 50:
            has_bad_posture = behaviors.get('posture', {}).get('has_bad_posture', False)
            posture_type = behaviors.get('posture', {}).get('posture_type', 'unknown')
            
            if has_bad_posture:
                alerts.append({
                    'type': 'posture',
                    'severity': 'low',
                    'message': f'Bad posture detected ({posture_type})',
                    'score': component_scores['posture'],
                    'posture_type': posture_type
                })
        
        return alerts
    
    def get_attention_color(self, score: float) -> str:
        """Get color code for attention score (for UI visualization)"""
        if score >= 85:
            return '#00AA00'  # Green
        elif score >= 70:
            return '#88DD00'  # Light Green
        elif score >= 55:
            return '#FFDD00'  # Yellow
        elif score >= 40:
            return '#FF8800'  # Orange
        else:
            return '#FF0000'  # Red
    
    def get_attention_emoji(self, score: float) -> str:
        """Get emoji representation of attention level"""
        if score >= 85:
            return '😊'  # Excellent
        elif score >= 70:
            return '🙂'  # Good
        elif score >= 55:
            return '😐'  # Fair
        elif score >= 40:
            return '😕'  # Poor
        else:
            return '😴'  # Critical
    
    def update_weights(self, new_weights: Dict[str, float]):
        """Update calculation weights"""
        if new_weights:
            self.weights = new_weights
            # Normalize
            total = sum(self.weights.values())
            if total != 1.0:
                self.weights = {k: v / total for k, v in self.weights.items()}
    
    @staticmethod
    def get_default_weights() -> Dict[str, float]:
        """Get default weight configuration"""
        return AttentionCalculator.DEFAULT_WEIGHTS.copy()
    
    @staticmethod
    def compare_students(student_scores: List[Dict]) -> List[Dict]:
        """
        Compare and rank students by attention score.
        
        Parameters:
        -----------
        student_scores : list of dict
            [{student_id, name, attention_score, level}, ...]
            
        Returns:
        --------
        list of dict : Sorted by attention score (lowest first - teacher priority)
        """
        # Sort by score (lowest first = highest priority)
        sorted_scores = sorted(student_scores, key=lambda x: x.get('attention_score', 100))
        
        # Add rank
        for idx, student in enumerate(sorted_scores):
            student['rank'] = idx + 1
            student['needs_attention'] = student.get('attention_score', 100) < 70
        
        return sorted_scores
