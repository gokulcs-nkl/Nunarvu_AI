# Measuring the system

Nothing in this project should be reported with an accuracy figure that was not
measured on your own data. This page describes how to produce those figures.

## Consent comes first

Every photo or recording used here must be of a person who agreed to it, for
this purpose. Keep the files off the repository (the `evaluation/` folder is
ignored by git) and delete them when the project is finished.

## 1. Face recognition

**Collect.** For each volunteer, take at least five photos that were not used
for enrolment: different days if possible, with and without glasses, slightly
different angles, and at the distances you intend to use. Put them in one
folder per person:

```
evaluation/faces/
  person_01/  a.jpg  b.jpg  c.jpg ...
  person_02/  ...
```

**Run.**

```bash
cd backend
python manage.py evaluate_faces ../evaluation/faces --csv ../evaluation/faces.csv
```

**Read the output.**

- *Misses* is the share of same-person pairs scored below the threshold (the
  false non-match rate). In use, a miss means a student is not marked
  automatically.
- *False matches* is the share of different-person pairs scored at or above the
  threshold (the false match rate). In use, a false match would mark the wrong
  student, which is the more serious error.
- The last lines show both rates at the thresholds currently configured
  (`FACE_MATCH_CONFIRM` and `FACE_MATCH_REVIEW`).

**Choose thresholds.** Set `FACE_MATCH_CONFIRM` to the lowest value with no
false matches on your data, plus a margin of about 0.05. Set
`FACE_MATCH_REVIEW` roughly 0.15 below it. Put both in `backend/.env`.

**Report honestly.** State the number of people, photos and pairs. With ten
people there are only a few hundred different-person pairs, so "0 false
matches" means "none observed in N pairs", not a rate of zero. Repeat the
measurement separately for poor lighting or long distance, and say how the
figures change.

## 2. Attendance per session

Recognition scores do not tell you whether attendance was right. For two or
three real sessions, write down who was actually present, late and absent, then
compare with the session page before any correction:

| Measure | How to count |
|---|---|
| Correct without help | Students whose automatic status matched the truth |
| Sent to review | Students left as "Pending review" |
| Wrong | Students given a status that did not match the truth |
| Missed | Students present but "Absent" or "Not yet seen" at the end |

Report these as counts out of the class size for each session.

## 3. Classroom observations

For each observation type, record a short session in which volunteers perform
the action a known number of times (for example ten hand raises) and also sit
normally for a few minutes. Then count on the Observations page:

- **Recall** = actions that produced an observation / actions performed.
- **Precision** = observations that correspond to a real action / all
  observations of that type.
- **False alarms per hour** during the period of normal sitting.

The phone and unusual-activity observations are expected to score lowest. If a
type is too unreliable to be useful, switch it off on the Observations page and
say so in the report.

## 4. Speed

```bash
python manage.py benchmark_models --image ../evaluation/faces/person_01/a.jpg
```

This prints the time per frame for each model on your computer and whether each
runs on the graphics card. The **System health** page shows the live figure
(frames per second and milliseconds per frame) while the worker is running.
For end-to-end delay, time how long a seated volunteer takes to change from
"Not yet seen" to "Present" over several trials.

## 5. Recovery

- Unplug or cover the camera during a session: the Cameras page should show
  "Camera error" within about twenty seconds, and return to "Online" by itself
  when the camera is back.
- Stop the camera worker: the session page should say that no worker is
  running, and attendance can still be marked by hand.

Record what happened in each case, including anything that did not recover.
