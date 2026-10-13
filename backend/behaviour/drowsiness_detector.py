"""
Drowsiness Detector Module
==========================

Detects drowsiness using Eye Aspect Ratio (EAR) from MediaPipe Face Mesh.
Eye Aspect Ratio is calculated as the ratio of vertical to horizontal eye distances.
When eyes close, EAR drops below threshold (typically 0.2), indicating drowsiness.

Performance: ~5ms per face on CPU
"""

import numpy as np
from collections import deque


class DrowsinessDetector:
    """
    Detects drowsiness by monitoring Eye Aspect Ratio (EAR).
    
    Algorithm:
    ----------
    EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
    
    Where p1-p6 are the eye landmark points from MediaPipe Face Mesh.
    
    Parameters:
    -----------
    ear_threshold : float
        EAR value below which eyes are considered closed (default: 0.2)
    consecutive_frames : int
        Number of consecutive frames with low EAR to trigger drowsiness (default: 5)
    smoothing_window : int
        Rolling window size for EAR smoothing (default: 5)
    """
    
    # Eye landmark indices from MediaPipe Face Mesh (468 landmarks)
    # Right eye: points 33, 160, 158, 133, 153, 144
    RIGHT_EYE = {
        'outer': 33,      # Right eye left corner
        'top': 160,       # Top eyelid
        'inner_top': 158, # Inner top
        'inner': 133,     # Right eye right corner
        'bottom': 153,    # Bottom eyelid
        'inner_bottom': 144  # Inner bottom
    }
    
    # Left eye: points 263, 387, 385, 362, 380, 373
    LEFT_EYE = {
        'outer': 263,     # Left eye right corner
        'top': 387,       # Top eyelid
        'inner_top': 385, # Inner top
        'inner': 362,     # Left eye left corner
        'bottom': 380,    # Bottom eyelid
        'inner_bottom': 373  # Inner bottom
    }
    
    def __init__(self, ear_threshold=0.2, consecutive_frames=5, smoothing_window=5):
        self.ear_threshold = ear_threshold
        self.consecutive_frames = consecutive_frames
        self.smoothing_window = smoothing_window
        
        # State tracking
        self.ear_history = deque(maxlen=smoothing_window)
        self.low_ear_counter = 0
        self.drowsiness_score = 100.0  # 0-100, where 100 = fully alert
        self.is_drowsy = False
        
    def _calculate_eye_aspect_ratio(self, eye_landmarks):
        """
        Calculate Eye Aspect Ratio from 6 eye landmark points.
        
        Parameters:
        -----------
        eye_landmarks : np.ndarray
            Array of 6 points (x, y) for eye landmarks
            
        Returns:
        --------
        float : EAR value (typically 0.0 - 0.5)
        """
        if eye_landmarks.shape[0] < 6:
            return 0.0
        
        # Extract coordinates
        p2 = eye_landmarks[1]  # top
        p3 = eye_landmarks[2]  # inner top
        p5 = eye_landmarks[4]  # inner bottom
        p6 = eye_landmarks[5]  # bottom
        p1 = eye_landmarks[0]  # outer
        p4 = eye_landmarks[3]  # inner
        
        # Calculate vertical distances
        vertical_dist1 = np.linalg.norm(p2 - p6)  # Top to bottom
        vertical_dist2 = np.linalg.norm(p3 - p5)  # Inner top to inner bottom
        
        # Calculate horizontal distance
        horizontal_dist = np.linalg.norm(p1 - p4)  # Outer to inner
        
        # Avoid division by zero
        if horizontal_dist == 0:
            return 0.0
        
        # Calculate EAR
        ear = (vertical_dist1 + vertical_dist2) / (2.0 * horizontal_dist)
        return ear
    
    def detect(self, face_landmarks):
        """
        Detect drowsiness from face landmarks.
        
        Parameters:
        -----------
        face_landmarks : list of tuples or np.ndarray
            468 facial landmarks from MediaPipe Face Mesh
            Expected shape: (468, 2) with (x, y) normalized coordinates
            
        Returns:
        --------
        dict : {
            'is_drowsy': bool,
            'drowsiness_score': float (0-100),
            'ear': float,
            'eye_state': str ('open' or 'closed')
        }
        """
        if face_landmarks is None or len(face_landmarks) < 468:
            return {
                'is_drowsy': False,
                'drowsiness_score': 100.0,
                'ear': 0.0,
                'eye_state': 'unknown'
            }
        
        # Convert to numpy array if needed
        landmarks = np.array(face_landmarks)
        
        # Calculate EAR for both eyes
        right_eye_points = landmarks[[33, 160, 158, 133, 153, 144]]
        left_eye_points = landmarks[[263, 387, 385, 362, 380, 373]]
        
        right_ear = self._calculate_eye_aspect_ratio(right_eye_points)
        left_ear = self._calculate_eye_aspect_ratio(left_eye_points)
        
        # Average EAR from both eyes
        avg_ear = (right_ear + left_ear) / 2.0
        
        # Update EAR history for smoothing
        self.ear_history.append(avg_ear)
        smoothed_ear = np.mean(list(self.ear_history))
        
        # Check if eyes are closed
        eyes_closed = smoothed_ear < self.ear_threshold
        
        # Update low EAR counter
        if eyes_closed:
            self.low_ear_counter += 1
        else:
            self.low_ear_counter = max(0, self.low_ear_counter - 1)
        
        # Determine if drowsy (sustained eye closure)
        self.is_drowsy = self.low_ear_counter >= self.consecutive_frames
        
        # Calculate drowsiness score (100 = fully alert, 0 = severely drowsy)
        # Linear mapping: EAR of 0.2 = 0% alert, EAR of 0.35 = 100% alert
        self.drowsiness_score = max(0, min(100, (smoothed_ear - 0.1) / 0.25 * 100))
        
        eye_state = 'closed' if eyes_closed else 'open'
        
        return {
            'is_drowsy': self.is_drowsy,
            'drowsiness_score': self.drowsiness_score,
            'ear': smoothed_ear,
            'eye_state': eye_state,
            'right_ear': right_ear,
            'left_ear': left_ear,
            'consecutive_frames_closed': self.low_ear_counter
        }
    
    def reset(self):
        """Reset detector state for new frame sequence"""
        self.ear_history.clear()
        self.low_ear_counter = 0
        self.drowsiness_score = 100.0
        self.is_drowsy = False
