# Demonstration walkthrough

A fifteen-minute demonstration of Nunarvu AI on one laptop with its webcam. It
shows period-based attendance, teacher review, a classroom observation and the
reports.

## Before the audience arrives

1. Start everything by double-clicking `start_nunarvu.bat`. Three windows open:
   the backend, the camera worker and the web app.
2. Open http://localhost:5173 and sign in as an administrator.
3. On **Classes and rooms**, check there is one class and one subject.
4. On **Students**, check that each volunteer has consent recorded and five face
   captures. Enrol anyone who is missing.
5. On **Period timings**, add two short periods a few minutes from now, for
   example five minutes each with a one-minute gap. Use the **One date** picker
   so they apply to today only.
6. On **Timetable**, put the subject in both periods for today's weekday.
7. On **Cameras**, check that the laptop webcam shows **Online**.

Only people who have agreed to take part should be in view of the camera.

## The demonstration

| Step | What to do | What the audience sees |
|---|---|---|
| 1 | Show the landing page (`/about`) | What the system is, and the privacy principles |
| 2 | Open **Overview** | Today's periods and sessions, and anything waiting for review |
| 3 | Wait for period 1 to start, then open its session | The session became active by itself; the live view shows labelled faces |
| 4 | Have an enrolled volunteer sit in view | "Confirmed", then **Present** in the attendance list after a few seconds |
| 5 | Have someone who is not enrolled step in | "Unrecognised": no name, no record |
| 6 | Have the volunteer raise a hand for two seconds | A **Hand raised** observation appears, marked "Not reviewed" |
| 7 | Open "What was measured" on the observation, then **Confirm** it | The measurement and threshold behind it, and the teacher's decision |
| 8 | Change one student's status by hand | A teacher's decision is kept; the camera does not overwrite it |
| 9 | Wait for period 1 to end | The session closes; anyone never seen is marked **Absent** |
| 10 | Let period 2 start | A new session, with attendance starting fresh |
| 11 | Open **Reports** | Attendance by date, class, subject and student; download the PDF |
| 12 | Open **System health** | Camera uptime, speed, and the models in use |

## If something goes wrong

- **The live view says no worker is running.** The camera worker window was
  closed or failed. Start it again from the `backend` folder:
  `python manage.py run_camera_worker`.
- **"Camera error".** Another program is using the webcam. Close it; the worker
  reconnects by itself.
- **A volunteer is not recognised.** Check lighting, and that they were enrolled
  with the face model now in use (System health shows it). Re-enrol if needed.
  Their attendance can always be marked by hand.
- **No hand-raise observation.** Both shoulders and the raised wrist must be in
  the picture, and the hand must stay up for about two seconds.
- **A backup plan for the camera.** Add a camera of type "Recorded video file"
  pointing at a recording made earlier with the volunteers' consent.

## What to say about limits

- Recognition depends on the camera. A laptop webcam covers roughly the first
  two to three metres.
- Accuracy figures come from `python manage.py evaluate_faces` on your own
  consented photos; see `docs/EVALUATION.md`. Do not quote benchmark figures as
  this system's accuracy.
- Observations describe what was visible. They are prompts for the teacher, not
  conclusions about a student.
