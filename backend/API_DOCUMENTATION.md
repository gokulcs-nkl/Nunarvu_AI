# Phase 10: Complete API Documentation

**Face Attendance & Behavior Analysis System - API Reference**

Version: 1.0  
Date: May 14, 2026  
Status: Complete

---

## 📚 API Overview

### Base URL
```
http://localhost:8000
```

### API Endpoints
```
/api/             - DRF API root
/api/config/      - Configuration management
/api/admin/       - Django admin API
```

### Authentication
```
Bearer Token (JWT)
Session-based auth
```

### Content Type
```
application/json
```

---

## 🔐 Authentication

### JWT Token Authentication

**Get Token:**
```bash
POST /api/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Use Token:**
```bash
GET /api/config/behavior/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Session Authentication

**Login:**
```bash
POST /login/
Content-Type: application/x-www-form-urlencoded

username=your_username&password=your_password
```

**Use Session:**
```bash
GET /api/config/behavior/
Cookie: sessionid=abc123def456...
```

---

## ⚙️ Configuration Management API

### 1. Behavior Configuration

#### Get Current Behavior Configuration
```
GET /api/config/behavior/
```

**Response (200 OK):**
```json
{
  "id": 1,
  "system_enabled": true,
  "processing_mode": "realtime",
  "min_fps": 15,
  "target_fps": 30,
  "store_events": true,
  "store_scores": true,
  "store_alerts": true,
  "enable_alerts": true,
  "alert_via_email": false,
  "alert_via_websocket": true,
  "log_level": "INFO",
  "log_to_file": true,
  "created_at": "2026-05-14T10:00:00Z",
  "updated_at": "2026-05-14T10:00:00Z",
  "updated_by": "admin"
}
```

#### Update Behavior Configuration (Full)
```
PUT /api/config/behavior/
Content-Type: application/json
Authorization: Bearer <token>

{
  "system_enabled": true,
  "processing_mode": "realtime",
  "min_fps": 20,
  "target_fps": 60,
  "store_events": true,
  "store_scores": true,
  "store_alerts": true,
  "enable_alerts": true,
  "log_level": "DEBUG"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "system_enabled": true,
  "processing_mode": "realtime",
  "min_fps": 20,
  "target_fps": 60,
  ...
}
```

#### Update Behavior Configuration (Partial)
```
PATCH /api/config/behavior/
Content-Type: application/json
Authorization: Bearer <token>

{
  "target_fps": 60
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "target_fps": 60,
  ...
}
```

#### Get Available Processing Modes
```
GET /api/config/behavior/options/
```

**Response (200 OK):**
```json
{
  "processing_modes": [
    {
      "value": "realtime",
      "label": "Real-time"
    },
    {
      "value": "batch",
      "label": "Batch Processing"
    },
    {
      "value": "hybrid",
      "label": "Hybrid (Real-time + Batch)"
    }
  ]
}
```

---

### 2. Optimization Configuration

#### Get Current Optimization Configuration
```
GET /api/config/optimization/
```

**Response (200 OK):**
```json
{
  "id": 1,
  "frame_skip_enabled": true,
  "initial_skip_rate": 1,
  "max_skip_rate": 5,
  "resolution_adapt_enabled": true,
  "cpu_threshold_low": 30.0,
  "cpu_threshold_mid": 60.0,
  "cpu_threshold_high": 85.0,
  "memory_pool_enabled": true,
  "memory_pool_size": 10,
  "cpu_throttle_enabled": true,
  "cpu_throttle_max": 80.0,
  "cache_enabled": true,
  "cache_ttl_scores": 300,
  "cache_ttl_alerts": 120,
  "cache_ttl_stats": 600,
  "created_at": "2026-05-14T10:00:00Z",
  "updated_at": "2026-05-14T10:00:00Z"
}
```

#### Update Optimization Configuration
```
PATCH /api/config/optimization/
Content-Type: application/json
Authorization: Bearer <token>

{
  "frame_skip_enabled": true,
  "initial_skip_rate": 2,
  "max_skip_rate": 8
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "initial_skip_rate": 2,
  "max_skip_rate": 8,
  ...
}
```

#### Get Available Optimization Presets
```
GET /api/config/optimization/presets/
```

**Response (200 OK):**
```json
{
  "presets": [
    {
      "name": "conservative",
      "description": "Minimal optimization - process most frames",
      "settings": {
        "frame_skip_enabled": true,
        "initial_skip_rate": 1,
        "max_skip_rate": 2,
        "resolution_adapt_enabled": false,
        "cpu_throttle_enabled": false
      }
    },
    {
      "name": "balanced",
      "description": "Automatic optimization with adaptive strategies",
      "settings": {
        "frame_skip_enabled": true,
        "initial_skip_rate": 1,
        "max_skip_rate": 5,
        "resolution_adapt_enabled": true,
        "cpu_throttle_enabled": true
      }
    },
    {
      "name": "aggressive",
      "description": "Maximum optimization - reduced processing load",
      "settings": {
        "frame_skip_enabled": true,
        "initial_skip_rate": 3,
        "max_skip_rate": 10,
        "resolution_adapt_enabled": true,
        "cpu_throttle_enabled": true,
        "cpu_threshold_high": 70.0,
        "memory_pool_size": 20
      }
    }
  ]
}
```

#### Apply Optimization Preset
```
POST /api/config/optimization/apply_preset/
Content-Type: application/json
Authorization: Bearer <token>

{
  "preset": "aggressive"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "frame_skip_enabled": true,
  "initial_skip_rate": 3,
  "max_skip_rate": 10,
  "resolution_adapt_enabled": true,
  "cpu_throttle_enabled": true,
  "message": "Preset 'aggressive' applied successfully"
}
```

---

### 3. Detector Configuration

#### List All Detectors
```
GET /api/config/detectors/
```

**Response (200 OK):**
```json
{
  "count": 5,
  "detectors": [
    {
      "id": 1,
      "detector_type": "drowsiness",
      "enabled": true,
      "confidence_threshold": 0.85,
      "min_consecutive_frames": 3,
      "eye_aspect_ratio_threshold": 0.2
    },
    {
      "id": 2,
      "detector_type": "head_pose",
      "enabled": true,
      "confidence_threshold": 0.75,
      "head_pose_yaw_threshold": 45.0,
      "head_pose_pitch_threshold": 35.0
    },
    {
      "id": 3,
      "detector_type": "phone",
      "enabled": true,
      "confidence_threshold": 0.8,
      "phone_presence_threshold": 0.5
    },
    {
      "id": 4,
      "detector_type": "posture",
      "enabled": true,
      "confidence_threshold": 0.75,
      "posture_confidence_threshold": 0.7
    },
    {
      "id": 5,
      "detector_type": "absence",
      "enabled": true,
      "confidence_threshold": 0.85
    }
  ]
}
```

#### Get Specific Detector
```
GET /api/config/detectors/drowsiness/
```

**Response (200 OK):**
```json
{
  "id": 1,
  "detector_type": "drowsiness",
  "enabled": true,
  "confidence_threshold": 0.85,
  "min_consecutive_frames": 3,
  "eye_aspect_ratio_threshold": 0.2,
  "created_at": "2026-05-14T10:00:00Z",
  "updated_at": "2026-05-14T10:00:00Z"
}
```

#### Update Detector Configuration
```
PATCH /api/config/detectors/drowsiness/
Content-Type: application/json
Authorization: Bearer <token>

{
  "confidence_threshold": 0.9,
  "eye_aspect_ratio_threshold": 0.25
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "detector_type": "drowsiness",
  "confidence_threshold": 0.9,
  "eye_aspect_ratio_threshold": 0.25,
  ...
}
```

---

### 4. Threshold Configuration

#### Get Current Thresholds
```
GET /api/config/thresholds/
```

**Response (200 OK):**
```json
{
  "id": 1,
  "attention_excellent_threshold": 80,
  "attention_good_threshold": 60,
  "attention_fair_threshold": 40,
  "attention_poor_threshold": 20,
  "drowsiness_alert_threshold": 50,
  "phone_usage_alert_threshold": 40,
  "distraction_alert_threshold": 60,
  "posture_alert_threshold": 70,
  "absence_alert_threshold": 90,
  "drowsiness_alert_duration": 300,
  "created_at": "2026-05-14T10:00:00Z",
  "updated_at": "2026-05-14T10:00:00Z"
}
```

#### Update Thresholds
```
PATCH /api/config/thresholds/
Content-Type: application/json
Authorization: Bearer <token>

{
  "attention_poor_threshold": 25,
  "drowsiness_alert_threshold": 55
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "attention_poor_threshold": 25,
  "drowsiness_alert_threshold": 55,
  ...
}
```

---

### 5. Configuration Audit Trail

#### List All Configuration Changes
```
GET /api/config/audit/?limit=50&offset=0
```

**Response (200 OK):**
```json
{
  "count": 127,
  "next": "http://localhost:8000/api/config/audit/?limit=50&offset=50",
  "previous": null,
  "results": [
    {
      "id": 1,
      "config_type": "optimization",
      "changed_by": "admin",
      "changed_field": "initial_skip_rate",
      "old_value": "1",
      "new_value": "2",
      "reason": "Performance tuning for peak hours",
      "created_at": "2026-05-14T10:30:00Z"
    },
    {
      "id": 2,
      "config_type": "system",
      "changed_by": "staff_user",
      "changed_field": "system_enabled",
      "old_value": "true",
      "new_value": "false",
      "reason": "System maintenance",
      "created_at": "2026-05-14T09:00:00Z"
    }
  ]
}
```

#### Get Configuration Change Statistics
```
GET /api/config/audit/statistics/
```

**Response (200 OK):**
```json
{
  "total_changes": 127,
  "by_type": {
    "system": 23,
    "optimization": 45,
    "detector": 38,
    "threshold": 21
  },
  "by_user": {
    "admin": 85,
    "staff_user": 42
  },
  "last_change": {
    "timestamp": "2026-05-14T10:30:00Z",
    "user": "admin",
    "type": "optimization"
  }
}
```

#### Filter Audit Trail by Type
```
GET /api/config/audit/?config_type=optimization&limit=20
```

---

## 🔄 Common Request/Response Patterns

### Error Responses

**400 Bad Request:**
```json
{
  "detail": "Invalid request data",
  "errors": {
    "target_fps": ["Ensure this value is >= 5."]
  }
}
```

**401 Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**404 Not Found:**
```json
{
  "detail": "Not found."
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error"
}
```

---

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request succeeded |
| 201 | Created - Resource created |
| 204 | No Content - Successful deletion |
| 400 | Bad Request - Invalid data |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Permission denied |
| 404 | Not Found - Resource not found |
| 500 | Server Error |

---

## 📊 API Usage Examples

### Example 1: Get Current System Status
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/config/behavior/ | jq
```

### Example 2: Increase FPS Target
```bash
curl -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_fps": 60}' \
  http://localhost:8000/api/config/behavior/ | jq
```

### Example 3: Apply Aggressive Optimization
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"preset": "aggressive"}' \
  http://localhost:8000/api/config/optimization/apply_preset/ | jq
```

### Example 4: Update Drowsiness Detector
```bash
curl -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confidence_threshold": 0.9}' \
  http://localhost:8000/api/config/detectors/drowsiness/ | jq
```

### Example 5: View Configuration Changes
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/config/audit/?limit=10" | jq
```

---

## 🔗 Pagination

Configuration audit and list endpoints support pagination:

```bash
# Get first 50 records
GET /api/config/audit/?limit=50&offset=0

# Get next 50 records
GET /api/config/audit/?limit=50&offset=50

# Response includes:
{
  "count": 127,           # Total records
  "next": "http://...",   # URL to next page
  "previous": null,       # URL to previous page
  "results": [...]        # Actual records
}
```

---

## 📋 Rate Limiting

**Current Limits:**
- Configuration reads: Unlimited (cached)
- Configuration writes: 10 per minute per user
- Audit queries: 5 per minute

---

## 🔗 Related Resources

- [Configuration Guide](PHASE9_CONFIGURATION_GUIDE.md)
- [Integration Guide](PHASE9_INTEGRATION_GUIDE.md)
- [Testing Guide](PHASE10_TESTING_GUIDE.md)

---

**API Documentation Complete** ✅

