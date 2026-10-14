import json
from datetime import date, timedelta

from django.utils import timezone

from apps.academics.models import ClassSession, ConsentRecord, PrivacySettings, Student, Subject
from apps.academics.privacy import (
    apply_retention,
    compliance_summary,
    erase_student,
    export_student_data,
    is_minor,
    withdraw_consent,
)
from apps.accounts.models import AuditLog
from apps.attendance.models import AttendanceRecord, FaceEnrollment
from apps.monitoring.models import ClassroomEvent
from apps.tests import BaseData


def enrol_face(student, model='buffalo_l'):
    return FaceEnrollment.objects.create(student=student, model_name=model, embedding=b'x' * 16, detection_score=0.9)


class AgeTests(BaseData):
    def test_minor_is_worked_out_from_date_of_birth(self):
        today = date(2026, 10, 14)
        self.student.date_of_birth = date(2012, 1, 1)
        self.assertTrue(is_minor(self.student, today))
        self.student.date_of_birth = date(2006, 1, 1)
        self.assertFalse(is_minor(self.student, today))
        self.student.date_of_birth = None
        self.assertIsNone(is_minor(self.student))


class WithdrawAndEraseTests(BaseData):
    def setUp(self):
        self.student.consent_given = True
        self.student.consent_recorded_at = timezone.now()
        self.student.save()
        enrol_face(self.student)
        enrol_face(self.student)
        self.session = ClassSession.objects.create(
            class_group=self.group, subject=self.maths, teacher=self.teacher, date=timezone.localdate(),
            starts_at=timezone.now(), status='closed',
        )
        AttendanceRecord.objects.create(session=self.session, student=self.student, status='present')
        self.event = ClassroomEvent.objects.create(
            session=self.session, kind='hand_raise', subject='1', student=self.student, started_at=timezone.now(),
            confidence=0.9, summary='Hand raised',
        )

    def test_withdrawing_consent_deletes_face_data_but_keeps_attendance(self):
        result = withdraw_consent(self.student, given_by='Asha', note='asked in person')
        self.assertEqual(result['face_enrollments_deleted'], 2)
        self.student.refresh_from_db()
        self.assertFalse(self.student.consent_given)
        self.assertIsNotNone(self.student.consent_withdrawn_at)
        self.assertEqual(FaceEnrollment.objects.filter(student=self.student).count(), 0)
        self.assertEqual(AttendanceRecord.objects.filter(student=self.student).count(), 1)  # register kept
        self.assertEqual(self.student.consent_records.filter(action='withdrawn').count(), 1)

    def test_erase_removes_the_student_and_personal_data_but_unlinks_observations(self):
        counts = erase_student(self.student)
        self.assertEqual((counts['face_enrollments'], counts['attendance_records']), (2, 1))
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())
        self.assertEqual(FaceEnrollment.objects.count(), 0)
        self.event.refresh_from_db()
        self.assertIsNone(self.event.student_id)  # the room's record survives, without the link

    def test_export_lists_what_is_held_without_dumping_face_vectors(self):
        ConsentRecord.objects.create(student=self.student, action='granted', given_by='Asha')
        data = export_student_data(self.student)
        self.assertEqual(data['student']['roll_number'], self.student.roll_number)
        self.assertEqual(data['face_data']['enrollments_held'], 2)
        self.assertEqual(len(data['attendance']), 1)
        self.assertIn('not included', data['face_data']['note'])
        # It must serialise cleanly for download.
        json.dumps(data, default=str)


class RetentionTests(BaseData):
    def test_retention_deletes_only_data_past_each_period(self):
        PrivacySettings.objects.update_or_create(pk=1, defaults={
            'face_retention_days': 30, 'attendance_retention_days': 365, 'event_retention_days': 30,
        })
        old_face = enrol_face(self.student)
        FaceEnrollment.objects.filter(pk=old_face.pk).update(created_at=timezone.now() - timedelta(days=60))
        enrol_face(self.student)  # recent, kept
        old_session = ClassSession.objects.create(
            class_group=self.group, subject=self.maths, date=timezone.localdate() - timedelta(days=400),
            starts_at=timezone.now() - timedelta(days=400), status='closed',
        )
        AttendanceRecord.objects.create(session=old_session, student=self.student, status='present')
        event = ClassroomEvent.objects.create(
            session=old_session, kind='phone', subject='1', started_at=timezone.now() - timedelta(days=60),
            confidence=0.5, summary='x',
        )

        removed = apply_retention()
        self.assertEqual(removed['face_enrollments'], 1)
        self.assertEqual(removed['attendance_records'], 1)
        self.assertEqual(removed['observations'], 1)
        self.assertEqual(FaceEnrollment.objects.count(), 1)  # the recent one remains
        self.assertFalse(ClassroomEvent.objects.filter(pk=event.pk).exists())

    def test_zero_days_keeps_everything(self):
        PrivacySettings.objects.update_or_create(pk=1, defaults={
            'face_retention_days': 0, 'attendance_retention_days': 0, 'event_retention_days': 0,
        })
        old = enrol_face(self.student)
        FaceEnrollment.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=9999))
        self.assertEqual(apply_retention()['face_enrollments'], 0)
        self.assertEqual(FaceEnrollment.objects.count(), 1)


class ComplianceSummaryTests(BaseData):
    def test_summary_flags_minors_without_guardian_and_faces_without_consent(self):
        self.student.date_of_birth = date(2012, 1, 1)  # a minor
        self.student.consent_given = True
        self.student.save()
        enrol_face(self.outsider)  # has a face but no consent recorded
        summary = compliance_summary()
        self.assertEqual(summary['with_consent'], 1)
        self.assertIn(self.student.roll_number, summary['minors_missing_guardian_contact'])
        self.assertIn(self.outsider.roll_number, summary['face_data_without_consent'])
        self.assertEqual(summary['retention']['face_days'], PrivacySettings.load().face_retention_days)


class PrivacyApiTests(BaseData):
    def setUp(self):
        self.student.consent_given = True
        self.student.save()
        enrol_face(self.student)
        # The teacher must teach this student's class to see and manage them.
        ClassSession.objects.create(
            class_group=self.group, subject=self.maths, teacher=self.teacher, date=timezone.localdate(),
            starts_at=timezone.now(), status='closed',
        )

    def test_consent_grant_and_withdraw_through_the_api(self):
        client = self.client_for(self.teacher_user)
        url = f'/api/v1/students/{self.student.id}/consent/'
        response = client.post(url, {'action': 'withdrawn', 'given_by': 'Asha'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['face_enrollments_deleted'], 1)
        self.student.refresh_from_db()
        self.assertFalse(self.student.consent_given)
        self.assertEqual(AuditLog.objects.filter(action='consent_withdrawn').count(), 1)
        granted = client.post(url, {'action': 'granted', 'given_by': 'Asha'}, format='json')
        self.assertEqual(granted.status_code, 200)
        history = client.get(f'/api/v1/students/{self.student.id}/consent_history/')
        self.assertEqual(len(history.data), 2)
        self.assertEqual(client.post(url, {'action': 'nonsense'}, format='json').status_code, 400)

    def test_export_downloads_json(self):
        response = self.client_for(self.admin).get(f'/api/v1/students/{self.student.id}/export_data/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('attachment', response['Content-Disposition'])
        body = json.loads(response.content)
        self.assertEqual(body['student']['roll_number'], self.student.roll_number)

    def test_erase_is_admin_only_and_needs_the_roll_number(self):
        teacher = self.client_for(self.teacher_user)
        self.assertEqual(teacher.post(f'/api/v1/students/{self.student.id}/erase/', {'confirm': self.student.roll_number}, format='json').status_code, 403)
        admin = self.client_for(self.admin)
        self.assertEqual(admin.post(f'/api/v1/students/{self.student.id}/erase/', {'confirm': 'wrong'}, format='json').status_code, 400)
        ok = admin.post(f'/api/v1/students/{self.student.id}/erase/', {'confirm': self.student.roll_number}, format='json')
        self.assertEqual(ok.status_code, 200)
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())
        self.assertEqual(AuditLog.objects.filter(action='erase_student').count(), 1)

    def test_compliance_and_privacy_settings_endpoints(self):
        self.assertTrue(self.client_for(self.teacher_user).get('/api/v1/compliance/').data['active_students'] >= 1)
        self.assertEqual(self.client_for(self.viewer).get('/api/v1/compliance/').status_code, 403)
        url = '/api/v1/settings/privacy/'
        self.assertTrue(self.client_for(self.teacher_user).get(url).data['blur_unconsented'])
        self.assertEqual(self.client_for(self.teacher_user).put(url, {'blur_unconsented': False}, format='json').status_code, 403)
        admin = self.client_for(self.admin)
        saved = admin.put(url, {'face_retention_days': 90}, format='json')
        self.assertEqual((saved.status_code, saved.data['face_retention_days']), (200, 90))
        self.assertEqual(admin.put(url, {'face_retention_days': 99999999}, format='json').status_code, 400)
        self.assertEqual(admin.post(url, {}, format='json').status_code, 200)  # run clean-up now
