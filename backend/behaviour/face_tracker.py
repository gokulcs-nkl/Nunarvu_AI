"""
Face Tracker Module
===================

Tracks and identifies faces across frames using embeddings.
Integrates with the existing InceptionResnetV1 face recognition system.

Performance: ~5ms per face on CPU (uses cached embeddings)
"""

import numpy as np
from collections import defaultdict
import threading


class FaceTracker:
    """
    Tracks student faces across video frames using face embeddings.
    
    Features:
    - Face matching with cached embeddings
    - Multi-face tracking per frame
    - Student ID persistence across frames
    - Face detection quality assessment
    
    Parameters:
    -----------
    embedding_distance_threshold : float
        Euclidean distance threshold for face matching (default: 0.6)
    confidence_threshold : float
        Minimum confidence for face detection (default: 0.5)
    max_face_age : int
        Max frames to keep face in tracking without re-detection (default: 30)
    """
    
    def __init__(self, embedding_distance_threshold=0.6, confidence_threshold=0.5, max_face_age=30):
        self.embedding_distance_threshold = embedding_distance_threshold
        self.confidence_threshold = confidence_threshold
        self.max_face_age = max_face_age
        
        # Face database - will be populated from Student model images
        self.known_face_embeddings = {}  # {student_id: embedding_array}
        self.known_face_names = {}        # {student_id: name}
        
        # Active tracking
        self.tracked_faces = {}           # {face_id: {'student_id', 'name', 'bbox', 'last_seen', 'confidence'}}
        self.face_id_counter = 0
        self.next_face_id = 0
        
        # Thread safety
        self.lock = threading.RLock()
    
    def load_known_faces(self, students_data):
        """
        Load known student face embeddings.
        
        Parameters:
        -----------
        students_data : list of dict
            Student data with embeddings
            [{
                'student_id': int,
                'name': str,
                'embedding': np.ndarray (128,)
            }, ...]
        """
        with self.lock:
            for student in students_data:
                student_id = student.get('student_id')
                name = student.get('name')
                embedding = student.get('embedding')
                
                if student_id is not None and embedding is not None:
                    self.known_face_embeddings[student_id] = embedding
                    self.known_face_names[student_id] = name
    
    def _euclidean_distance(self, embedding1, embedding2):
        """Calculate Euclidean distance between two embeddings"""
        return np.linalg.norm(embedding1 - embedding2)
    
    def _match_face_embedding(self, embedding):
        """
        Find closest matching known face for given embedding.
        
        Parameters:
        -----------
        embedding : np.ndarray
            Face embedding (128-dim from InceptionResnetV1)
            
        Returns:
        --------
        tuple : (student_id, distance) or (None, None)
        """
        if not self.known_face_embeddings:
            return None, None
        
        min_distance = float('inf')
        matched_student_id = None
        
        for student_id, known_embedding in self.known_face_embeddings.items():
            distance = self._euclidean_distance(embedding, known_embedding)
            
            if distance < min_distance:
                min_distance = distance
                matched_student_id = student_id
        
        # Check if match is good enough
        if min_distance <= self.embedding_distance_threshold:
            return matched_student_id, min_distance
        
        return None, min_distance
    
    def update_tracked_faces(self, detected_faces):
        """
        Update face tracking state with newly detected faces.
        
        Parameters:
        -----------
        detected_faces : list of dict
            Currently detected faces in frame
            [{
                'bbox': (x1, y1, x2, y2),
                'embedding': np.ndarray,
                'confidence': float,
                'landmarks': np.ndarray
            }, ...]
            
        Returns:
        --------
        list of dict : Tracked faces with student IDs
            [{
                'face_id': int,
                'student_id': int,
                'name': str,
                'bbox': tuple,
                'embedding': np.ndarray,
                'confidence': float,
                'distance': float,
                'is_recognized': bool
            }, ...]
        """
        with self.lock:
            result_faces = []
            matched_face_ids = set()
            
            # Process each detected face
            for detected_face in detected_faces:
                embedding = detected_face.get('embedding')
                
                if embedding is None:
                    continue
                
                # Try to match face to known student
                student_id, distance = self._match_face_embedding(embedding)
                
                # Try to match with recently tracked faces
                best_match_face_id = None
                best_match_distance = float('inf')
                
                if student_id is None:
                    # If not matched to known student, try to match with tracked faces
                    for face_id, tracked_face in self.tracked_faces.items():
                        if face_id in matched_face_ids:
                            continue
                        
                        # Check if tracked face has same student ID or nearby bbox
                        tracked_bbox = tracked_face.get('bbox')
                        detected_bbox = detected_face.get('bbox')
                        
                        # Calculate bbox overlap/distance
                        if tracked_bbox and detected_bbox:
                            # Simple centroid distance
                            tracked_center = ((tracked_bbox[0] + tracked_bbox[2]) / 2,
                                            (tracked_bbox[1] + tracked_bbox[3]) / 2)
                            detected_center = ((detected_bbox[0] + detected_bbox[2]) / 2,
                                             (detected_bbox[1] + detected_bbox[3]) / 2)
                            
                            centroid_distance = np.sqrt((tracked_center[0] - detected_center[0])**2 +
                                                       (tracked_center[1] - detected_center[1])**2)
                            
                            # If centroid is close, likely same person
                            if centroid_distance < 50 and centroid_distance < best_match_distance:
                                best_match_distance = centroid_distance
                                best_match_face_id = face_id
                else:
                    # Face matched to known student, look for existing tracked entry
                    for face_id, tracked_face in self.tracked_faces.items():
                        if tracked_face.get('student_id') == student_id:
                            best_match_face_id = face_id
                            break
                
                # Create or update tracked face
                if best_match_face_id is not None:
                    face_id = best_match_face_id
                else:
                    face_id = self._get_next_face_id()
                
                # Update tracking state
                tracked_face_data = {
                    'face_id': face_id,
                    'student_id': student_id,
                    'name': self.known_face_names.get(student_id, f'Unknown {face_id}'),
                    'bbox': detected_face.get('bbox'),
                    'embedding': embedding,
                    'confidence': detected_face.get('confidence', 0.0),
                    'distance': distance,
                    'is_recognized': student_id is not None,
                    'landmarks': detected_face.get('landmarks'),
                    'last_seen': 0
                }
                
                self.tracked_faces[face_id] = tracked_face_data
                matched_face_ids.add(face_id)
                result_faces.append(tracked_face_data)
            
            # Age out unmatched faces
            faces_to_remove = []
            for face_id, tracked_face in self.tracked_faces.items():
                if face_id not in matched_face_ids:
                    tracked_face['last_seen'] += 1
                    
                    # Remove if not seen for too long
                    if tracked_face['last_seen'] > self.max_face_age:
                        faces_to_remove.append(face_id)
            
            for face_id in faces_to_remove:
                del self.tracked_faces[face_id]
            
            return result_faces
    
    def _get_next_face_id(self):
        """Generate next face ID"""
        self.next_face_id += 1
        return self.next_face_id
    
    def get_student_location(self, student_id):
        """
        Get current location/bbox of a student if visible.
        
        Parameters:
        -----------
        student_id : int
            Student ID to locate
            
        Returns:
        --------
        dict or None : {'bbox': tuple, 'confidence': float} or None
        """
        with self.lock:
            for face_id, tracked_face in self.tracked_faces.items():
                if tracked_face.get('student_id') == student_id:
                    return {
                        'bbox': tracked_face.get('bbox'),
                        'confidence': tracked_face.get('confidence'),
                        'face_id': face_id
                    }
        
        return None
    
    def get_all_visible_students(self):
        """
        Get list of all currently visible/tracked students.
        
        Returns:
        --------
        list of dict : [{student_id, name, bbox, confidence}, ...]
        """
        with self.lock:
            students = []
            for face_id, tracked_face in self.tracked_faces.items():
                if tracked_face.get('student_id') is not None:
                    students.append({
                        'student_id': tracked_face.get('student_id'),
                        'name': tracked_face.get('name'),
                        'bbox': tracked_face.get('bbox'),
                        'confidence': tracked_face.get('confidence'),
                        'face_id': face_id
                    })
            
            return students
    
    def reset(self):
        """Reset tracking state"""
        with self.lock:
            self.tracked_faces.clear()
            self.next_face_id = 0
