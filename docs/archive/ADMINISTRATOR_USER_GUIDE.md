# Administrator User Guide

**Face Attendance & Behavior Analysis System - Admin Manual**

Version: 1.0  
Date: May 14, 2026  
Audience: System Administrators, Instructors, Support Staff

---

## 📖 Table of Contents

1. [Getting Started](#getting-started)
2. [System Dashboard](#system-dashboard)
3. [Configuration Management](#configuration-management)
4. [Student Management](#student-management)
5. [Attendance Tracking](#attendance-tracking)
6. [Behavior Monitoring](#behavior-monitoring)
7. [Reports & Analytics](#reports--analytics)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Accessing the System

**Web URL:**
```
http://localhost:8000/admin/
```

**Login Credentials:**
- Username: Your username
- Password: Your password
- First time? Contact your system administrator

### System Requirements

- **Browser:** Chrome, Firefox, Safari, Edge (latest version)
- **Connection:** Stable internet (minimum 5 Mbps recommended)
- **Device:** Desktop or laptop (tablet may have limited functionality)

### Dashboard Overview

After logging in, you'll see:
- Quick status of active classrooms
- Recent attendance records
- Current alerts and notifications
- System health indicators

---

## System Dashboard

### Main Dashboard View

**Location:** Home page after login

**Shows:**
- 🔴 Active classrooms with number of students
- 👁️ Students marked as drowsy/distracted
- 📞 Phone usage detections
- ⚠️ Alert summary
- 📊 Today's attendance statistics

### Navigation Menu

**Left Sidebar:**
- System Configuration
- Optimization Configuration
- Detector Configuration
- Alert Thresholds
- Configuration Audit Trail
- Students
- Attendance Records
- Behavior Events
- Alerts
- Reports

### Quick Actions

**Top Right Menu:**
- 👤 Profile - View/edit your account
- 🔔 Notifications - See recent alerts
- ⚙️ Settings - System preferences
- 🚪 Logout - Exit system

---

## Configuration Management

### 1. System Configuration

**Purpose:** Control overall system behavior and logging

**Access:** Admin → System Configuration

**What You Can Change:**

| Setting | Options | Default | Effect |
|---------|---------|---------|--------|
| System Enabled | On/Off | On | Enable/disable entire system |
| Processing Mode | Realtime/Batch/Hybrid | Realtime | How frames are processed |
| Minimum FPS | 5-60 | 15 | Minimum acceptable frame rate |
| Target FPS | 5-60 | 30 | Desired frame rate |
| Store Events | On/Off | On | Save behavior events to database |
| Store Scores | On/Off | On | Save attention scores |
| Store Alerts | On/Off | On | Save alert notifications |
| Enable Alerts | On/Off | On | Send alert notifications |
| Alert via Email | On/Off | Off | Send email notifications |
| Alert via WebSocket | On/Off | On | Real-time alerts in dashboard |
| Log Level | DEBUG/INFO/WARN/ERROR | INFO | Logging verbosity |
| Log to File | On/Off | Off | Save logs to file |

**How to Change:**
1. Click "System Configuration"
2. Modify desired settings
3. Click "Save"
4. Setting applied immediately (no restart needed)
5. Change logged in audit trail

### 2. Optimization Configuration

**Purpose:** Tune system performance for different hardware

**Access:** Admin → Optimization Configuration

**Three Quick Presets:**

#### Conservative (Highest Accuracy)
✅ Best for: High-end servers, small classrooms
- Minimal frame skipping
- Full resolution processing
- Maximum accuracy
- Higher CPU/memory usage

**Apply:** Click "Conservative" preset, then Save

#### Balanced (Recommended)
✅ Best for: Standard hardware, typical use
- Smart frame skipping
- Adaptive resolution
- Good accuracy & performance
- Auto-adjusting

**Apply:** Click "Balanced" preset, then Save

#### Aggressive (Maximum Performance)
✅ Best for: Low-end hardware, large classrooms
- Heavy frame skipping
- Reduced resolution
- Lower accuracy but responsive
- Minimal resource usage

**Apply:** Click "Aggressive" preset, then Save

**Manual Tuning:**

| Setting | Range | Effect |
|---------|-------|--------|
| Frame Skip Rate | 1-10 | How many frames to skip (higher = faster but less accurate) |
| Resolution Scale | 0.33-1.0 | Video resolution multiplier (lower = faster) |
| CPU Threshold High | 50-95% | When to apply aggressive optimization |
| Memory Pool Size | 5-50 | Number of pre-allocated buffers |
| Cache TTL | 10-1800 sec | How long to cache results |

**When to Adjust:**
- System running slowly: Try "Aggressive" preset
- Missing detections: Try "Conservative" preset
- High CPU usage: Increase Frame Skip Rate
- Jittery video: Reduce Resolution Scale

### 3. Detector Configuration

**Purpose:** Configure sensitivity of each detection type

**Access:** Admin → Detector Configuration

**5 Detectors:**

#### Drowsiness Detection
- Eye Aspect Ratio Threshold: 0-1.0
- Confidence Threshold: 0-1.0
- Min Consecutive Frames: 1-30

**Adjust if:**
- Too many false positives: Increase threshold
- Missing actual drowsiness: Decrease threshold

#### Head Pose Detection (Looking Away)
- Yaw Threshold: 0-90° (head turn)
- Pitch Threshold: 0-90° (head up/down)
- Confidence Threshold: 0-1.0

**Adjust if:**
- Too sensitive to normal movements: Increase threshold
- Not detecting side-looking: Decrease threshold

#### Phone Usage Detection
- Phone Presence Threshold: 0-1.0
- Confidence Threshold: 0-1.0

**Adjust if:**
- Detecting hands as phones: Increase threshold
- Missing actual phones: Decrease threshold

#### Posture Detection
- Confidence Threshold: 0-1.0
- Posture Confidence: 0-1.0

**Adjust if:**
- Too many false alerts: Increase threshold
- Missing poor posture: Decrease threshold

#### Absence Detection
- Confidence Threshold: 0-1.0

**Adjust if:**
- False absence alerts: Increase threshold
- Not detecting actual absences: Decrease threshold

### 4. Alert Thresholds

**Purpose:** Configure when alerts are triggered

**Access:** Admin → Alert Thresholds

**Attention Level Scoring:**
```
Excellent: Score ≥ 80
Good:      Score ≥ 60
Fair:      Score ≥ 40
Poor:      Score < 40
```

**Component Alerts:**

| Alert Type | Threshold | Effect |
|-----------|-----------|--------|
| Drowsiness | 0-100 | Alert when drowsiness score exceeds |
| Phone Usage | 0-100 | Alert when phone detected |
| Distraction | 0-100 | Alert when attention too low |
| Posture | 0-100 | Alert when poor posture detected |
| Absence | 0-100 | Alert when student absent |

**Alert Duration:** How long alert stays active (seconds)

**Adjustment Guide:**
- Increasing threshold = fewer false alarms (less sensitive)
- Decreasing threshold = catches more issues (more sensitive)

### 5. Configuration Audit Trail

**Purpose:** View history of all configuration changes

**Access:** Admin → Configuration Audit Trail

**Information Shown:**
- What was changed (field name)
- Who changed it (username)
- When it was changed (date/time)
- Old value → New value
- Reason for change

**How to Use:**
1. Click date range to filter
2. Click user name to see their changes
3. Click config type to filter by system/optimization/detector/threshold
4. Scroll through complete change history

---

## Student Management

### Adding Students

**Steps:**
1. Go to Admin → Students
2. Click "Add Student"
3. Fill in details:
   - Name
   - Email
   - Phone
   - Class/Section
   - Student ID
4. Upload photo (optional but recommended)
5. Click "Save"

**Tips:**
- Use consistent naming format
- Ensure unique email addresses
- Include photo for better recognition

### Editing Student Info

1. Go to Admin → Students
2. Find student in list
3. Click student name to edit
4. Modify details
5. Click "Save"

### Deactivating Students

1. Go to Admin → Students
2. Select student
3. Check "Authorized" checkbox to toggle status
4. Click "Save"

**Note:** Deactivated students won't be tracked in attendance

### Bulk Import

**Coming in future update** - For now, add students individually

---

## Attendance Tracking

### Viewing Attendance

**Location:** Admin → Attendance Records

**Filters:**
- By Date (single day or date range)
- By Student (search by name)
- By Class/Section
- By Status (Present/Absent/Partial)

**Information Shown:**
- Student name
- Date
- Check-in time
- Check-out time
- Duration
- Status

### Attendance Report

**Steps:**
1. Go to Admin → Attendance Records
2. Set date range
3. Click "Generate Report"
4. Choose format (CSV, PDF, Excel)
5. Download

**Included in Report:**
- Attendance summary
- Total hours
- Percentage present
- Tardy records
- Absent days

### Manual Attendance Correction

**If System Error Occurs:**
1. Go to Admin → Attendance Records
2. Find incorrect record
3. Click to edit
4. Update times or status
5. Click "Save"
6. Reason required for audit trail

---

## Behavior Monitoring

### Real-Time Monitoring

**Location:** Dashboard → Monitoring Tab

**Shows Live:**
- 🟢 Students in frame
- 🟡 Attention indicators
- 🔴 Active alerts
- 📊 Statistics updating real-time

**Controls:**
- Select classroom (dropdown)
- Pause/resume video
- Adjust view
- Toggle detection overlays

### Behavior Events

**Location:** Admin → Behavior Events

**Event Types:**
- Drowsiness (eyes closing)
- Head Turn (looking away)
- Phone Usage (phone detected)
- Posture Change (slouching)
- Absence (left frame)

**Information:**
- Event type
- Student name
- Timestamp
- Duration
- Confidence score
- Metadata (e.g., eye aspect ratio)

### Attention Scores

**Location:** Admin → Attention Scores

**What is Attention Score:**
- Composite score (0-100)
- Based on:
  - Drowsiness (20%)
  - Head Pose (20%)
  - Phone Usage (20%)
  - Posture (20%)
  - Attendance (20%)

**Thresholds:**
- Excellent: 80-100
- Good: 60-79
- Fair: 40-59
- Poor: 0-39

### Alerts

**Location:** Admin → Alerts

**Alert Types:**
- Drowsiness: Student appears sleepy
- Distraction: Looking away
- Phone Usage: Phone detected
- Posture: Bad posture
- Absence: Not in frame

**Alert Status:**
- 🔴 Active: Alert currently happening
- 🟡 Acknowledged: Staff noted alert
- 🟢 Resolved: Issue resolved

**Managing Alerts:**
1. View alert details
2. Click "Acknowledge" to mark seen
3. Add notes if needed
4. Click "Resolve" when done

---

## Reports & Analytics

### Built-in Reports

**Available Reports:**
1. Daily Attendance Summary
2. Student Behavior Report
3. Classroom Statistics
4. Alert Summary
5. Performance Metrics

### Running a Report

**Steps:**
1. Go to Admin → Reports
2. Select report type
3. Choose date range
4. Select filters (class, student, etc.)
5. Click "Generate"
6. View or download

### Exporting Data

**Supported Formats:**
- CSV (Excel spreadsheet)
- PDF (Printable)
- JSON (Data import)

**How to Export:**
1. Generate desired report
2. Click "Export"
3. Choose format
4. Click download link

### Interpreting Reports

**Attendance Report:**
- Shows present/absent/late students
- Calculates attendance percentage
- Identifies patterns

**Behavior Report:**
- Shows behavior issues by student
- Lists events chronologically
- Includes severity levels

**Performance Report:**
- System uptime percentage
- CPU/memory usage
- Frame processing speed
- Detection accuracy

---

## Troubleshooting

### Common Issues

#### Issue: Students Not Being Detected

**Possible Causes & Solutions:**
1. Camera offline or no video feed
   - Check camera connection
   - Verify camera in settings
   - Test with test capture

2. Detection disabled
   - Check if detector is enabled
   - Check if system is enabled
   - Verify confidence thresholds

3. Poor lighting
   - Improve classroom lighting
   - Adjust camera angle
   - Check camera focus

**Steps:**
1. Go to Dashboard → Camera Status
2. Check camera connection
3. Go to Admin → Detector Configuration
4. Verify detector is enabled
5. Check confidence thresholds not too high

#### Issue: Too Many False Alerts

**Solutions:**
1. Increase detection thresholds
   - Higher = less sensitive
2. Increase consecutive frames requirement
3. Apply "Conservative" preset
4. Check detector enabled status

#### Issue: System Running Slow

**Solutions:**
1. Apply "Aggressive" optimization preset
2. Increase frame skip rate
3. Reduce resolution scale
4. Close unnecessary applications
5. Check CPU/memory usage

#### Issue: High CPU Usage

**Solutions:**
1. Lower resolution or skip more frames
2. Apply "Aggressive" preset
3. Reduce number of monitored classrooms
4. Check for background processes
5. Contact IT support if persists

#### Issue: Students Not in Attendance

**Solutions:**
1. Check if student is configured in system
2. Verify camera is capturing that area
3. Check if student is in frame
4. Verify attendance thresholds

### Getting Help

**For Support:**
1. Check this guide first
2. Contact your system administrator
3. Email: support@attendance.system
4. Phone: 1-800-ATTENDANCE

**Information to Provide:**
- Issue description
- When it occurred
- Student/classroom involved
- Screenshot if possible
- Recent changes made

### System Health Check

**Regular Maintenance:**
- Check configuration audit trail weekly
- Review alert patterns monthly
- Verify camera connections daily
- Backup data weekly
- Update system monthly

**Performance Monitoring:**
1. Go to Dashboard → System Status
2. Check CPU usage
3. Check Memory usage
4. Check Processing speed
5. Check Detection accuracy

---

## FAQ

**Q: Can I change settings while classroom is active?**
A: Yes! All changes apply immediately without restart.

**Q: Who can access the configuration?**
A: Only staff and administrators (users with staff status).

**Q: Are all changes logged?**
A: Yes! Complete audit trail in Configuration Audit Trail.

**Q: Can I revert changes?**
A: Not automatically. Audit trail shows what changed and when.

**Q: What FPS is best?**
A: 30 is recommended. Higher = more accurate, more CPU. Lower = faster, less accurate.

**Q: Should I use Conservative or Aggressive?**
A: Start with Balanced (default). Use Conservative for high accuracy, Aggressive if system slow.

**Q: What if I accidentally change something wrong?**
A: Check audit trail to see what changed, then manually revert the setting.

**Q: How do I know system is working?**
A: Go to Dashboard. Should see active students, current alerts, and real-time video.

---

## Quick Reference

### Most Common Tasks

**Change FPS Target:**
1. Admin → System Configuration
2. Change "Target FPS"
3. Save

**Reduce CPU Usage:**
1. Admin → Optimization Configuration
2. Click "Aggressive" preset
3. Save

**Increase Drowsiness Detection:**
1. Admin → Detector Configuration
2. Decrease "Eye Aspect Ratio Threshold"
3. Save

**View Configuration Changes:**
1. Admin → Configuration Audit Trail
2. Browse list
3. See who changed what and when

**Acknowledge Alert:**
1. Admin → Alerts
2. Click alert
3. Click "Acknowledge"
4. Add note if needed

**Generate Report:**
1. Admin → Reports
2. Select report type
3. Set date range
4. Click "Generate"
5. Download format

---

**Administrator Guide Complete** ✅

For questions or updates, contact your system administrator.

