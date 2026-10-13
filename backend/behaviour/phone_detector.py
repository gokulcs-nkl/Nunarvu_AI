"""
Phone Detection Module
======================

Detects mobile phones in the classroom using YOLOv8n (nano model).
Maps detected phones to individual students based on spatial proximity.

Performance: ~15ms per frame on CPU with YOLOv8n
"""

import numpy as np
from collections import deque, defaultdict
import os


class PhoneDetector:
    """
    Detects mobile phones using YOLOv8n YOLO model.
    
    Features:
    - Single phone detection (most relevant phone in frame)
    - Phone tracking across frames
    - Assignment of phone to specific student based on proximity
    
    Parameters:
    -----------
    confidence_threshold : float
        Confidence threshold for phone detection (default: 0.5)
    nms_threshold : float
        Non-maximum suppression threshold (default: 0.45)
    sustained_threshold : float
        Duration in seconds to trigger phone usage alert (default: 5.0)
    """
    
    # Target object classes from COCO dataset
    PHONE_CLASSES = [
        'cell phone',
        'mobile phone',
        'phone',
        'smartphone',
        'iphone'
    ]
    
    def __init__(self, confidence_threshold=0.5, nms_threshold=0.45, sustained_threshold=5.0):
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.sustained_threshold = sustained_threshold
        
        # Try to load YOLOv8n model (lazy loading)
        self.model = None
        self.model_loaded = False
        self._load_model()
        
        # Phone tracking per student
        self.student_phone_timer = defaultdict(float)
        self.phone_usage_score = 1.0  # 1.0 = no phone (100%), 0.0 = using phone
        self.is_using_phone = False
        
    def _load_model(self):
        """Lazy load YOLOv8n model on first use"""
        try:
            from ultralytics import YOLO
            
            # Try to load cached model, or download if not available
            model_path = 'yolov8n.pt'  # nano model (~6MB)
            
            if not os.path.exists(model_path):
                print(f"[PhoneDetector] Downloading YOLOv8n model...")
            
            self.model = YOLO(model_path)
            self.model.to('cpu')  # Force CPU
            self.model_loaded = True
            print("[PhoneDetector] YOLOv8n model loaded successfully")
        except ImportError:
            print("[PhoneDetector] WARNING: ultralytics not installed. Phone detection disabled.")
            print("  Install with: pip install ultralytics")
            self.model_loaded = False
        except Exception as e:
            print(f"[PhoneDetector] ERROR loading model: {e}")
            self.model_loaded = False
    
    def _calculate_centroid(self, bbox):
        """Calculate centroid of bounding box"""
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        return cx, cy
    
    def _get_distance(self, point1, point2):
        """Calculate Euclidean distance between two points"""
        return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
    
    def detect(self, frame, detected_faces=None, fps=25):
        """
        Detect phones in frame and assign to students.
        
        Parameters:
        -----------
        frame : np.ndarray
            Input frame (BGR format)
        detected_faces : list of dict
            List of detected faces with 'bbox', 'student_id', 'name' keys
            Each face: {'bbox': (x1, y1, x2, y2), 'student_id': int, 'name': str}
        fps : int
            Frames per second for duration calculation (default: 25)
            
        Returns:
        --------
        dict : {
            'phone_detected': bool,
            'phone_detections': list,  # [{bbox, confidence, assigned_student_id}, ...]
            'student_phone_usage': dict,  # {student_id: {'duration': float, 'bbox': tuple}}
            'phone_usage_score': float (0-100),
            'frame_height': int,
            'frame_width': int
        }
        """
        frame_height, frame_width = frame.shape[:2]
        
        phone_detections = []
        student_phone_usage = {}
        
        # If model not loaded, return empty detections
        if not self.model_loaded:
            return {
                'phone_detected': False,
                'phone_detections': [],
                'student_phone_usage': {},
                'phone_usage_score': 100.0,
                'frame_height': frame_height,
                'frame_width': frame_width
            }
        
        try:
            # Run YOLO inference
            # Use conf parameter to filter by confidence
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            
            # Process detections
            for result in results:
                if result.boxes is None:
                    continue
                
                # Extract detections
                boxes = result.boxes
                for box in boxes:
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    
                    # Check if detected object is a phone
                    if any(phone_class in class_name.lower() for phone_class in self.PHONE_CLASSES):
                        phone_detections.append({
                            'bbox': (x1, y1, x2, y2),
                            'confidence': confidence,
                            'class': class_name
                        })
        
        except Exception as e:
            print(f"[PhoneDetector] Error during inference: {e}")
            return {
                'phone_detected': False,
                'phone_detections': [],
                'student_phone_usage': {},
                'phone_usage_score': 100.0,
                'frame_height': frame_height,
                'frame_width': frame_width
            }
        
        # Assign phones to students based on proximity
        if detected_faces and phone_detections:
            for phone_det in phone_detections:
                phone_bbox = phone_det['bbox']
                phone_centroid = self._calculate_centroid(phone_bbox)
                
                # Find closest student face
                min_distance = float('inf')
                assigned_student_id = None
                assigned_student_name = None
                
                for face in detected_faces:
                    if 'bbox' not in face or 'student_id' not in face:
                        continue
                    
                    face_bbox = face['bbox']
                    face_centroid = self._calculate_centroid(face_bbox)
                    
                    distance = self._get_distance(phone_centroid, face_centroid)
                    
                    # Assign if within reasonable distance (e.g., 200 pixels)
                    if distance < 200 and distance < min_distance:
                        min_distance = distance
                        assigned_student_id = face.get('student_id')
                        assigned_student_name = face.get('name', f'Student {assigned_student_id}')
                
                # Update detection with assigned student
                phone_det['assigned_student_id'] = assigned_student_id
                phone_det['assigned_student_name'] = assigned_student_name
                
                # Track phone usage duration for student
                if assigned_student_id is not None:
                    self.student_phone_timer[assigned_student_id] += 1.0 / fps
                    student_phone_usage[assigned_student_id] = {
                        'duration': self.student_phone_timer[assigned_student_id],
                        'bbox': phone_det['bbox'],
                        'confidence': phone_det['confidence']
                    }
        
        # Update phone usage score based on detections
        self.is_using_phone = len(phone_detections) > 0
        
        # Score: 100% if no phones, decreases with phone usage time
        # Reset score if no phones detected for >sustained_threshold seconds
        if not self.is_using_phone:
            self.phone_usage_score = 100.0
            self.student_phone_timer.clear()
        else:
            # Scale down score based on usage
            max_usage = max(self.student_phone_timer.values()) if self.student_phone_timer else 0
            self.phone_usage_score = max(0, 100 - (max_usage / self.sustained_threshold) * 100)
        
        return {
            'phone_detected': self.is_using_phone,
            'phone_detections': phone_detections,
            'student_phone_usage': student_phone_usage,
            'phone_usage_score': self.phone_usage_score,
            'frame_height': frame_height,
            'frame_width': frame_width
        }
    
    def reset(self):
        """Reset detector state"""
        self.student_phone_timer.clear()
        self.phone_usage_score = 100.0
        self.is_using_phone = False
    
    def reset_student(self, student_id):
        """Reset timer for specific student"""
        if student_id in self.student_phone_timer:
            del self.student_phone_timer[student_id]
