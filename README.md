<p><img src="frontend/public/logo.svg" width="72" alt="Nunarvu AI logo"></p>

# Nunarvu AI: Classroom Monitoring System (RCMS)

A classroom monitoring system for automated, period-based attendance and
teacher-reviewed classroom observations, built with Django and React.

**Status:** under redesign.

| Phase | Scope | State |
|---|---|---|
| 1 | Roles, academic data, period timings, sessions, web app shell | Done |
| 2 | Consent-based face enrolment, attendance from the camera, teacher review, attendance report | Done |
| 3 | Background camera worker, IP cameras, live view over WebSocket, camera management | Done |
| 4 | Classroom observations (hand raise, head-down posture, phone-like object, unusual activity) with teacher review | Done, not yet evaluated |
| 5 | Analytics: attendance by date, class, subject and student; observation counts; PDF and CSV export | Done |
| 6 | Timetable screen with automatic session start and end, user management, system health and in-app alerts | Done |
| 7 | Evaluation, benchmark and backup tools; PostgreSQL compose file; demonstration and evaluation guides | Tools done; measurements not yet run; PostgreSQL untested |
| + | Dark interface with depth; GPU support for the face models; email alerts for camera problems | Done |

Recognition accuracy has not been evaluated yet; the match thresholds are
starting values. See `docs/EVALUATION.md` for how to measure it and
`docs/DEMO.md` for a demonstration walkthrough. The earlier prototype lives
in `backend/app1`, `backend/behaviour` and `legacy_frontend` until it is replaced.

## Layout

```
backend/
  Project101/        Django settings and root URLs
  apps/              New system
    accounts/        Roles, session login, audit log
    academics/       Students, classes, subjects, rooms, periods, timetable, sessions
    attendance/      Face enrolment, session attendance rules, review, report
    monitoring/      Cameras, the camera worker, live updates, classroom observations
  vision/            Camera capture with reconnect; face detection, embedding, tracking, matching;
                     body-pose rules and event timing
  app1/, behaviour/  Earlier prototype (being replaced)
frontend/            React + TypeScript web app (Vite, Tailwind)
legacy_frontend/     Django templates used by the earlier prototype
docs/                Demonstration and evaluation guides; archive/ holds the prototype's old notes
```

## Run it

Requirements: Python 3.10+, Node.js 20+.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows; use `source venv/bin/activate` elsewhere
pip install -r requirements.txt
cp ../.env.example .env          # then set SECRET_KEY as described in the file
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The server refuses to start without `SECRET_KEY`. SQLite is used unless the
`DB_*` variables in `.env` point at PostgreSQL.

### Face models

```bash
python manage.py download_face_models                    # buffalo_l, about 280 MB
python manage.py download_face_models --pack buffalo_sc  # about 15 MB, for CPU-only machines
```

Set `FACE_EMBEDDING_KEY` in `.env` (see `.env.example`) before enrolling anyone.
The InsightFace pretrained models are licensed for non-commercial research use.

### Camera worker

Set `WORKER_TOKEN` in `.env` (see `.env.example`), then, with the backend running:

```bash
python manage.py run_camera_worker            # every enabled camera
python manage.py run_camera_worker --camera 1 # one camera
```

The worker reads each camera, recognises faces for the active session in that
camera's room, records attendance and feeds the live view. A camera with no
room serves sessions with no room. If a camera drops, the worker retries with a
growing delay and the camera shows as "Camera error" until it returns. While the
worker holds a webcam, enrol faces from the worker's camera on the Students page.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 for the landing page, then sign in. The dev server forwards `/api` to the
backend at http://127.0.0.1:8000.

## Roles

| Role | Can do |
|---|---|
| Administrator | Everything, including users, students, cameras and period timings |
| Teacher | See own classes and students; start and close own sessions; mark and correct attendance |
| Viewer | Read classes, timetable, sessions and attendance; no student personal data |

Superusers are administrators. Other users get a role through the
`/api/v1/users/` endpoint.

## Period timings

Timings are optional. An administrator can set a default schedule, override it
for any weekday, and override it again for one calendar date. The most specific
match applies. With no timings, teachers start and close sessions manually.

Put subjects into periods on the Timetable page. While the camera worker is
running it creates each day's sessions, starts each one when its period begins
and ends it when the period is over, marking unseen students absent. Sessions
started by hand are never ended automatically.

```bash
python manage.py generate_sessions            # create today's sessions without the worker
python manage.py generate_sessions --date 2026-10-19
```

## Attendance from the camera

1. Record a student's consent on the Students page, then enrol their face with
   about five captures. Photos are discarded; only an encrypted embedding is stored.
2. Start a session. If the camera worker is running, the session page shows
   its live view automatically; otherwise the page can use the browser's webcam.
3. A student is marked present (or late) after two confident sightings. An
   uncertain match becomes "pending review" and never marks anyone present. An
   unrecognised face is never given a name.
4. Ending the session marks unseen students absent. A teacher can correct any
   record; corrections are audited and are not overwritten by the camera.

## Classroom observations

While a session is active the worker can also report four things it sees:

| Observation | What is measured | Default delay |
|---|---|---|
| Hand raised | A wrist above its shoulder | 1 s |
| Head-down posture | Nose at or below the shoulder line | 60 s |
| Phone-like object | An object detected as a phone inside a person's outline | 5 s |
| Unusual activity | Two or more fast-moving people close together | 3 s |

Each is stored as an event with its measurements and thresholds, shown to the
teacher as "not reviewed", and confirmed or dismissed by them. The wording
describes what was visible; nothing is presented as a conclusion about a
student. An administrator can switch each observation off or change its delay
on the Observations page. Run the worker with `--no-observations` to record
attendance only.

These rules use pretrained models (YOLO11n-pose and YOLO11n) and fixed
thresholds. Their precision and recall have not been measured yet, and the
phone and unusual-activity observations in particular should be expected to
miss cases and raise false alarms.

## Tools

```bash
python manage.py evaluate_faces <folder> --csv out.csv   # recognition error rates on your own labelled photos
python manage.py benchmark_models --image photo.jpg      # time per frame for each model on this computer
python manage.py backup_data --out backups               # compressed backup; restore with loaddata
```

`start_nunarvu.bat` starts the backend, the camera worker and the web app in
three windows. To use a particular Python (for example a virtual environment
with GPU packages), put its full path in a file named `python_path.txt` next to
the script.

## Graphics card

With an NVIDIA card, install the GPU packages into the Python environment that runs the app:

```bash
pip install torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cu121
pip uninstall -y onnxruntime
pip install "onnxruntime-gpu[cuda,cudnn]==1.23.2"
```

The app loads the CUDA libraries at start-up. `python manage.py benchmark_models` shows
whether each model is on the graphics card. Each program that uses the card reserves several
GB of system memory; set `BEHAVIOR_DEVICE=cpu` in `backend/.env` to keep the pose and object
models on the processor if memory is short.

## Email alerts

When a camera stops working, and when it recovers, administrators and teachers who have an
email address are told, unless they switch it off on the System health page. By default the
message is printed in the camera worker window; set the `EMAIL_*` values in `backend/.env`
to send real email.

## PostgreSQL

SQLite is the default and needs no setup. To use PostgreSQL, set the `DB_*` values in
`backend/.env` (see `.env.example`), create the tables, and copy any existing SQLite data:

```bash
cd backend
python manage.py migrate
python manage.py copy_from_sqlite db.sqlite3   # reads SQLite, checks every table's row count
```

PostgreSQL can run in Docker (`docker compose --env-file backend/.env up -d`, using the same
`DB_*` values) or as a local install. Only one of them can use port 5432 at a time.

`start_nunarvu.bat` runs `local_start.bat` first if it exists (it is not committed), which is the
place to start a local PostgreSQL.

## API and tests

- API reference: http://127.0.0.1:8000/api/docs/ (new endpoints are under `/api/v1/`)
- Tests: `python manage.py test apps`

## Privacy

This system is intended to process student faces. Before any use with real
students, obtain institutional approval and informed consent, and check the
data-protection law that applies to you. The system stores no video and no
photos. Face enrolment is only permitted for students with recorded consent,
and withdrawing consent deletes the student's face data.
