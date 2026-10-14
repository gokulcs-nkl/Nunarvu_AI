# Dashboard Integration Guide

## Installation & Setup

### 1. Dashboard Files Created

The following files have been created for the behavior analysis dashboard:

```
Templates:
├── behavior_dashboard.html          # Main real-time dashboard
├── student_attention_list.html      # Student attention monitoring
├── behavior_analytics.html          # Analytics and reporting
└── DASHBOARD_GUIDE.md              # User documentation

Static Files:
├── css/behavior_dashboard.css       # Styling for all dashboard pages
└── js/behavior_dashboard.js         # Core dashboard functionality

Views & URLs:
├── behavior_dashboard_views.py      # Django view classes
├── behavior_dashboard_urls.py       # URL routing configuration
└── urls.py                          # (Modified to include dashboard URLs)
```

### 2. Required Django Configuration

Ensure the following are configured in `Project101/settings.py`:

```python
# Template context processors
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Authentication
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
```

### 3. Required Python Dependencies

Add these to `requirements.txt` if not already present:

```
Django>=5.0.0
djangorestframework>=3.14.0
django-cors-headers>=4.2.0
Chart.js>=3.9.1
bootstrap>=5.3.0
mediapipe>=0.10.0
ultralytics>=8.0.0
torch>=2.0.0
numpy>=1.24.0
```

### 4. URL Configuration

The dashboard URLs are automatically included in the app's URL configuration:

```python
# app1/urls.py includes:
path('', include('app1.behavior_dashboard_urls'))

# Available URLs:
/behavior-dashboard/        # Main real-time dashboard
/student-attention/         # Student attention list
/behavior-analytics/        # Analytics and reporting
```

### 5. Required API Endpoints

The dashboard requires the following API endpoints (all created in Phase 6):

```
GET  /api/behavior-stats/classroom/
GET  /api/behavior-stats/student/
GET  /api/behavior-stats/daily/
GET  /api/attention-scores/latest_scores/
GET  /api/attention-scores/by_student/
GET  /api/behaviour-alerts/
GET  /api/behaviour-alerts/unacknowledged/
GET  /api/behaviour-alerts/statistics/
GET  /api/behaviour-events/
GET  /api/student-seats/
```

---

## Features Overview

### Real-Time Dashboard (`/behavior-dashboard/`)

**Live Features:**
- Real-time video stream with student overlays
- Attention score visualization
- Critical alert feed
- System performance metrics
- Recording and screenshot capabilities

**Polling Interval:** 3 seconds
**Performance Targets:**
- Video FPS: 15-20
- Processing time: <30ms per frame
- CPU usage: <70%
- Memory: <500MB

**New Features Included:**
1. **Video Overlay Rendering** - Canvas-based drawing of:
   - Student face bounding boxes
   - Student names
   - Attention scores with color coding
   - Alert indicators

2. **Real-time Statistics** - Updated every 3 seconds:
   - Total/active students count
   - Active alerts count
   - Average attention score
   - Processing metrics

3. **Critical Alert System** - Color-coded by severity:
   - High (Red) - Drowsiness >10s, Phone Usage >5s
   - Medium (Yellow) - Looking away >25s
   - Low (Blue) - Bad posture >15s

4. **System Health Monitor**:
   - Processing time gauge
   - CPU/Memory usage indicators
   - Frame queue visualization
   - Thread health status

### Student Attention List (`/student-attention/`)

**Real-Time Monitoring:**
- Live table showing all students
- Sorted by attention score (lowest first by default)
- Color-coded status indicators
- Individual component scores

**New Features:**
1. **Smart Sorting** - 4 sort options:
   - Lowest attention first (default)
   - Highest attention first
   - Most alerts first
   - Alphabetical by name

2. **Advanced Filtering**:
   - By classroom
   - By alert type (drowsiness, phone, posture, etc.)
   - By time range (1h, 4h, 24h, 7d)
   - By attention level (excellent to critical)

3. **Student Detail Modal** - Deep-dive analysis:
   - Radar chart of 5 components
   - Recent alert history
   - Recent behavior events
   - Custom time range selection

4. **Data Export** - Download as:
   - CSV for Excel/Sheets
   - JSON for data analysis
   - Automatic file naming with timestamp

5. **Responsive Pagination** - 10 students per page
   - Dynamic page count
   - Quick navigation
   - Row count display

### Analytics Dashboard (`/behavior-analytics/`)

**Comprehensive Analytics:**
- Time-series charts showing trends
- Distribution analysis by behavior type
- Component breakdown (5-axis radar)
- Daily activity heatmaps

**New Features:**
1. **Advanced Date Filtering**:
   - Start/end date pickers
   - Quick preset ranges (1h, 4h, 24h, 7d)
   - Classroom and student filters
   - Behavior type filters

2. **Key Metrics Display**:
   - Average attention score
   - Total alerts count
   - Drowsiness rate (%)
   - Phone usage rate (%)

3. **Multiple Chart Types**:
   - **Trend Line Chart** - Attention over time
   - **Distribution Chart** - Alerts by type
   - **Radar Chart** - Component comparison
   - **Heatmap** - Hourly activity intensity

4. **Event Log Table**:
   - Complete event history
   - Sortable and filterable
   - Event type filtering
   - Detailed metadata display

5. **Export Capabilities**:
   - CSV export for spreadsheets
   - JSON export for analysis
   - PDF report generation
   - Print-friendly formatting

---

## Advanced Features

### Dark Mode
- **Toggle Button** - Moon icon in navigation
- **Persistent** - Preference saved to localStorage
- **Auto-applied** - All pages support dark mode
- **Print-optimized** - Light mode for printing

### Keyboard Shortcuts
```
Space  - Pause/Resume live updates
S      - Capture screenshot
R      - Toggle recording
?      - Show keyboard shortcuts help
D      - Toggle dark mode
```

### Notifications System
- **Toast notifications** - Top-right corner
- **Auto-dismiss** - After 5 seconds
- **Color-coded** - By message type
- **Sound alerts** - For critical events

### Connection Monitoring
- **Status indicator** - Green/Red connected/disconnected
- **Auto-reconnect** - Handles temporary failures
- **Fallback polling** - If WebSocket unavailable
- **Error handling** - Graceful degradation

---

## Performance Optimization

### Frame Processing
- **Lazy loading** - MediaPipe models load on first frame
- **Resolution reduction** - 480p analysis for speed
- **Frame skipping** - Process every Nth frame
- **Queue-based** - Non-blocking frame submission

### Chart Rendering
- **Limit data points** - Show only last 100 events
- **Debounced updates** - Group multiple updates
- **Canvas rendering** - GPU acceleration when available
- **Virtualization** - Lazy render table rows

### API Calls
- **Polling intervals** - 3 second default (configurable)
- **Request batching** - Combine related queries
- **Caching** - Client-side response caching
- **Pagination** - Limit API response size

---

## Customization Guide

### Change Polling Interval
Edit `behavior_dashboard.js`:
```javascript
DashboardState.updateInterval = 3000; // Change to desired milliseconds
```

### Adjust Color Scheme
Edit `behavior_dashboard.css`:
```css
:root {
    --primary-color: #4f46e5;
    --danger-color: #dc3545;
    --success-color: #10b981;
    /* ... other colors ... */
}
```

### Modify Chart Types
Edit `behavior_dashboard.js` in `initializeAnalyticsCharts()`:
```javascript
// Change Chart.js type (line, bar, pie, doughnut, radar, etc.)
DashboardState.charts.attentionTrend = new Chart(ctx, {
    type: 'line', // Change this
    // ...
});
```

### Add Custom Metrics
1. Create new metric card in HTML template
2. Add fetch call to API endpoint
3. Update metric card with data

---

## Troubleshooting

### Dashboard Not Loading
**Check:**
1. Django server is running: `python manage.py runserver`
2. Static files collected: `python manage.py collectstatic`
3. Templates directory exists and has files
4. LoginRequiredMixin authentication

**Solution:**
```bash
python manage.py collectstatic --noinput
python manage.py runserver
```

### No Data in Charts
**Check:**
1. API endpoints are working: visit `/api/behavior-stats/classroom/`
2. Database has records from behavior module
3. Behavior thread is running
4. Students are being tracked

**Solution:**
```bash
python manage.py shell
from app1.models import AttentionScore
print(AttentionScore.objects.count())  # Should be > 0
```

### Alerts Not Showing
**Check:**
1. Thresholds in config.py are reasonable
2. Behavior events are being logged
3. API endpoint `/api/behaviour-alerts/unacknowledged/` returns data
4. Browser console for JavaScript errors

**Solution:**
```bash
python manage.py shell
from app1.models import BehaviourAlert
print(BehaviourAlert.objects.count())
```

### Charts Not Rendering
**Check:**
1. Chart.js library loaded (check DevTools Network tab)
2. Canvas element exists in DOM
3. Data passed to chart is valid
4. No JavaScript errors in console

**Solution:**
```javascript
// In browser console
console.log(DashboardState.charts);  // Check if charts exist
console.log(Chart);  // Check if Chart.js loaded
```

### Performance Issues
**Solutions:**
1. Increase polling interval in `behavior_dashboard.js`
2. Reduce chart data points
3. Enable frame skipping in behavior config
4. Close unused browser tabs

---

## Testing the Dashboard

### Quick Test
```bash
# 1. Start Django server
python manage.py runserver

# 2. Create test user
python manage.py shell
from django.contrib.auth.models import User
User.objects.create_user('teacher', 'teacher@test.com', 'password')

# 3. Login and navigate to:
# http://localhost:8000/behavior-dashboard/
# http://localhost:8000/student-attention/
# http://localhost:8000/behavior-analytics/
```

### Load Testing
```bash
# Install Apache Bench
apt-get install apache2-utils

# Test dashboard endpoint
ab -n 100 -c 10 http://localhost:8000/behavior-dashboard/

# Test API endpoints
ab -n 1000 -c 50 http://localhost:8000/api/behavior-stats/student/
```

### Browser DevTools
- **Console (F12)** - Check for JavaScript errors
- **Network tab** - Monitor API requests
- **Performance tab** - Profile rendering
- **Storage tab** - Check localStorage settings

---

## Browser Support

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome | ✅ Full | Recommended |
| Firefox | ✅ Full | Full support |
| Edge | ✅ Full | Modern Edge |
| Safari | ✅ Full | Safari 14+ |
| IE 11 | ❌ No | Not supported |

---

## Security Considerations

1. **Authentication** - All pages require login via `LoginRequiredMixin`
2. **Authorization** - Add permissions check for teacher/admin only
3. **HTTPS** - Use in production with `SESSION_COOKIE_SECURE = True`
4. **CORS** - Restrict API access to same origin
5. **Rate Limiting** - Add `django-ratelimit` for API endpoints

---

## Production Deployment

### Checklist
- [ ] DEBUG = False in settings.py
- [ ] ALLOWED_HOSTS configured
- [ ] STATIC_ROOT collected
- [ ] Database migrated
- [ ] HTTPS enabled
- [ ] SECRET_KEY rotated
- [ ] EMAIL configured for alerts
- [ ] Logging configured
- [ ] Monitoring set up
- [ ] Backup strategy

### Performance Settings
```python
# settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

---

## Version Information

- **Dashboard Version:** 1.0
- **Created:** May 2026
- **Django Version:** 5.0.7
- **Bootstrap Version:** 5.3.0
- **Chart.js Version:** 3.9.1

---

## Support & Documentation

- Main README: `README.md`
- API Docs: Available at `/api/docs/`
- User Guide: `DASHBOARD_GUIDE.md`
- Architecture: `BEHAVIOR_ANALYSIS_README.md`

---

**For questions or issues, contact the development team.**
