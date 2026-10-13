from datetime import timedelta
from pathlib import Path
from unittest import mock, skipUnless

import cv2
import numpy as np
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from apps.academics.models import ClassSession, Student
from apps.accounts.models import AuditLog
from apps.attendance.embeddings import decrypt_embedding, encrypt_embedding
from apps.attendance.models import AttendanceRecord, FaceEnrollment, PresenceWindow
from apps.attendance.services import Sighting, finalize_session, record_sightings
from apps.tests import BaseData
from vision.face import matcher
from vision.face.engine import DetectedFace, FaceEngine

TEST_KEY = Fernet.generate_key().decode()
MODEL_NAME = 'fake-model'


def unit(*values):
    vector = np.zeros(8, dtype=np.float32)
    vector[:len(values)] = values
    return vector / np.linalg.norm(vector)


ASHA = unit(1, 0, 0)
BALA = unit(0, 1, 0)
STRANGER = unit(0, 0, 1)


def face(embedding, size=160, score=0.95):
    return DetectedFace(box=(10, 10, 10 + size, 10 + size), score=score, landmarks=np.zeros((5, 2)), embedding=embedding)


class FakeEngine:
    model_name = MODEL_NAME

    def __init__(self, faces):
        self.faces = faces

    def analyze(self, image):
        return self.faces


def image_upload():
    ok, encoded = cv2.imencode('.jpg', np.full((64, 64, 3), 127, dtype=np.uint8))
    assert ok
    return SimpleUploadedFile('frame.jpg', encoded.tobytes(), content_type='image/jpeg')


class MatcherTests(SimpleTestCase):
    gallery = {1: np.stack([ASHA]), 2: np.stack([BALA])}

    def match(self, *embeddings):
        return matcher.match_faces(list(embeddings), self.gallery, confirm_threshold=0.5, review_threshold=0.35)

    def test_clear_match_is_confirmed(self):
        result = self.match(unit(1, 0.1, 0))[0]
        self.assertEqual((result.band, result.student_id), (matcher.CONFIRMED, 1))

    def test_stranger_is_unknown_and_gets_no_identity(self):
        result = self.match(STRANGER)[0]
        self.assertEqual((result.band, result.student_id), (matcher.UNKNOWN, None))

    def test_borderline_score_goes_to_review(self):
        result = self.match(unit(0.45, 0, 0.9))[0]  # similarity to Asha is about 0.45
        self.assertEqual((result.band, result.student_id), (matcher.REVIEW, 1))

    def test_ambiguous_between_two_students_goes_to_review(self):
        result = self.match(unit(1, 0.98, 0))[0]
        self.assertEqual(result.band, matcher.REVIEW)
        self.assertIn('close', result.reason)

    def test_two_faces_cannot_both_be_the_same_student(self):
        strong, weak = self.match(unit(1, 0, 0), unit(1, 0.2, 0.6))
        self.assertEqual((strong.band, strong.student_id), (matcher.CONFIRMED, 1))
        self.assertEqual((weak.band, weak.student_id), (matcher.REVIEW, 1))

    def test_empty_gallery_names_nobody(self):
        result = matcher.match_faces([ASHA], {}, 0.5, 0.35)[0]
        self.assertEqual(result.band, matcher.UNKNOWN)


@override_settings(FACE_EMBEDDING_KEY=TEST_KEY)
class FaceBase(BaseData):
    def setUp(self):
        Student.objects.filter(pk__in=[self.student.pk, self.outsider.pk]).update(consent_given=True)
        self.student.refresh_from_db()
        self.session = ClassSession.objects.create(
            class_group=self.group, subject=self.maths, teacher=self.teacher, date=timezone.localdate(),
            starts_at=timezone.now() - timedelta(minutes=2), ends_at=timezone.now() + timedelta(minutes=48),
            status=ClassSession.Status.ACTIVE,
        )

    def enroll(self, student, embedding):
        return FaceEnrollment.objects.create(
            student=student, embedding=encrypt_embedding(embedding), model_name=MODEL_NAME, detection_score=0.9,
        )

    def engine(self, *faces):
        return mock.patch('apps.attendance.face_views.get_engine', return_value=FakeEngine(list(faces)))


class EnrollmentTests(FaceBase):
    def url(self, student=None):
        return f'/api/v1/students/{(student or self.student).id}/face-enrollments/'

    def post(self, user=None, student=None):
        return self.client_for(user or self.admin).post(self.url(student), {'image': image_upload()}, format='multipart')

    def test_embedding_is_encrypted_and_round_trips(self):
        blob = encrypt_embedding(ASHA)
        self.assertNotIn(ASHA.tobytes(), blob)
        np.testing.assert_allclose(decrypt_embedding(blob), ASHA)

    def test_enrolment_refused_without_consent(self):
        Student.objects.filter(pk=self.student.pk).update(consent_given=False)
        with self.engine(face(ASHA)):
            self.assertEqual(self.post().status_code, 409)
        self.assertEqual(FaceEnrollment.objects.count(), 0)

    def test_successful_enrolment_stores_only_an_encrypted_embedding(self):
        with self.engine(face(ASHA)):
            response = self.post()
        self.assertEqual(response.status_code, 201)
        enrollment = FaceEnrollment.objects.get()
        self.assertNotIn(ASHA.tobytes(), bytes(enrollment.embedding))
        np.testing.assert_allclose(decrypt_embedding(enrollment.embedding), ASHA)
        self.assertEqual(enrollment.model_name, MODEL_NAME)
        self.assertTrue(AuditLog.objects.filter(action='enroll_face').exists())

    def test_rejects_no_face_two_faces_small_face_and_unclear_face(self):
        cases = {
            'none': [],
            'two': [face(ASHA), face(BALA)],
            'small': [face(ASHA, size=40)],
            'unclear': [face(ASHA, score=0.55)],
        }
        for name, faces in cases.items():
            with self.subTest(case=name), self.engine(*faces):
                self.assertEqual(self.post().status_code, 400)
        self.assertEqual(FaceEnrollment.objects.count(), 0)

    def test_withdrawing_consent_deletes_face_data(self):
        self.enroll(self.student, ASHA)
        response = self.client_for(self.admin).patch(f'/api/v1/students/{self.student.id}/', {'consent_given': False}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FaceEnrollment.objects.count(), 0)

    def test_delete_removes_all_face_data(self):
        self.enroll(self.student, ASHA)
        self.assertEqual(self.client_for(self.admin).delete(self.url()).status_code, 204)
        self.assertEqual(FaceEnrollment.objects.count(), 0)

    def test_teacher_cannot_enrol_student_of_another_class_and_viewer_cannot_enrol(self):
        with self.engine(face(BALA)):
            self.assertEqual(self.post(user=self.teacher_user, student=self.outsider).status_code, 403)
            self.assertEqual(self.post(user=self.viewer).status_code, 403)

    def test_missing_models_report_service_unavailable(self):
        from vision.face.engine import ModelNotAvailable

        with mock.patch('apps.attendance.face_views.get_engine', side_effect=ModelNotAvailable('missing')):
            self.assertEqual(self.post().status_code, 503)


class RecognitionTests(FaceBase):
    def recognize(self, *faces, user=None):
        with self.engine(*faces):
            return self.client_for(user or self.teacher_user).post(
                f'/api/v1/sessions/{self.session.id}/recognize/', {'image': image_upload()}, format='multipart',
            )

    def setUp(self):
        super().setUp()
        self.enroll(self.student, ASHA)
        self.enroll(self.outsider, BALA)  # enrolled, but in a different class

    def test_needs_two_confirmed_sightings_then_marks_present_once(self):
        first = self.recognize(face(ASHA))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['faces'][0]['band'], 'confirmed')
        self.assertEqual(AttendanceRecord.objects.count(), 0)

        second = self.recognize(face(ASHA))
        self.assertEqual(len(second.data['changed']), 1)
        for _ in range(3):
            self.recognize(face(ASHA))
        record = AttendanceRecord.objects.get()
        self.assertEqual((record.status, record.source, record.student), ('present', 'auto', self.student))
        self.assertEqual(PresenceWindow.objects.get().sightings, 5)

    def test_unknown_face_is_never_named_or_recorded(self):
        response = self.recognize(face(STRANGER), face(STRANGER))
        self.assertEqual([f['student'] for f in response.data['faces']], [None, None])
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_student_of_another_class_is_not_matched(self):
        response = self.recognize(face(BALA))
        self.assertEqual(response.data['faces'][0]['band'], 'unknown')
        self.assertEqual(response.data['enrolled_students'], 1)

    def test_uncertain_match_becomes_pending_not_present(self):
        self.recognize(face(unit(0.45, 0, 0.9)))
        record = AttendanceRecord.objects.get()
        self.assertEqual(record.status, 'pending')
        self.assertTrue(record.note)

    def test_pending_is_upgraded_by_confirmed_sightings(self):
        self.recognize(face(unit(0.45, 0, 0.9)))
        self.recognize(face(ASHA))
        self.recognize(face(ASHA))
        self.assertEqual(AttendanceRecord.objects.get().status, 'present')

    def test_manual_record_is_not_overwritten(self):
        AttendanceRecord.objects.create(session=self.session, student=self.student, status='absent', source='manual')
        for _ in range(3):
            self.recognize(face(ASHA))
        self.assertEqual(AttendanceRecord.objects.get().status, 'absent')

    def test_arrival_after_grace_period_is_late(self):
        ClassSession.objects.filter(pk=self.session.pk).update(starts_at=timezone.now() - timedelta(minutes=25))
        self.recognize(face(ASHA))
        self.recognize(face(ASHA))
        self.assertEqual(AttendanceRecord.objects.get().status, 'late')

    def test_requires_active_session_and_own_session(self):
        self.assertEqual(self.recognize(face(ASHA), user=self.other_teacher_user).status_code, 403)
        ClassSession.objects.filter(pk=self.session.pk).update(status=ClassSession.Status.SCHEDULED)
        self.assertEqual(self.recognize(face(ASHA)).status_code, 409)

    def test_student_without_consent_is_not_matched(self):
        Student.objects.filter(pk=self.student.pk).update(consent_given=False)
        self.assertEqual(self.recognize(face(ASHA)).data['faces'][0]['band'], 'unknown')


class SessionRuleTests(FaceBase):
    def test_left_early_when_last_seen_long_before_the_end(self):
        start = timezone.now() - timedelta(minutes=50)
        ClassSession.objects.filter(pk=self.session.pk).update(starts_at=start, ends_at=start + timedelta(minutes=50))
        self.session.refresh_from_db()
        confirmed = [Sighting(self.student.id, matcher.CONFIRMED, 0.8)]
        record_sightings(self.session, confirmed, at=start + timedelta(minutes=1))
        record_sightings(self.session, confirmed, at=start + timedelta(minutes=2))
        self.assertEqual(finalize_session(self.session), 0)
        self.assertEqual(AttendanceRecord.objects.get().status, 'left_early')

    def test_seen_until_the_end_stays_present(self):
        start = timezone.now() - timedelta(minutes=50)
        ClassSession.objects.filter(pk=self.session.pk).update(starts_at=start, ends_at=start + timedelta(minutes=50))
        self.session.refresh_from_db()
        confirmed = [Sighting(self.student.id, matcher.CONFIRMED, 0.8)]
        for minute in (1, 20, 46):
            record_sightings(self.session, confirmed, at=start + timedelta(minutes=minute))
        finalize_session(self.session)
        self.assertEqual(AttendanceRecord.objects.get().status, 'present')
        self.assertEqual(PresenceWindow.objects.count(), 3)


class ReportTests(FaceBase):
    def setUp(self):
        super().setUp()
        second = Student.objects.create(roll_number='A002', full_name='Chitra')
        second.class_groups.add(self.group)
        statuses = {self.student: ['present', 'late', 'absent', 'pending'], second: ['absent', 'absent', 'present', 'present']}
        for day in range(4):
            session = ClassSession.objects.create(
                class_group=self.group, subject=self.maths, teacher=self.teacher,
                date=timezone.localdate() - timedelta(days=day + 1), starts_at=timezone.now() - timedelta(days=day + 1),
            )
            for student, values in statuses.items():
                AttendanceRecord.objects.create(session=session, student=student, status=values[day])

    def test_percentages_exclude_pending(self):
        rows = {row['roll_number']: row for row in self.client_for(self.teacher_user).get('/api/v1/reports/attendance/').data}
        self.assertEqual(rows['A001']['attendance_percent'], 66.7)  # 2 attended of 3 decided
        self.assertEqual(rows['A001']['pending'], 1)
        self.assertEqual(rows['A002']['attendance_percent'], 50.0)

    def test_date_filter_and_csv_export(self):
        client = self.client_for(self.admin)
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        rows = client.get(f'/api/v1/reports/attendance/?date_from={yesterday}').data
        self.assertEqual([row['sessions'] for row in rows], [1, 1])
        export = client.get('/api/v1/reports/attendance/?export=csv')
        self.assertEqual(export['Content-Type'], 'text/csv')
        lines = export.content.decode().strip().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[1].startswith('A001,Asha,4,1,1,0,1,1,66.7'))

    def test_other_teacher_sees_nothing_and_viewer_is_refused(self):
        self.assertEqual(self.client_for(self.other_teacher_user).get('/api/v1/reports/attendance/').data, [])
        self.assertEqual(self.client_for(self.viewer).get('/api/v1/reports/attendance/').status_code, 403)


MODELS_PRESENT = Path(settings.FACE_DETECTOR_MODEL).is_file() and Path(settings.FACE_RECOGNIZER_MODEL).is_file()


@skipUnless(MODELS_PRESENT, 'face model files are not installed')
class RealEngineTests(SimpleTestCase):
    def test_blank_image_has_no_faces(self):
        engine = FaceEngine(Path(settings.FACE_DETECTOR_MODEL), Path(settings.FACE_RECOGNIZER_MODEL))
        self.assertEqual(engine.analyze(np.full((480, 640, 3), 120, dtype=np.uint8)), [])
