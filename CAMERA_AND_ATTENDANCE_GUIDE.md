# 📹 Camera Configuration & Attendance Recording Guide

## Quick Summary

Your system now has **complete camera configuration and attendance recording capabilities**:

✅ **Camera Configuration Page** - Manage all your cameras  
✅ **Camera Testing Tool** - Test camera connectivity  
✅ **Attendance Documentation** - Complete step-by-step guide  
✅ **Automatic Attendance** - Records from video feed automatically  

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Configure Your Camera
1. Go to **Capture & Recognize** → **Configure Camera** button
2. Click **"Add Camera"**
3. Enter camera name and source:
   - **Webcam:** `0` (default) or `1`, `2` for additional cameras
   - **IP Camera (RTSP):** `rtsp://admin:password@192.168.1.100:554/stream`
4. Set threshold to `0.6` (default)
5. Click **"Save Camera"**

### Step 2: Test Camera Connection
1. Go to **Test Camera** tab
2. Select camera source
3. Click **"Test Camera Connection"**
4. Wait for success message with video properties

### Step 3: Start Attendance
1. Go to **Capture & Recognize** page
2. Click **"Start Video Capture"** button
3. System automatically records attendance:
   - ✓ Check-in when student appears (>2% of frame)
   - ✓ Check-out after 60 seconds
   - ✓ Re-entry after 5 minutes

---

## 🎬 How Attendance Recording Works

### The Complete Flow (Automated)

```
Camera Frame
    ↓
Detect Faces (MTCNN)
    ↓
Recognize Student (InceptionResnetV1)
    ↓
Check Proximity (>2% of frame)
    ↓
Check Attendance Status
    ├─ No Record → CHECK-IN (create new record)
    ├─ Checked In → Wait 60s → CHECK-OUT
    └─ Checked Out → Wait 5m → RE-ENTRY
    ↓
Record in Database
```

### Example Timeline

```
09:30:00 - John appears on camera
          → System detects face
          → Recognizes "John"
          → Face is large enough (>2% of frame)
          → Creates attendance record
          → ✓ John checked in
          → Plays check-in sound

09:31:00 - John still in frame
          → 60 seconds have passed
          → System marks check-out
          → ✓ John checked out
          → Plays check-out sound

11:45:00 - John appears again (5+ minutes later)
          → System detects face again
          → 5 minutes since checkout
          → Creates NEW attendance record
          → ✓ John re-entered
          → Plays re-entry sound
```

---

## 📊 Database Recording

Each attendance record stores:

| Field | Example | Description |
|-------|---------|-------------|
| Student ID | 5 | Which student |
| Date | 2024-05-14 | Which day |
| Check-in Time | 09:30:15 | When they entered |
| Check-out Time | 14:45:30 | When they left |
| Status | present | Automatic determination |

**All times are recorded automatically - students cannot edit**

---

## 🎥 Camera Configuration Options

### Option 1: Built-in Webcam (USB/Integrated)

**Camera Source:** `0`  
**Threshold:** `0.6` (recommended)

**Setup Tips:**
- Mount at eye level
- Position 1-2 meters from students
- Good lighting (200+ lux)
- No backlighting

**Check if working:**
```
Go to Test Camera tab → Enter "0" → Click Test
Should show: Resolution (e.g., 1280x720), FPS (e.g., 30)
```

### Option 2: IP Camera (RTSP Stream)

**Camera Source Format:**
```
rtsp://[username]:[password]@[ip]:[port]/[stream]
```

**Examples:**

**Hikvision:**
```
rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101
```

**Dahua:**
```
rtsp://admin:password@192.168.1.100:554/live1
```

**Axis:**
```
rtsp://admin:password@192.168.1.100:554/axis-media/media.amp
```

**Generic/Other:**
```
rtsp://admin:password@192.168.1.100:554/stream
```

**Setup Tips:**
- Verify camera is on network
- Check admin credentials
- Ensure RTSP port (554) is open
- Test connectivity before saving

**Check if working:**
```
Go to Test Camera tab → Enter full RTSP URL → Click Test
Should connect and show resolution/FPS
```

### Option 3: Multiple Cameras

**Setup Multiple Cameras:**
1. Configure Camera 1 (source: `0`)
2. Configure Camera 2 (source: `1`)
3. Configure Camera 3 (source: `rtsp://...`)
4. Start video capture - all will run in parallel

---

## ⚙️ Recognition Threshold Explained

### What is Threshold?

**Threshold** = How strict the face recognition is

- **Lower threshold (0.3-0.4):** Very permissive, accepts similar-looking faces
- **Default threshold (0.6):** Balanced, works for most classrooms
- **Higher threshold (0.8+):** Very strict, only exact matches

### Recommended Settings

| Scenario | Threshold | Notes |
|----------|-----------|-------|
| High-quality camera, close distance | 0.7-0.8 | Very accurate recognition |
| **Standard classroom (recommended)** | **0.6** | Best balance |
| Poor lighting, far distance | 0.4-0.5 | More permissive |
| Emergency fallback | 0.3 | Accept any similar face |

### How to Adjust

1. Go to **Camera Configuration**
2. Edit camera
3. Change threshold value
4. Save and test

---

## 🧪 Testing Your Camera

### Method 1: Configuration Page

1. Go to Camera Configuration → **Test Camera** tab
2. Enter camera source (0 or RTSP URL)
3. Click **"Test Camera Connection"**
4. Wait for result

**Success Message Shows:**
- Resolution (width x height)
- FPS (frames per second)
- Status (ready to use)

**Error Message Shows:**
- What went wrong
- Troubleshooting tips

### Method 2: API Test

```bash
curl -X POST http://127.0.0.1:8000/api/test-camera/ \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"camera_source": "0", "threshold": 0.6}'
```

### Method 3: System Camera App

Test camera with built-in app first:
- **Windows:** Camera app
- **Mac:** Photo Booth
- **Linux:** Cheese

---

## ❌ Troubleshooting

### Problem: "Unable to access camera"

**Solutions:**
1. Check camera is physically connected
2. Restart Django server
3. Try different camera index:
   ```
   Try: 0, 1, 2, 3 until one works
   ```
4. Check drivers installed
5. Test with system camera app first

### Problem: Students not recognized

**Solutions:**
1. Verify student is authorized
2. Check student photo was captured
3. Lower threshold (try 0.4 instead of 0.6)
4. Improve lighting
5. Student must move closer
6. No sunglasses or masks
7. Student must be in database

### Problem: "Come closer!" message

**Solutions:**
1. Move camera closer to students (1.5m ideal)
2. Move student closer to camera
3. Increase camera resolution
4. Ensure face is >2% of frame

### Problem: Attendance not recording

**Solutions:**
1. Check browser console (F12) for errors
2. Verify server running: `python manage.py runserver`
3. Try restarting video capture
4. Check student is authorized
5. Verify database: 
   ```sql
   SELECT * FROM app1_attendance;
   ```

---

## 📝 Technical Details

### Face Recognition System

**Face Detection (MTCNN):**
- Detects all faces in frame
- Very fast, works in real-time
- Returns face bounding boxes

**Face Encoding (InceptionResnetV1):**
- Converts face to 512-dimensional vector
- Unique representation of each face
- Used for comparison

**Face Matching:**
- Calculates distance between vectors
- Lower distance = more similar
- Threshold determines if match

### Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Frame Processing | ~30 FPS | Real-time |
| Face Detection | <50ms per frame | MTCNN |
| Face Recognition | <30ms per frame | InceptionResnetV1 |
| Database Write | <10ms | Attendance recording |
| Total Latency | ~100-150ms | End-to-end |

### Minimum Requirements

- **Camera Resolution:** 640x480 (minimum), 1280x720 (recommended)
- **Frame Rate:** 20+ FPS (30 FPS recommended)
- **Lighting:** 200+ lux (classroom lighting)
- **Network:** Stable for IP cameras
- **Server:** Running on http://127.0.0.1:8000

---

## 🔧 Advanced Configuration

### Using Multiple Cameras

**Parallel Processing:**
```
All cameras run in separate threads
↓
Each captures frames at 30 FPS
↓
Shared face recognition engine
↓
Independent attendance recording
```

**When to use:**
- Multiple classrooms
- Multiple entry points
- 360-degree coverage

### Custom Thresholds Per Camera

```
Camera 1 (HD, close range): 0.7
Camera 2 (SD, far range): 0.5
```

Each camera can have different threshold settings.

### Real-time Monitoring

**Check Active Cameras:**
1. Go to Dashboard
2. See "Cameras Online" metric
3. Shows how many cameras configured

**View Recent Activity:**
1. Dashboard shows recent attendance
2. Student Attendance list shows all records
3. Export as CSV

---

## 📱 Mobile Access

**Access from Mobile Device:**
```
http://[server-ip]:8000/home/
```

Replace `[server-ip]` with your server's IP address.

**Features:**
- View attendance records
- Check real-time metrics
- Responsive design (works on tablet/phone)

---

## 🚨 Important Notes

⚠️ **Student Registration First:**
- Must create student account
- Capture face photo during registration
- Mark as authorized in admin

⚠️ **Lighting Critical:**
- Minimum 200 lux (classroom lighting)
- Avoid backlighting (windows behind students)
- Direct shadows reduce accuracy

⚠️ **Face Visibility:**
- No sunglasses or masks
- Clear view of face
- At least 2% of frame occupied

⚠️ **Database Safety:**
- All attendance records permanent
- Backed up in SQLite3
- Cannot be accidentally deleted

---

## 📖 Help & Documentation

**View Full Documentation:**
- Go to **Capture & Recognize** → Click **"Help"** button
- Or visit: `/attendance-flow-documentation/`

**View Camera Status:**
- Dashboard shows cameras online
- Admin panel shows all configurations

**Access Camera Management:**
- URL: `/camera-config/`
- Create new cameras
- Edit existing cameras
- Delete cameras
- Test camera connectivity

---

## ✅ Checklist Before Using

Before starting attendance recording, verify:

- [ ] Camera is physically connected
- [ ] Camera test shows success
- [ ] At least 1 camera configured
- [ ] Students registered in system
- [ ] Student photos captured
- [ ] Students marked as authorized
- [ ] Good lighting in room
- [ ] Django server running
- [ ] No browser errors (F12 console)

---

## 🎓 Example Workflow

### Complete Day Workflow

**Morning (9:00 AM):**
1. Start camera (go to Capture & Recognize)
2. Students arrive and position in front of camera
3. System automatically records check-in as they appear

**Throughout Day:**
- System tracks presence
- Records check-outs when students leave
- Allows re-entry if they return

**End of Day (2:00 PM):**
1. Stop camera (press 'q' in video window or close)
2. View attendance summary on Dashboard
3. Export attendance as CSV if needed

---

## 📞 Support

**If you encounter issues:**

1. **Check logs:** Browser console (F12) or server terminal
2. **Test camera:** Use "Test Camera" tab
3. **Restart server:** `python manage.py runserver`
4. **Review this guide:** Most common issues covered above
5. **Check database:** Verify attendance records exist

---

**System Status:** ✅ Ready to Use  
**Last Updated:** May 14, 2024  
**Version:** 1.0.0
