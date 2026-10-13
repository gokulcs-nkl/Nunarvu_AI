# Behavior Analysis Dashboard - Features & Usage Guide

## Overview

The Behavior Analysis Dashboard is a comprehensive real-time monitoring system for classroom behavior analysis. It provides three main interfaces for different use cases:

1. **Real-Time Dashboard** - Live monitoring with video overlays
2. **Student Attention List** - Sorted priority list of students by attention level
3. **Analytics & Reports** - Detailed analytics, charts, and data export

---

## 1. Real-Time Dashboard

### URL
```
http://localhost:8000/behavior-dashboard/
```

### Features

#### Live Video Stream
- **Real-time video capture** with MediaPipe overlays
- **Student identification** with face bounding boxes
- **Attention score display** color-coded by level
- **Active alert indicators** showing critical behaviors
- **FPS counter** and processing metrics

#### Quick Stats Panel
- **Total Students** - Number of students being tracked
- **Active Students** - Students currently visible in frame
- **Active Alerts** - Count of critical alerts
- **Average Attention** - Classroom-wide attention score

#### Critical Alerts Section
- **Real-time alert feed** sorted by severity
- **Color-coded by severity** (High/Medium/Low)
- **Student name and duration** for each alert
- **Auto-scroll** to latest alerts
- **Clear alerts button** to reset list

#### System Performance Metrics
- **Processing Time** - Time to analyze each frame (target: <30ms)
- **CPU Usage** - Real-time CPU utilization (target: <70%)
- **Memory Usage** - Current memory consumption (target: <500MB)
- **Queue Size** - Frame queue utilization (0-30)
- **Thread Health** - Status of behavior analysis thread

#### Controls
- **Classroom Filter** - Select specific classroom to monitor
- **Record Button** - Start/stop recording of session
- **Screenshot Button** - Capture current frame
- **Connection Status** - Real-time API connection indicator
- **Dark Mode Toggle** - Switch between dark and light themes

#### Keyboard Shortcuts
- `Space` - Pause/Resume updates
- `S` - Capture screenshot
- `R` - Toggle recording
- `?` - Show help modal

---

## 2. Student Attention List

### URL
```
http://localhost:8000/student-attention/
```

### Features

#### Real-Time Table
- **Student Names** - Full student names with seat assignments
- **Attention Score** - Large color-coded score display (0-100)
- **Status Badge** - Attention level (Excellent/Good/Fair/Poor/Critical)
- **Component Scores** - Individual bars for:
  - Drowsiness Score
  - Head Pose Score  
  - Phone Usage Score
  - Posture Score
- **Alert Count** - Number of alerts for this student
- **Action Button** - View detailed student analysis

#### Sorting Options
- **Lowest Attention First** - Prioritize students at risk (default)
- **Highest Attention First** - Show best-performing students
- **Most Alerts First** - Sort by alert frequency
- **Name (A-Z)** - Alphabetical order

#### Filtering Options
- **Classroom Filter** - Select specific classroom
- **Alert Type Filter** - Filter by alert type (Drowsiness/Phone/Posture/etc)
- **Time Range Filter** - 1h/4h/24h/7d lookback
- **Status Filter** - Show only certain attention levels
- **Search Box** - Search by student name

#### Statistics
- **Total Students** - Students in current view
- **Critical Count** - Students in critical state
- **Total Alerts** - Cumulative alerts shown
- **Average Attention** - Mean attention score

#### Export
- **CSV Export** - Download as comma-separated values
- **Pagination** - View 10 students per page
- **Last Updated** - Timestamp of last refresh

#### Student Detail Modal
Click any row or "View" button to open:
- **Radar Chart** - Visual 5-component score comparison
- **Alert History** - Recent alerts for this student
- **Recent Events** - Raw behavior detection events

---

## 3. Analytics & Reports

### URL
```
http://localhost:8000/behavior-analytics/
```

### Features

#### Date & Classroom Filters
- **Start Date** - Analysis start date
- **End Date** - Analysis end date
- **Classroom Filter** - Select classroom(s)
- **Student Filter** - Individual student analysis
- **Behavior Type Filter** - Filter by behavior category

#### Key Metrics
- **Average Attention** - Mean attention score over period
- **Total Alerts** - Count of all alerts
- **Drowsiness Rate** - % of observations with drowsiness
- **Phone Usage Rate** - % of observations with phone usage

#### Charts & Visualizations

1. **Attention Score Trend Line Chart**
   - X-axis: Timeline
   - Y-axis: Average attention score (0-100)
   - Shows attention trends over selected period
   - Identifies patterns and peak hours

2. **Alert Distribution Doughnut Chart**
   - Breakdown of alerts by type
   - 5 categories: Drowsiness, Phone, Posture, Distraction, Absence
   - Helps identify most common behavior issues

3. **Behavior Component Scores Radar Chart**
   - 5-axis radar showing component averages
   - Easy visual comparison of all factors
   - Identifies which behaviors need most attention

4. **Hourly Activity Heatmap**
   - Color-coded intensity by time of day
   - Identifies peak behavior issues hours
   - Useful for scheduling interventions

5. **Top Issues by Student**
   - Table of students with most issues
   - Sorted by frequency
   - Includes severity levels

6. **Alert Timeline**
   - Historical view of all alerts
   - Sorted chronologically
   - Shows duration of each incident

#### Detailed Event Log
- **Full-text table** of all behavior events
- **Timestamp** - When event occurred
- **Student** - Which student
- **Event Type** - What behavior detected
- **Confidence** - Detection confidence (0-100%)
- **Duration** - How long behavior lasted
- **Filterable** by event type

#### Export Options
- **CSV Export** - All metrics as spreadsheet
- **JSON Export** - Raw data in JSON format
- **PDF Export** - Professional report document
- **Share Report** - Generate shareable link

#### Print
- **Print Button** - Format for printing
- **Optimized layout** - Hides controls
- **All charts** included in printout

---

## Color Coding System

### Attention Score Levels
```
Excellent    85-100  🟢 Green    - No action needed
Good         70-84   🔵 Blue     - Monitor
Fair         55-69   🟡 Yellow   - Intervention advised
Poor         40-54   🔴 Red      - Active monitoring
Critical     0-39    🔴 Dark Red - Immediate action needed
```

### Component Score Colors
```
High (70+)   🟢 Green   - No issues
Medium (55-69) 🟡 Yellow - Minor attention
Low (0-54)   🔴 Red     - Major concern
```

### Alert Severity
```
High     🔴 Red     - Immediate attention needed
Medium   🟡 Yellow  - Should be addressed
Low      🔵 Blue    - Informational
```

---

## Real-Time Features

### WebSocket/Polling Updates
- **3-second refresh interval** - Latest data every 3 seconds
- **Non-blocking** - UI stays responsive
- **Auto-pause** - Can pause updates with Space key
- **Connection indicator** - Shows API connection status

### Notifications
- **Toast notifications** - Top-right corner
- **Auto-dismiss** - Disappear after 5 seconds
- **Color-coded** - By message type (success/info/warning/danger)
- **Manual close** - Click X to dismiss

### Performance Monitoring
- **Frame counter** - Total frames processed
- **FPS display** - Real-time frames per second
- **Queue monitor** - Frame buffer utilization
- **Thread health** - Behavior analysis thread status

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Pause/Resume live updates |
| `S` | Capture screenshot of video |
| `R` | Toggle recording on/off |
| `?` | Show keyboard shortcuts help |
| `D` | Toggle dark mode |
| `Ctrl+P` | Print current page |
| `Ctrl+S` | Save page |

---

## Dark Mode

- **Toggle button** - Moon icon in top-right corner
- **Persistent** - Preference saved to localStorage
- **All pages** - Works across all dashboard views
- **Print-friendly** - Optimized for both light and dark

---

## Data Export Formats

### CSV Export
```
Student Name, Average Attention, Min Score, Max Score, Alert Count
John Doe, 85, 75, 95, 2
Jane Smith, 65, 55, 78, 5
```

### JSON Export
```json
[
  {
    "student_id": 1,
    "student_name": "John Doe",
    "avg_attention_score": 85,
    "alert_count": 2
  },
  {
    "student_id": 2,
    "student_name": "Jane Smith",
    "avg_attention_score": 65,
    "alert_count": 5
  }
]
```

### PDF Report
- Professional formatting
- All charts and tables
- Header with date/classroom
- Footer with page numbers

---

## API Integration

### REST Endpoints Used

```
GET  /api/behavior-stats/classroom/     - Classroom overview stats
GET  /api/behavior-stats/student/       - Per-student statistics
GET  /api/behavior-stats/daily/         - Daily trends
GET  /api/attention-scores/latest_scores/ - Current student scores
GET  /api/attention-scores/by_student/  - Student score history
GET  /api/behaviour-alerts/             - All alerts
GET  /api/behaviour-alerts/unacknowledged/ - Only critical alerts
GET  /api/behaviour-alerts/statistics/  - Alert aggregates
GET  /api/behaviour-events/             - Raw behavior events
GET  /api/student-seats/                - Seat assignments
```

---

## Browser Compatibility

- **Chrome/Edge** - Full support
- **Firefox** - Full support
- **Safari** - Full support
- **Mobile** - Responsive layout

---

## Performance Tips

1. **Frame Skipping** - Reduces CPU load by skipping frames
2. **Resolution Reduction** - 480p analysis is faster than 720p
3. **Polling Interval** - Increase if network is slow
4. **Dark Mode** - Slightly better performance on OLED screens
5. **Chart Limits** - Show only last 100 events to avoid lag

---

## Troubleshooting

### Dashboard Not Loading
- Check API server is running
- Verify Django server is accessible
- Check browser console for errors (F12)

### No Data Showing
- Verify camera/students are initialized
- Check behavior thread is running
- Ensure database has records

### Alerts Not Updating
- Refresh page (F5)
- Check WebSocket connection in DevTools
- Verify thresholds in config

### Charts Not Rendering
- Ensure Chart.js library loaded (check DevTools Network)
- Try different date range
- Clear browser cache

### Recording Not Working
- Check browser permissions
- Ensure MediaRecorder API supported
- Try different browser

---

## Advanced Usage

### Custom Thresholds
Edit `/backend/behaviour/config.py` to adjust:
- Drowsiness threshold (EAR value)
- Head pose angles (yaw/pitch)
- Phone detection confidence
- Posture angles
- Alert duration thresholds

### Real-Time Monitoring
Use browser DevTools (F12) to:
- Monitor API response times
- Watch WebSocket messages
- Debug chart data
- Profile performance

### Data Analysis
Export JSON data to external tools:
- Excel/Google Sheets
- Python pandas
- R statistical analysis
- Tableau/Power BI

---

## Security Notes

- **Authentication Required** - All pages require login
- **HTTPS Recommended** - Use SSL in production
- **CORS Configured** - API calls within same origin
- **Rate Limiting** - Implement if needed for large deployments

---

## Support & Documentation

For more information:
- See `BEHAVIOR_ANALYSIS_README.md` for architecture
- Check API documentation at `/api/docs/`
- Review Django admin for data inspection
- Run tests with `python manage.py test`

---

## Version History

### v1.0 (Current)
- Real-time dashboard with video overlays
- Student attention list with sorting/filtering
- Analytics with time-series charts
- CSV/JSON export
- Dark mode support
- Keyboard shortcuts
- Mobile responsive

---

## Contact & Feedback

For issues or feature requests, contact the development team or submit through your organization's issue tracker.

---

**Last Updated:** May 2026  
**Maintained By:** Development Team  
**License:** Internal Use Only
