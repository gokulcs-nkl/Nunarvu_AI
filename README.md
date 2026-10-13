# Nunarvu AI: Classroom Monitoring System (RCMS)

A classroom monitoring system for automated, period-based attendance and
teacher-reviewed classroom observations, built with Django and React.

**Status:** under redesign. Phase 1 (foundation) is in place: roles, academic
data, period timings, sessions, manual attendance and the web app shell.
Camera-based attendance, live monitoring and behaviour observations are not
part of the new system yet; the earlier prototype of those lives in
`backend/app1`, `backend/behaviour` and `legacy_frontend` until it is replaced.

## Layout

```
backend/
  Project101/        Django settings and root URLs
  apps/              New system
    accounts/        Roles, session login, audit log
    academics/       Students, classes, subjects, rooms, periods, timetable, sessions
    attendance/      One attendance record per student per session
    monitoring/      Camera devices
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

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in. The dev server forwards `/api` to the
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

## API and tests

- API reference: http://127.0.0.1:8000/api/docs/ (new endpoints are under `/api/v1/`)
- Tests: `python manage.py test apps`

## Privacy

This system is intended to process student faces. Before any use with real
students, obtain institutional approval and informed consent, and check the
data-protection law that applies to you. The system stores no video; face
enrolment is only permitted for students with recorded consent.
