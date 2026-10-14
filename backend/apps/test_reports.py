from datetime import timedelta

from django.utils import timezone

from apps.academics.models import ClassSession, Student, Subject
from apps.accounts.models import AuditLog
from apps.attendance.analytics import camera_uptime
from apps.attendance.models import AttendanceRecord
from apps.monitoring.models import Camera, CameraStatusLog, ClassroomEvent
from apps.tests import BaseData


class ReportBase(BaseData):
    def setUp(self):
        self.physics = Subject.objects.create(code='PH101', name='Physics')
        self.second = Student.objects.create(roll_number='A002', full_name='Chitra')
        self.second.class_groups.add(self.group)
        today = timezone.localdate()
        # Two Maths sessions for CSE-A (two days ago and yesterday) and one Physics session for CSE-B today.
        plan = [
            (self.group, self.maths, self.teacher, 2, {self.student: 'present', self.second: 'absent'}),
            (self.group, self.maths, self.teacher, 1, {self.student: 'late', self.second: 'pending'}),
            (self.other_group, self.physics, self.other_teacher, 0, {self.outsider: 'present'}),
        ]
        self.sessions = []
        for group, subject, teacher, days_ago, marks in plan:
            session = ClassSession.objects.create(
                class_group=group, subject=subject, teacher=teacher, date=today - timedelta(days=days_ago),
                starts_at=timezone.now() - timedelta(days=days_ago),
            )
            self.sessions.append(session)
            for student, status in marks.items():
                AttendanceRecord.objects.create(session=session, student=student, status=status)
        self.today = today


class SummaryTests(ReportBase):
    def test_totals_exclude_pending_from_the_percentage(self):
        totals = self.client_for(self.admin).get('/api/v1/reports/summary/').data['totals']
        self.assertEqual((totals['records'], totals['sessions'], totals['students']), (5, 3, 3))
        self.assertEqual((totals['present'], totals['late'], totals['absent'], totals['pending']), (2, 1, 1, 1))
        self.assertEqual(totals['attendance_percent'], 75.0)  # 3 attended of 4 decided

    def test_trend_and_breakdowns(self):
        data = self.client_for(self.admin).get('/api/v1/reports/summary/').data
        self.assertEqual([(row['attended'], row['decided'], row['percent']) for row in data['by_date']], [(1, 2, 50.0), (1, 1, 100.0), (1, 1, 100.0)])
        self.assertEqual([row['date'] for row in data['by_date']], sorted(row['date'] for row in data['by_date']))
        classes = {row['name']: row for row in data['by_class']}
        self.assertEqual((classes['CSE-A (2026-27)']['percent'], classes['CSE-A (2026-27)']['sessions']), (66.7, 2))
        self.assertEqual(classes['CSE-B (2026-27)']['percent'], 100.0)
        self.assertEqual({row['name'] for row in data['by_subject']}, {'MA101', 'PH101'})

    def test_filters_and_validation(self):
        client = self.client_for(self.admin)
        only_b = client.get(f'/api/v1/reports/summary/?class_group={self.other_group.id}').data
        self.assertEqual(only_b['totals']['records'], 1)
        yesterday = (self.today - timedelta(days=1)).isoformat()
        self.assertEqual(client.get(f'/api/v1/reports/summary/?date_from={yesterday}').data['totals']['records'], 3)
        by_teacher = client.get(f'/api/v1/reports/summary/?teacher={self.teacher.id}').data
        self.assertEqual(by_teacher['totals']['sessions'], 2)
        self.assertEqual(client.get('/api/v1/reports/summary/?date_from=13-10-2026').status_code, 400)
        self.assertEqual(client.get('/api/v1/reports/summary/?class_group=abc').status_code, 400)

    def test_teacher_sees_only_own_sessions_and_viewer_is_refused(self):
        mine = self.client_for(self.teacher_user).get('/api/v1/reports/summary/').data
        self.assertEqual((mine['totals']['sessions'], len(mine['by_class'])), (2, 1))
        self.assertEqual(self.client_for(self.viewer).get('/api/v1/reports/summary/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/reports/summary/').status_code, 401)

    def test_empty_result_has_no_percentage(self):
        data = self.client_for(self.admin).get('/api/v1/reports/summary/?date_from=2030-01-01').data
        self.assertEqual((data['totals']['records'], data['totals']['attendance_percent'], data['by_date']), (0, None, []))


class PdfTests(ReportBase):
    def test_pdf_export_is_a_pdf_and_is_audited(self):
        response = self.client_for(self.teacher_user).get(f'/api/v1/reports/attendance/?export=pdf&class_group={self.group.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertGreater(len(response.content), 1500)
        entry = AuditLog.objects.get(action='export_attendance_report')
        self.assertEqual((entry.detail['format'], entry.detail['rows']), ('pdf', 2))

    def test_pdf_with_no_rows_still_builds(self):
        response = self.client_for(self.admin).get('/api/v1/reports/attendance/?export=pdf&date_from=2030-01-01')
        self.assertTrue(response.content.startswith(b'%PDF'))


class ObservationSummaryTests(ReportBase):
    def test_counts_by_kind_and_review_status(self):
        now = timezone.now()
        for index, (kind, status) in enumerate([('hand_raise', 'confirmed'), ('hand_raise', 'unreviewed'), ('phone', 'dismissed')]):
            ClassroomEvent.objects.create(
                session=self.sessions[0], kind=kind, subject=str(index), started_at=now + timedelta(seconds=index),
                confidence=0.8, summary='x', review_status=status,
            )
        rows = {row['kind']: row for row in self.client_for(self.teacher_user).get('/api/v1/reports/observations/').data}
        self.assertEqual((rows['hand_raise']['total'], rows['hand_raise']['confirmed'], rows['hand_raise']['unreviewed']), (2, 1, 1))
        self.assertEqual((rows['phone']['dismissed'], rows['head_down']['total']), (1, 0))
        other = {row['kind']: row for row in self.client_for(self.other_teacher_user).get('/api/v1/reports/observations/').data}
        self.assertEqual(other['hand_raise']['total'], 0)


class HealthTests(ReportBase):
    def setUp(self):
        super().setUp()
        self.camera = Camera.objects.get(name='Laptop webcam')

    def log(self, status, minutes_ago, detail=''):
        entry = CameraStatusLog.objects.create(camera=self.camera, status=status, detail=detail)
        CameraStatusLog.objects.filter(pk=entry.pk).update(at=timezone.now() - timedelta(minutes=minutes_ago))

    def test_uptime_counts_only_online_intervals(self):
        self.log('online', 50)
        self.log('error', 35, 'The camera stopped sending frames.')
        self.log('online', 20)
        self.log('offline', 5)
        end = timezone.now()
        seconds = camera_uptime(self.camera, end - timedelta(hours=1), end)
        self.assertAlmostEqual(seconds, 30 * 60, delta=5)  # 15 minutes, then another 15

    def test_worker_killed_without_logging_offline_is_capped_by_its_heartbeat(self):
        self.log('online', 40)
        Camera.objects.filter(pk=self.camera.pk).update(last_heartbeat=timezone.now() - timedelta(minutes=30))
        self.camera.refresh_from_db()
        end = timezone.now()
        seconds = camera_uptime(self.camera, end - timedelta(hours=1), end)
        self.assertAlmostEqual(seconds, 10 * 60 + 20, delta=5)  # ten minutes plus the heartbeat timeout

    def test_health_reports_alerts_and_items_waiting_for_review(self):
        Camera.objects.filter(pk=self.camera.pk).update(
            status='error', last_error='The camera stopped sending frames.', last_heartbeat=timezone.now(),
        )
        data = self.client_for(self.admin).get('/api/v1/system/health/').data
        self.assertEqual(data['cameras'][0]['status'], 'error')
        self.assertIn('stopped sending frames', data['alerts'][0]['message'])
        self.assertEqual(data['pending_attendance'], 1)
        self.assertEqual(data['students']['active'], 3)
        self.assertIn('face', data['models'])

    def test_enabled_camera_with_no_worker_raises_an_alert(self):
        data = self.client_for(self.teacher_user).get('/api/v1/system/health/').data
        self.assertEqual(data['cameras'][0]['status'], 'offline')
        self.assertIn('no worker is reporting', data['alerts'][0]['message'])
        self.assertEqual(self.client_for(self.viewer).get('/api/v1/system/health/').status_code, 403)
