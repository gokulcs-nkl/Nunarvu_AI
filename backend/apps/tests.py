from datetime import date, time

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from apps.academics.models import (
    ClassGroup, ClassSession, Holiday, Period, Room, Student, Subject, Teacher, TimetableEntry,
)
from apps.academics.services import generate_sessions_for_date, periods_for_date
from apps.accounts.models import AuditLog, Profile, Role
from apps.attendance.models import AttendanceRecord
from apps.monitoring.models import Camera

User = get_user_model()

MONDAY = date(2026, 10, 12)
SATURDAY = date(2026, 10, 17)


def make_user(username, role):
    user = User.objects.create_user(username=username, password='test-pass-123')
    Profile.objects.create(user=user, role=role)
    return user


class BaseData(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user('admin', Role.ADMIN)
        cls.teacher_user = make_user('teacher', Role.TEACHER)
        cls.other_teacher_user = make_user('teacher2', Role.TEACHER)
        cls.viewer = make_user('viewer', Role.VIEWER)
        cls.teacher = Teacher.objects.create(user=cls.teacher_user, employee_code='T1')
        cls.other_teacher = Teacher.objects.create(user=cls.other_teacher_user, employee_code='T2')
        cls.group = ClassGroup.objects.create(name='CSE-A', academic_year='2026-27')
        cls.other_group = ClassGroup.objects.create(name='CSE-B', academic_year='2026-27')
        cls.maths = Subject.objects.create(code='MA101', name='Maths')
        cls.room = Room.objects.create(name='R101')
        cls.student = Student.objects.create(roll_number='A001', full_name='Asha')
        cls.student.class_groups.add(cls.group)
        cls.outsider = Student.objects.create(roll_number='B001', full_name='Bala')
        cls.outsider.class_groups.add(cls.other_group)

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client


class PeriodResolutionTests(BaseData):
    def setUp(self):
        Period.objects.create(number=1, start_time=time(9, 0), end_time=time(9, 50))
        Period.objects.create(number=2, start_time=time(10, 0), end_time=time(10, 50))

    def test_default_schedule_applies_when_no_override(self):
        self.assertEqual([p.start_time for p in periods_for_date(MONDAY)], [time(9, 0), time(10, 0)])

    def test_weekday_override_replaces_default(self):
        Period.objects.create(number=1, weekday=5, start_time=time(8, 0), end_time=time(8, 30))
        self.assertEqual([p.start_time for p in periods_for_date(SATURDAY)], [time(8, 0)])
        self.assertEqual(len(periods_for_date(MONDAY)), 2)

    def test_specific_date_beats_weekday(self):
        Period.objects.create(number=1, weekday=5, start_time=time(8, 0), end_time=time(8, 30))
        Period.objects.create(number=1, specific_date=SATURDAY, start_time=time(11, 0), end_time=time(11, 20))
        self.assertEqual([p.start_time for p in periods_for_date(SATURDAY)], [time(11, 0)])

    def test_no_periods_configured_is_allowed(self):
        Period.objects.all().delete()
        self.assertEqual(periods_for_date(MONDAY), [])
        self.assertEqual(generate_sessions_for_date(MONDAY), 0)

    def test_duplicate_number_in_same_scope_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Period.objects.create(number=1, start_time=time(12, 0), end_time=time(12, 30))

    def test_api_rejects_overlap_and_bad_times(self):
        client = self.client_for(self.admin)
        overlap = client.post('/api/v1/periods/', {'number': 3, 'start_time': '09:30', 'end_time': '10:10'}, format='json')
        self.assertEqual(overlap.status_code, 400)
        backwards = client.post('/api/v1/periods/', {'number': 3, 'start_time': '12:00', 'end_time': '11:00'}, format='json')
        self.assertEqual(backwards.status_code, 400)
        ok = client.post('/api/v1/periods/', {'number': 3, 'start_time': '11:00', 'end_time': '11:50'}, format='json')
        self.assertEqual(ok.status_code, 201)

    def test_same_times_allowed_on_a_different_day(self):
        client = self.client_for(self.admin)
        response = client.post(
            '/api/v1/periods/', {'number': 1, 'weekday': 5, 'start_time': '09:00', 'end_time': '09:50'}, format='json',
        )
        self.assertEqual(response.status_code, 201)

    def test_copy_day(self):
        client = self.client_for(self.admin)
        response = client.post('/api/v1/periods/copy-day/', {'to_weekday': 5}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Period.objects.filter(weekday=5).count(), 2)


class SessionGenerationTests(BaseData):
    def setUp(self):
        Period.objects.create(number=1, start_time=time(9, 0), end_time=time(9, 50))
        TimetableEntry.objects.create(
            class_group=self.group, subject=self.maths, teacher=self.teacher, room=self.room,
            weekday=0, period_number=1,
        )

    def test_generates_once_and_is_idempotent(self):
        self.assertEqual(generate_sessions_for_date(MONDAY), 1)
        self.assertEqual(generate_sessions_for_date(MONDAY), 0)
        session = ClassSession.objects.get()
        self.assertEqual(session.source, ClassSession.Source.TIMETABLE)
        self.assertEqual(session.teacher, self.teacher)
        self.assertLess(session.starts_at, session.ends_at)

    def test_other_weekday_gets_nothing(self):
        self.assertEqual(generate_sessions_for_date(SATURDAY), 0)

    def test_holiday_gets_nothing(self):
        Holiday.objects.create(date=MONDAY, name='Holiday')
        self.assertEqual(generate_sessions_for_date(MONDAY), 0)

    def test_entry_without_matching_period_is_skipped(self):
        TimetableEntry.objects.create(class_group=self.other_group, subject=self.maths, weekday=0, period_number=7)
        self.assertEqual(generate_sessions_for_date(MONDAY), 1)

    def test_room_double_booking_rejected(self):
        client = self.client_for(self.admin)
        response = client.post('/api/v1/timetable/', {
            'class_group': self.other_group.id, 'subject': self.maths.id, 'room': self.room.id,
            'weekday': 0, 'period_number': 1,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('room', response.data)


class AttendanceTests(BaseData):
    def setUp(self):
        Period.objects.create(number=1, start_time=time(9, 0), end_time=time(9, 50))
        TimetableEntry.objects.create(
            class_group=self.group, subject=self.maths, teacher=self.teacher, weekday=0, period_number=1,
        )
        generate_sessions_for_date(MONDAY)
        self.session = ClassSession.objects.get()

    def test_one_record_per_session_and_student_in_database(self):
        AttendanceRecord.objects.create(session=self.session, student=self.student, status='present')
        with self.assertRaises(IntegrityError), transaction.atomic():
            AttendanceRecord.objects.create(session=self.session, student=self.student, status='late')

    def test_api_rejects_duplicate_and_unenrolled_student(self):
        client = self.client_for(self.teacher_user)
        payload = {'session': self.session.id, 'student': self.student.id, 'status': 'present'}
        self.assertEqual(client.post('/api/v1/attendance/', payload, format='json').status_code, 201)
        self.assertEqual(client.post('/api/v1/attendance/', payload, format='json').status_code, 400)
        outsider = {'session': self.session.id, 'student': self.outsider.id, 'status': 'present'}
        self.assertEqual(client.post('/api/v1/attendance/', outsider, format='json').status_code, 400)

    def test_manual_correction_is_audited(self):
        client = self.client_for(self.teacher_user)
        created = client.post(
            '/api/v1/attendance/', {'session': self.session.id, 'student': self.student.id, 'status': 'absent'}, format='json',
        )
        response = client.patch(f"/api/v1/attendance/{created.data['id']}/", {'status': 'present'}, format='json')
        self.assertEqual(response.status_code, 200)
        entry = AuditLog.objects.get(action='correct_attendance')
        self.assertEqual(entry.detail, {'from': 'absent', 'to': 'present'})
        self.assertEqual(entry.actor, self.teacher_user)

    def test_other_teacher_cannot_mark_or_see(self):
        client = self.client_for(self.other_teacher_user)
        payload = {'session': self.session.id, 'student': self.student.id, 'status': 'present'}
        self.assertEqual(client.post('/api/v1/attendance/', payload, format='json').status_code, 403)
        self.assertEqual(client.get('/api/v1/sessions/').data['count'], 0)

    def test_closing_session_marks_missing_students_absent(self):
        second = Student.objects.create(roll_number='A002', full_name='Chitra')
        second.class_groups.add(self.group)
        AttendanceRecord.objects.create(session=self.session, student=self.student, status='present')
        client = self.client_for(self.teacher_user)
        response = client.post(f'/api/v1/sessions/{self.session.id}/close/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AttendanceRecord.objects.get(student=second).status, 'absent')
        self.assertEqual(AttendanceRecord.objects.get(student=self.student).status, 'present')
        self.assertEqual(client.post(f'/api/v1/sessions/{self.session.id}/close/').status_code, 409)

    def test_teacher_can_start_a_manual_session_without_any_schedule(self):
        client = self.client_for(self.teacher_user)
        response = client.post('/api/v1/sessions/', {
            'class_group': self.group.id, 'subject': self.maths.id, 'date': '2026-10-13',
            'starts_at': '2026-10-13T14:00:00+05:30',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        session = ClassSession.objects.get(pk=response.data['id'])
        self.assertEqual(session.source, ClassSession.Source.MANUAL)
        self.assertEqual(session.teacher, self.teacher)


class PermissionTests(BaseData):
    LIST_URLS = [
        'users', 'audit-log', 'teachers', 'class-groups', 'subjects', 'rooms', 'students', 'enrollments',
        'periods', 'holidays', 'timetable', 'sessions', 'attendance', 'cameras',
    ]

    def test_every_endpoint_rejects_anonymous_requests(self):
        client = APIClient()
        for name in self.LIST_URLS + ['me', 'me/notifications']:
            with self.subTest(endpoint=name):
                self.assertEqual(client.get(f'/api/v1/{name}/').status_code, 401)

    def test_viewer_is_read_only_and_cannot_read_sensitive_data(self):
        client = self.client_for(self.viewer)
        self.assertEqual(client.get('/api/v1/class-groups/').status_code, 200)
        self.assertEqual(client.post('/api/v1/class-groups/', {'name': 'X', 'academic_year': 'Y'}, format='json').status_code, 403)
        for name in ('students', 'cameras', 'users', 'audit-log'):
            with self.subTest(endpoint=name):
                self.assertEqual(client.get(f'/api/v1/{name}/').status_code, 403)

    def test_teacher_cannot_manage_students_users_or_cameras(self):
        client = self.client_for(self.teacher_user)
        self.assertEqual(client.post('/api/v1/students/', {'roll_number': 'Z1', 'full_name': 'Z'}, format='json').status_code, 403)
        self.assertEqual(client.get('/api/v1/users/').status_code, 403)
        self.assertEqual(client.post('/api/v1/cameras/', {'name': 'C', 'source': '1'}, format='json').status_code, 403)

    def test_teacher_sees_only_students_of_own_classes(self):
        TimetableEntry.objects.create(class_group=self.group, subject=self.maths, teacher=self.teacher, weekday=0, period_number=1)
        rolls = [s['roll_number'] for s in self.client_for(self.teacher_user).get('/api/v1/students/').data['results']]
        self.assertEqual(rolls, ['A001'])

    def test_admin_manages_users_with_roles(self):
        client = self.client_for(self.admin)
        response = client.post('/api/v1/users/', {'username': 'newt', 'password': 'a-Strong-pass-91', 'role': 'teacher'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['role'], 'teacher')
        self.assertNotIn('password', response.data)
        self.assertTrue(User.objects.get(username='newt').check_password('a-Strong-pass-91'))

    def test_me_reports_role_and_superuser_is_admin(self):
        self.assertEqual(self.client_for(self.viewer).get('/api/v1/me/').data['role'], 'viewer')
        root = User.objects.create_superuser('root', password='test-pass-123')
        self.assertEqual(self.client_for(root).get('/api/v1/me/').data['role'], 'admin')

    def test_legacy_pages_require_login(self):
        for path in ('/students/attendance/', '/students/attendance/export/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login/', response['Location'])
        response = self.client.post('/process-face-recognition/', data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 302)


class StudentAndCameraTests(BaseData):
    def test_consent_timestamp_follows_consent_flag(self):
        client = self.client_for(self.admin)
        created = client.post('/api/v1/students/', {
            'roll_number': 'A010', 'full_name': 'Devi', 'consent_given': True, 'class_groups': [self.group.id],
        }, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertIsNotNone(created.data['consent_recorded_at'])
        withdrawn = client.patch(f"/api/v1/students/{created.data['id']}/", {'consent_given': False}, format='json')
        self.assertIsNone(withdrawn.data['consent_recorded_at'])
        self.assertTrue(AuditLog.objects.filter(action='update', target_type='academics.Student').exists())

    def test_duplicate_roll_number_rejected(self):
        response = self.client_for(self.admin).post('/api/v1/students/', {'roll_number': 'A001', 'full_name': 'Dup'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_default_webcam_exists_and_sources_are_validated(self):
        self.assertTrue(Camera.objects.filter(name='Laptop webcam', source='0').exists())
        client = self.client_for(self.admin)
        bad = client.post('/api/v1/cameras/', {'name': 'IP', 'source_type': 'rtsp', 'source': 'not-a-url'}, format='json')
        self.assertEqual(bad.status_code, 400)
        good = client.post('/api/v1/cameras/', {'name': 'IP', 'source_type': 'rtsp', 'source': 'rtsp://10.0.0.5/stream'}, format='json')
        self.assertEqual(good.status_code, 201)


class SessionAuthTests(BaseData):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # reset the login throttle between tests
        self.browser = APIClient(enforce_csrf_checks=True)

    def _csrf(self):
        return self.browser.get('/api/v1/auth/csrf/').data['csrfToken']

    def test_login_requires_csrf_token(self):
        response = self.browser.post('/api/v1/auth/login/', {'username': 'admin', 'password': 'test-pass-123'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_login_me_write_logout_flow(self):
        token = self._csrf()
        bad = self.browser.post(
            '/api/v1/auth/login/', {'username': 'admin', 'password': 'wrong'}, format='json', HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(bad.status_code, 401)
        good = self.browser.post(
            '/api/v1/auth/login/', {'username': 'admin', 'password': 'test-pass-123'}, format='json', HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(good.status_code, 200)
        self.assertEqual(good.data['role'], 'admin')
        self.assertEqual(self.browser.get('/api/v1/me/').data['username'], 'admin')

        token = self.browser.cookies['csrftoken'].value
        payload = {'name': 'CSE-C', 'academic_year': '2026-27'}
        self.assertEqual(self.browser.post('/api/v1/class-groups/', payload, format='json').status_code, 403)
        created = self.browser.post('/api/v1/class-groups/', payload, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(created.status_code, 201)

        self.assertEqual(self.browser.post('/api/v1/auth/logout/', HTTP_X_CSRFTOKEN=token).status_code, 204)
        self.assertEqual(self.browser.get('/api/v1/me/').status_code, 401)

    def test_login_is_rate_limited(self):
        token = self._csrf()
        statuses = [
            self.browser.post(
                '/api/v1/auth/login/', {'username': 'admin', 'password': 'wrong'}, format='json', HTTP_X_CSRFTOKEN=token,
            ).status_code
            for _ in range(11)
        ]
        self.assertEqual(statuses[:10], [401] * 10)
        self.assertEqual(statuses[10], 429)
