# Phase 9: Configuration System - Quick Reference

**5-Minute Setup Guide**

---

## 📦 Files to Copy

Copy these 4 files to `/backend/app1/`:

```
✅ configuration_models.py     (450 lines) - Django models
✅ configuration_admin.py      (350 lines) - Admin interface  
✅ configuration_api.py        (500 lines) - REST API
✅ configuration_forms.py      (300 lines) - Web forms
```

---

## ⚡ Quick Setup (5 steps)

### 1️⃣ Create Migrations

```bash
cd backend
python manage.py makemigrations app1
python manage.py migrate app1
```

**Output expected:**
```
Operations to perform:
  Apply migrations for app1
    - Create model BehaviorConfig
    - Create model OptimizationConfig
    - Create model DetectorConfig
    - Create model ThresholdConfig
    - Create model ConfigurationAudit
```

### 2️⃣ Register Admin Classes

Open `/backend/app1/admin.py` and add:

```python
from .configuration_admin import (
    BehaviorConfigAdmin,
    OptimizationConfigAdmin,
    DetectorConfigAdmin,
    ThresholdConfigAdmin,
    ConfigurationAuditAdmin,
)
```

Classes already have `@admin.register()` decorators - no need to call `admin.site.register()`.

### 3️⃣ Add API Routes

Open `/backend/Project101/urls.py` and add:

```python
from app1.configuration_api import (
    BehaviorConfigViewSet,
    OptimizationConfigViewSet,
    DetectorConfigViewSet,
    ThresholdConfigViewSet,
    ConfigurationAuditViewSet,
)

# In your router registration:
router.register(r'config/behavior', BehaviorConfigViewSet)
router.register(r'config/optimization', OptimizationConfigViewSet)
router.register(r'config/detectors', DetectorConfigViewSet)
router.register(r'config/thresholds', ThresholdConfigViewSet)
router.register(r'config/audit', ConfigurationAuditViewSet)
```

### 4️⃣ Test Admin

```bash
python manage.py createsuperuser  # If no superuser exists
python manage.py runserver
```

Go to: `http://localhost:8000/admin/`

✅ Should see:
- System Configuration
- Optimization Configuration
- Detector Configuration  
- Alert Thresholds
- Configuration Audit Trail

### 5️⃣ Test API

```bash
# Get current settings
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/config/behavior/

# Update setting
curl -X PUT -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"system_enabled": false}' \
  http://localhost:8000/api/config/behavior/
```

✅ Should return configuration JSON with HTTP 200.

---

## 🎯 Main Features

### Django Admin
- Navigate to System Configuration
- Change FPS target, processing mode, logging
- All changes auto-logged to audit trail
- Color-coded status indicators

### REST API
- `/api/config/behavior/` - Get/update system settings
- `/api/config/optimization/` - Get/update optimization
- `/api/config/detectors/` - Get/update detector params
- `/api/config/thresholds/` - Get/update alert thresholds
- `/api/config/audit/` - View change history

### Code Usage
```python
from app1.configuration_models import (
    get_behavior_config,
    get_optimization_config,
    get_detector_config,
)

# Use in any view/service
config = get_behavior_config()
if config.system_enabled:
    print(f"FPS target: {config.target_fps}")
```

---

## 📊 Configuration Models

### BehaviorConfig
**System-wide settings** (One record, pk=1)

```
- system_enabled: Boolean
- processing_mode: realtime/batch/hybrid
- min_fps, target_fps: 5-60
- store_events, store_scores, store_alerts: Boolean
- enable_alerts: Boolean
- alert_via_email, alert_via_websocket: Boolean
- log_level: DEBUG/INFO/WARNING/ERROR
- log_to_file: Boolean
```

### OptimizationConfig
**Performance settings** (One record, pk=1)

```
- frame_skip_enabled: Boolean
- initial_skip_rate, max_skip_rate: 1-10
- resolution_adapt_enabled: Boolean
- cpu_threshold_low, mid, high: 0-100
- memory_pool_enabled: Boolean
- memory_pool_size: 5-50
- cpu_throttle_enabled: Boolean
- cpu_throttle_max: 50-95
- cache_enabled: Boolean
- cache_ttl_scores, alerts, stats: seconds
```

### DetectorConfig
**Per-detector settings** (5 records - one per detector)

```
Detector Types:
- drowsiness
- head_pose
- phone
- posture
- absence

Common Fields:
- detector_type: Enumerated
- enabled: Boolean
- confidence_threshold: 0-1.0
- min_consecutive_frames: 1-30
- specific_fields: Based on detector type
```

### ThresholdConfig
**Alert thresholds** (One record, pk=1)

```
Attention Level:
- attention_excellent_threshold: ≥ score
- attention_good_threshold: ≥ score
- attention_fair_threshold: ≥ score
- attention_poor_threshold: ≥ score

Component Alerts:
- drowsiness_alert_threshold: 0-100
- phone_usage_alert_threshold: 0-100
- distraction_alert_threshold: 0-100
- posture_alert_threshold: 0-100
- absence_alert_threshold: 0-100
- drowsiness_alert_duration: seconds
```

### ConfigurationAudit
**Change tracking** (Append-only log)

```
- config_type: system/optimization/detector/threshold
- changed_by: FK to User
- changed_field: Field name
- old_value: Previous value
- new_value: New value
- reason: Why it changed
- created_at: When it changed
```

---

## 🔌 API Endpoints Quick Reference

### Behavior Configuration

```
GET  /api/config/behavior/
     → Current system configuration

PUT  /api/config/behavior/
PATCH /api/config/behavior/
     → Update settings (staff only)

GET  /api/config/behavior/options/
     → Available processing modes
```

### Optimization Configuration

```
GET  /api/config/optimization/
     → Current optimization settings

PUT  /api/config/optimization/
PATCH /api/config/optimization/
     → Update settings (staff only)

GET  /api/config/optimization/presets/
     → Available optimization presets

POST /api/config/optimization/apply_preset/
     → Apply preset (conservative/balanced/aggressive)
```

### Detector Configuration

```
GET  /api/config/detectors/
     → List all detectors

GET  /api/config/detectors/{detector_type}/
     → Get specific detector config

PUT  /api/config/detectors/{detector_type}/
PATCH /api/config/detectors/{detector_type}/
     → Update detector (staff only)
```

### Thresholds

```
GET  /api/config/thresholds/
     → Current alert thresholds

PUT  /api/config/thresholds/
PATCH /api/config/thresholds/
     → Update thresholds (staff only)
```

### Audit Trail

```
GET  /api/config/audit/
     → List all changes (paginated)

GET  /api/config/audit/statistics/
     → Change statistics by type/user
```

---

## 💡 Usage Examples

### Example 1: Check System Status

```python
from app1.configuration_models import get_behavior_config

config = get_behavior_config()
print(f"System enabled: {config.system_enabled}")
print(f"Target FPS: {config.target_fps}")
print(f"Processing mode: {config.processing_mode}")
```

### Example 2: Apply Optimization Preset

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"preset": "aggressive"}' \
  http://localhost:8000/api/config/optimization/apply_preset/
```

### Example 3: Update Detector Confidence

```bash
curl -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confidence_threshold": 0.85}' \
  http://localhost:8000/api/config/detectors/drowsiness/
```

### Example 4: View Recent Changes

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/config/audit/?limit=10
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Migrations created successfully
- [ ] `python manage.py migrate` runs without errors
- [ ] Admin interface loads
- [ ] Can view System Configuration in admin
- [ ] Can view Optimization Configuration in admin
- [ ] Can view Detectors in admin
- [ ] Can view Alert Thresholds in admin
- [ ] Can view Audit Trail in admin
- [ ] API endpoints return JSON (200 OK)
- [ ] Can modify settings and see audit logs
- [ ] Configuration loads correctly in Python code

---

## 🐛 Troubleshooting

### Issue: Migration errors

**Solution:** Ensure Django installed and database initialized
```bash
python manage.py migrate auth
python manage.py makemigrations app1
python manage.py migrate app1
```

### Issue: Admin interface shows import errors

**Solution:** Verify all configuration files in `/backend/app1/`:
```bash
ls app1/configuration_*
```

Should show all 4 files.

### Issue: API returns 403 Forbidden

**Solution:** Ensure user is staff/admin:
```python
from django.contrib.auth.models import User
user = User.objects.get(username='admin')
user.is_staff = True
user.save()
```

### Issue: Configuration not applied to optimizer

**Solution:** Load config in your optimization code:
```python
from app1.configuration_models import get_optimization_config
from app1.performance_optimizer import AdaptiveOptimizer

config = get_optimization_config()
optimizer = AdaptiveOptimizer()
optimizer.frame_skipper.set_skip_rate(config.initial_skip_rate)
```

---

## 🚀 Next Steps

1. ✅ Copy files to `backend/app1/`
2. ✅ Run migrations
3. ✅ Register admin classes
4. ✅ Add API routes
5. ✅ Test admin interface
6. ✅ Test API endpoints
7. → **Integrate with Phase 8 optimizer** (see PHASE9_INTEGRATION_GUIDE.md)
8. → Create web forms and templates
9. → Deploy to production

---

## 📞 Support

**Files Included:**
- `PHASE9_CONFIGURATION_GUIDE.md` - Complete documentation
- `PHASE9_QUICK_REFERENCE.md` - This file (5-min setup)
- `PHASE9_INTEGRATION_GUIDE.md` - Phase 8 integration details

**Questions?**
Check the complete guide for detailed explanations of each component.

---

**Ready to go! Start with Step 1.** 🚀

