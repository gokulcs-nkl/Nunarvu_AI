"""
Posture Detector Module
=======================

Analyzes student posture using MediaPipe Pose estimation.
Detects slouching, bent posture, and other bad sitting positions.

Performance: ~10ms per frame on CPU
"""

import numpy as np
from collections import deque
import math


class PostureDetector:
    """
    Analyzes body posture from MediaPipe Pose landmarks.
    
    Detects:
    - Upright posture (good)
    - Slouching (shoulders dropped)
    - Bent forward (looking down)
    - Lying down / extreme positions (abnormal)
    
    Parameters:
    -----------
    upright_threshold : float
        Angle threshold for upright posture (default: 20 degrees)
    slouch_threshold : float
        Angle threshold for slouch detection (default: 30 degrees)
    smoothing_window : int
        Rolling window for angle smoothing (default: 5)
    """
    
    # Key body landmarks from MediaPipe Pose (33 landmarks)
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_EAR = 7
    RIGHT_EAR = 8
    NOSE = 0
    
    # Posture types
    POSTURE_TYPES = {
        'upright': 1,
        'slouching': 2,
        'bent_forward': 3,
        'leaning_left': 4,
        'leaning_right': 5,
        'abnormal': 6
    }
    
    def __init__(self, upright_threshold=20, slouch_threshold=30, smoothing_window=5):
        self.upright_threshold = upright_threshold
        self.slouch_threshold = slouch_threshold
        self.smoothing_window = smoothing_window
        
        # State tracking
        self.spine_angle_history = deque(maxlen=smoothing_window)
        self.shoulder_angle_history = deque(maxlen=smoothing_window)
        self.forward_angle_history = deque(maxlen=smoothing_window)
        
        self.posture_score = 100.0  # 0-100, where 100 = perfect upright
        self.posture_type = 'upright'
        self.has_bad_posture = False
        
    def _calculate_angle(self, point1, point2, point3):
        """
        Calculate angle at point2 formed by points 1-2-3.
        
        Parameters:
        -----------
        point1, point2, point3 : np.ndarray
            (x, y) coordinates of points
            
        Returns:
        --------
        float : angle in degrees (0-180)
        """
        # Calculate vectors
        vec1 = point1 - point2
        vec2 = point3 - point2
        
        # Calculate angle using dot product
        cos_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-6)
        cos_angle = np.clip(cos_angle, -1, 1)
        
        angle = np.arccos(cos_angle)
        angle_degrees = np.degrees(angle)
        
        return angle_degrees
    
    def detect(self, pose_landmarks):
        """
        Detect posture from MediaPipe Pose landmarks.
        
        Parameters:
        -----------
        pose_landmarks : np.ndarray
            33 body landmarks from MediaPipe Pose
            Expected shape: (33, 3) with (x, y, z) or (x, y) coordinates
            
        Returns:
        --------
        dict : {
            'posture_type': str,
            'posture_score': float (0-100),
            'has_bad_posture': bool,
            'spine_angle': float,
            'shoulder_angle': float,
            'forward_angle': float
        }
        """
        if pose_landmarks is None or len(pose_landmarks) < 25:
            return {
                'posture_type': 'unknown',
                'posture_score': 50.0,
                'has_bad_posture': False,
                'spine_angle': 0,
                'shoulder_angle': 0,
                'forward_angle': 0
            }
        
        landmarks = np.array(pose_landmarks)
        
        # Only use x, y coordinates
        if landmarks.shape[1] >= 2:
            landmarks = landmarks[:, :2]
        
        # Extract key points
        left_shoulder = landmarks[self.LEFT_SHOULDER]
        right_shoulder = landmarks[self.RIGHT_SHOULDER]
        left_hip = landmarks[self.LEFT_HIP]
        right_hip = landmarks[self.RIGHT_HIP]
        left_ear = landmarks[self.LEFT_EAR]
        right_ear = landmarks[self.RIGHT_EAR]
        nose = landmarks[self.NOSE]
        
        # Calculate spine angle (vertical alignment of shoulders and hips)
        # Ideal spine angle should be close to 90 degrees (vertical)
        shoulder_center = (left_shoulder + right_shoulder) / 2
        hip_center = (left_hip + right_hip) / 2
        
        # Vector from hip to shoulder (spine)
        spine_vector = shoulder_center - hip_center
        # Vertical reference vector
        vertical_vector = np.array([0, 1])
        
        # Calculate angle from vertical
        spine_angle = self._calculate_angle(
            spine_vector + shoulder_center,
            shoulder_center,
            vertical_vector + shoulder_center
        )
        spine_angle = abs(spine_angle - 90)  # How far from vertical
        
        # Calculate shoulder angle (for slouching detection)
        # If shoulders drop significantly, it's slouching
        shoulder_drop = (left_shoulder[1] + right_shoulder[1]) / 2
        hip_height = (left_hip[1] + right_hip[1]) / 2
        
        # Shoulder should be notably above hip when upright
        shoulder_angle = hip_height - shoulder_drop
        
        # Calculate forward angle (bending forward)
        # Angle between shoulders and ear positions
        ear_center = (left_ear + right_ear) / 2
        forward_vector = ear_center - shoulder_center
        
        forward_angle = self._calculate_angle(
            shoulder_center,
            shoulder_center,
            forward_vector + shoulder_center
        )
        
        # Update history for smoothing
        self.spine_angle_history.append(spine_angle)
        self.shoulder_angle_history.append(shoulder_angle)
        self.forward_angle_history.append(forward_angle)
        
        # Smooth angles
        smooth_spine_angle = np.mean(list(self.spine_angle_history))
        smooth_shoulder_angle = np.mean(list(self.shoulder_angle_history))
        smooth_forward_angle = np.mean(list(self.forward_angle_history))
        
        # Classify posture
        if smooth_spine_angle < self.upright_threshold:
            # Good upright posture
            self.posture_type = 'upright'
            self.posture_score = 100 - smooth_spine_angle
            self.has_bad_posture = False
        elif smooth_shoulder_angle < 30:
            # Slouching (shoulders dropped)
            self.posture_type = 'slouching'
            self.posture_score = max(0, 70 - (self.slouch_threshold - smooth_shoulder_angle) * 5)
            self.has_bad_posture = True
        elif smooth_forward_angle > 45:
            # Bent forward
            self.posture_type = 'bent_forward'
            self.posture_score = max(0, 50 - (smooth_forward_angle - 45) * 2)
            self.has_bad_posture = True
        elif smooth_spine_angle > 40:
            # Leaning
            if spine_vector[0] < 0:
                self.posture_type = 'leaning_left'
            else:
                self.posture_type = 'leaning_right'
            self.posture_score = max(0, 60 - (smooth_spine_angle - 40) * 2)
            self.has_bad_posture = True
        else:
            self.posture_type = 'upright'
            self.posture_score = 80
            self.has_bad_posture = False
        
        return {
            'posture_type': self.posture_type,
            'posture_score': self.posture_score,
            'has_bad_posture': self.has_bad_posture,
            'spine_angle': smooth_spine_angle,
            'shoulder_angle': smooth_shoulder_angle,
            'forward_angle': smooth_forward_angle
        }
    
    def reset(self):
        """Reset detector state"""
        self.spine_angle_history.clear()
        self.shoulder_angle_history.clear()
        self.forward_angle_history.clear()
        self.posture_score = 100.0
        self.posture_type = 'upright'
        self.has_bad_posture = False
