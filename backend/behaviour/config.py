"""
Behavior Analysis Configuration
================================

Central configuration file for all behavior detection thresholds and parameters.
Can be overridden by environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# ============================================================================
# DETECTION THRESHOLDS
# ============================================================================

# Drowsiness Detection (Eye Aspect Ratio)
DROWSINESS_EAR_THRESHOLD = float(os.getenv('BEHAVIOR_DROWSINESS_EAR_THRESHOLD', '0.2'))
DROWSINESS_CONSECUTIVE_FRAMES = int(os.getenv('BEHAVIOR_DROWSINESS_FRAMES', '5'))
DROWSINESS_SMOOTHING_WINDOW = int(os.getenv('BEHAVIOR_DROWSINESS_SMOOTHING', '5'))

# Head Pose Detection
HEAD_POSE_YAW_THRESHOLD = float(os.getenv('BEHAVIOR_HEAD_POSE_YAW', '30'))  # degrees
HEAD_POSE_PITCH_THRESHOLD = float(os.getenv('BEHAVIOR_HEAD_POSE_PITCH', '25'))  # degrees
HEAD_POSE_SUSTAINED_FRAMES = int(os.getenv('BEHAVIOR_HEAD_POSE_FRAMES', '50'))
HEAD_POSE_SMOOTHING_WINDOW = int(os.getenv('BEHAVIOR_HEAD_POSE_SMOOTHING', '5'))

# Phone Detection
PHONE_DETECTION_CONFIDENCE = float(os.getenv('BEHAVIOR_PHONE_CONFIDENCE', '0.5'))
PHONE_DETECTION_NMS = float(os.getenv('BEHAVIOR_PHONE_NMS', '0.45'))
PHONE_PROXIMITY_DISTANCE = float(os.getenv('BEHAVIOR_PHONE_PROXIMITY', '200'))  # pixels

# Posture Detection
POSTURE_UPRIGHT_THRESHOLD = float(os.getenv('BEHAVIOR_POSTURE_UPRIGHT', '20'))  # degrees
POSTURE_SLOUCH_THRESHOLD = float(os.getenv('BEHAVIOR_POSTURE_SLOUCH', '30'))  # degrees
POSTURE_SMOOTHING_WINDOW = int(os.getenv('BEHAVIOR_POSTURE_SMOOTHING', '5'))

# ============================================================================
# ALERT THRESHOLDS
# ============================================================================

ALERT_DROWSINESS_DURATION = float(os.getenv('BEHAVIOR_ALERT_DROWSINESS', '10.0'))  # seconds
ALERT_LOOKING_AWAY_DURATION = float(os.getenv('BEHAVIOR_ALERT_LOOKING_AWAY', '25.0'))
ALERT_PHONE_USAGE_DURATION = float(os.getenv('BEHAVIOR_ALERT_PHONE', '5.0'))
ALERT_BAD_POSTURE_DURATION = float(os.getenv('BEHAVIOR_ALERT_POSTURE', '15.0'))
ALERT_ABSENCE_DURATION = float(os.getenv('BEHAVIOR_ALERT_ABSENCE', '30.0'))

# ============================================================================
# ATTENTION SCORE WEIGHTS
# ============================================================================

# Default weights for attention score calculation
# Total should sum to 1.0
ATTENTION_WEIGHT_DROWSINESS = float(os.getenv('BEHAVIOR_WEIGHT_DROWSINESS', '0.25'))
ATTENTION_WEIGHT_HEAD_POSE = float(os.getenv('BEHAVIOR_WEIGHT_HEAD_POSE', '0.25'))
ATTENTION_WEIGHT_PHONE_USAGE = float(os.getenv('BEHAVIOR_WEIGHT_PHONE', '0.20'))
ATTENTION_WEIGHT_POSTURE = float(os.getenv('BEHAVIOR_WEIGHT_POSTURE', '0.15'))
ATTENTION_WEIGHT_ATTENDANCE = float(os.getenv('BEHAVIOR_WEIGHT_ATTENDANCE', '0.15'))

# Validate weights sum to 1.0
ATTENTION_WEIGHTS = {
    'drowsiness': ATTENTION_WEIGHT_DROWSINESS,
    'head_pose': ATTENTION_WEIGHT_HEAD_POSE,
    'phone_usage': ATTENTION_WEIGHT_PHONE_USAGE,
    'posture': ATTENTION_WEIGHT_POSTURE,
    'attendance': ATTENTION_WEIGHT_ATTENDANCE
}

_total_weight = sum(ATTENTION_WEIGHTS.values())
if abs(_total_weight - 1.0) > 0.01:
    print(f"[Config] WARNING: Attention weights sum to {_total_weight}, normalizing...")
    for key in ATTENTION_WEIGHTS:
        ATTENTION_WEIGHTS[key] /= _total_weight

# ============================================================================
# PROCESSING OPTIMIZATION
# ============================================================================

# Frame skipping (process every Nth frame for behavior analysis)
# 1 = every frame, 2 = every other frame, 3 = every 3rd frame, etc.
BEHAVIOR_FRAME_SKIP = int(os.getenv('BEHAVIOR_FRAME_SKIP', '1'))

# Input resolution for behavior analysis (height, width)
# Lower resolution = faster processing but lower accuracy
BEHAVIOR_INPUT_HEIGHT = int(os.getenv('BEHAVIOR_INPUT_HEIGHT', '480'))
BEHAVIOR_INPUT_WIDTH = int(os.getenv('BEHAVIOR_INPUT_WIDTH', '640'))
BEHAVIOR_INPUT_RESOLUTION = (BEHAVIOR_INPUT_HEIGHT, BEHAVIOR_INPUT_WIDTH)

# Batch size for database writes
DATABASE_BATCH_SIZE = int(os.getenv('DATABASE_BATCH_SIZE', '50'))
DATABASE_FLUSH_INTERVAL = float(os.getenv('DATABASE_FLUSH_INTERVAL', '10.0'))

# ============================================================================
# MEDIAPIPE MODELS
# ============================================================================

# MediaPipe Face Mesh settings
MEDIAPIPE_FACE_MAX_FACES = int(os.getenv('MEDIAPIPE_FACE_MAX', '50'))
MEDIAPIPE_FACE_MIN_DETECTION = float(os.getenv('MEDIAPIPE_FACE_MIN_DETECT', '0.5'))
MEDIAPIPE_FACE_MIN_TRACKING = float(os.getenv('MEDIAPIPE_FACE_MIN_TRACK', '0.5'))

# MediaPipe Pose settings (lightweight model for CPU)
MEDIAPIPE_POSE_MODEL_COMPLEXITY = int(os.getenv('MEDIAPIPE_POSE_COMPLEXITY', '0'))  # 0=lightweight
MEDIAPIPE_POSE_MIN_DETECTION = float(os.getenv('MEDIAPIPE_POSE_MIN_DETECT', '0.5'))
MEDIAPIPE_POSE_MIN_TRACKING = float(os.getenv('MEDIAPIPE_POSE_MIN_TRACK', '0.5'))

# ============================================================================
# YOLO SETTINGS
# ============================================================================

# YOLOv8n model for phone detection
YOLO_MODEL_NAME = os.getenv('YOLO_MODEL', 'yolov8n.pt')
YOLO_CONFIDENCE_THRESHOLD = float(os.getenv('YOLO_CONFIDENCE', '0.5'))
YOLO_NMS_THRESHOLD = float(os.getenv('YOLO_NMS', '0.45'))

# ============================================================================
# PERFORMANCE TARGETS
# ============================================================================

# Target performance metrics
TARGET_FPS = int(os.getenv('TARGET_FPS', '20'))  # Minimum acceptable FPS
TARGET_MAX_CPU_PERCENT = float(os.getenv('TARGET_MAX_CPU', '70.0'))  # Max CPU usage
TARGET_MAX_MEMORY_MB = int(os.getenv('TARGET_MAX_MEMORY', '500'))  # Max memory usage

# ============================================================================
# LOGGING & DEBUG
# ============================================================================

# Enable detailed logging
ENABLE_PERFORMANCE_LOGGING = os.getenv('BEHAVIOR_ENABLE_LOGGING', 'False').lower() == 'true'
ENABLE_DEBUG_VISUALIZATION = os.getenv('BEHAVIOR_ENABLE_DEBUG', 'False').lower() == 'true'

# Log file paths
BEHAVIOR_LOG_DIR = os.getenv('BEHAVIOR_LOG_DIR', 'logs/behavior_analysis/')
BEHAVIOR_LOG_FILE = os.path.join(BEHAVIOR_LOG_DIR, 'behavior_analysis.log')

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_config():
    """Validate that all configuration values are within reasonable ranges"""
    issues = []
    
    # Check drowsiness settings
    if not (0.0 < DROWSINESS_EAR_THRESHOLD < 0.5):
        issues.append(f"Drowsiness EAR threshold {DROWSINESS_EAR_THRESHOLD} out of range (0.0-0.5)")
    
    # Check head pose thresholds
    if not (0 < HEAD_POSE_YAW_THRESHOLD < 90):
        issues.append(f"Head pose yaw threshold {HEAD_POSE_YAW_THRESHOLD} out of range (0-90)")
    if not (0 < HEAD_POSE_PITCH_THRESHOLD < 90):
        issues.append(f"Head pose pitch threshold {HEAD_POSE_PITCH_THRESHOLD} out of range (0-90)")
    
    # Check alert thresholds (in seconds)
    if ALERT_DROWSINESS_DURATION < 1.0:
        issues.append(f"Alert drowsiness duration {ALERT_DROWSINESS_DURATION}s too short")
    if ALERT_PHONE_USAGE_DURATION < 1.0:
        issues.append(f"Alert phone usage duration {ALERT_PHONE_USAGE_DURATION}s too short")
    
    # Check frame skip
    if BEHAVIOR_FRAME_SKIP < 1:
        issues.append(f"Frame skip {BEHAVIOR_FRAME_SKIP} must be >= 1")
    
    # Check resolution
    if BEHAVIOR_INPUT_HEIGHT < 100 or BEHAVIOR_INPUT_WIDTH < 100:
        issues.append(f"Input resolution {BEHAVIOR_INPUT_RESOLUTION} too small")
    
    # Log any issues
    if issues:
        print("[Config] Configuration Warnings:")
        for issue in issues:
            print(f"  - {issue}")
    
    return len(issues) == 0

# Validate on import
validate_config()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_attention_weights():
    """Get attention score calculation weights"""
    return ATTENTION_WEIGHTS.copy()

def get_alert_thresholds():
    """Get all alert thresholds as a dictionary"""
    return {
        'drowsiness': ALERT_DROWSINESS_DURATION,
        'looking_away': ALERT_LOOKING_AWAY_DURATION,
        'phone_usage': ALERT_PHONE_USAGE_DURATION,
        'posture': ALERT_BAD_POSTURE_DURATION,
        'absence': ALERT_ABSENCE_DURATION
    }

def get_detection_thresholds():
    """Get all detection thresholds as a dictionary"""
    return {
        'drowsiness_ear': DROWSINESS_EAR_THRESHOLD,
        'head_pose_yaw': HEAD_POSE_YAW_THRESHOLD,
        'head_pose_pitch': HEAD_POSE_PITCH_THRESHOLD,
        'phone_confidence': PHONE_DETECTION_CONFIDENCE,
        'posture_upright': POSTURE_UPRIGHT_THRESHOLD
    }

def print_config_summary():
    """Print a summary of current configuration"""
    print("\n" + "="*60)
    print("BEHAVIOR ANALYSIS CONFIGURATION SUMMARY")
    print("="*60)
    print(f"\nDetection Thresholds:")
    print(f"  Drowsiness EAR: {DROWSINESS_EAR_THRESHOLD}")
    print(f"  Head Pose Yaw: {HEAD_POSE_YAW_THRESHOLD}°")
    print(f"  Head Pose Pitch: {HEAD_POSE_PITCH_THRESHOLD}°")
    print(f"  Phone Detection Confidence: {PHONE_DETECTION_CONFIDENCE}")
    print(f"\nAlert Thresholds (seconds):")
    print(f"  Drowsiness: {ALERT_DROWSINESS_DURATION}s")
    print(f"  Looking Away: {ALERT_LOOKING_AWAY_DURATION}s")
    print(f"  Phone Usage: {ALERT_PHONE_USAGE_DURATION}s")
    print(f"  Bad Posture: {ALERT_BAD_POSTURE_DURATION}s")
    print(f"\nAttention Score Weights:")
    for component, weight in ATTENTION_WEIGHTS.items():
        print(f"  {component}: {weight*100:.1f}%")
    print(f"\nProcessing Optimization:")
    print(f"  Frame Skip: {BEHAVIOR_FRAME_SKIP}")
    print(f"  Input Resolution: {BEHAVIOR_INPUT_RESOLUTION}")
    print(f"  Target FPS: {TARGET_FPS}")
    print(f"  Target Max CPU: {TARGET_MAX_CPU_PERCENT}%")
    print(f"\nMediaPipe Settings:")
    print(f"  Face Mesh Max Faces: {MEDIAPIPE_FACE_MAX_FACES}")
    print(f"  Pose Model Complexity: {MEDIAPIPE_POSE_MODEL_COMPLEXITY}")
    print("="*60 + "\n")

# Print summary on first import if debug enabled
if ENABLE_DEBUG_VISUALIZATION:
    print_config_summary()
