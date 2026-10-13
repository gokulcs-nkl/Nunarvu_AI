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
| 4 | Behaviour observations | Not started |
| 5+ | Analytics, PDF export, deployment | Not started |

Recognition accuracy has not been evaluated yet; the match thresholds are
starting values. Inference currently runs on CPU. The earlier prototype lives
in `backend/app1`, `backend/behaviour` and `legacy_frontend` until it is replaced.

## Layout

```
backend/
  Project101/        Django settings and root URLs
  apps/              New system
    accounts/        Roles, session login, audit log
    academics/       Students, classes, subjects, rooms, periods, timetable, sessions
    attendance/      Face enrolment, session attendance rules, review, report
    monitoring/      Cameras, the camera worker, live updates
  vision/            Camera capture with reconnect; face detection, embedding, tracking, matching
  app1/, behaviour/  Earlier prototype (being replaced)
frontend/            React + TypeScript web app (Vite, Tailwind)
legacy_frontend/     Django templates used by the earlier prototype
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

```bash
python manage.py generate_sessions            # create today's sessions from the timetable
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

## API and tests

- API reference: http://127.0.0.1:8000/api/docs/ (new endpoints are under `/api/v1/`)
- Tests: `python manage.py test apps`

## Privacy

This system is intended to process student faces. Before any use with real
students, obtain institutional approval and informed consent, and check the
data-protection law that applies to you. The system stores no video and no
photos. Face enrolment is only permitted for students with recorded consent,
and withdrawing consent deletes the student's face data.
