import time
from datetime import timedelta
from unittest import mock

import numpy as np
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.academics.models import ClassGroup, ClassSession, Room, Student, Subject, Teacher
from apps.accounts.models import Profile, Role
from apps.attendance.embeddings import encrypt_embedding
from apps.attendance.models import AttendanceRecord, FaceEnrollment
from apps.monitoring import live
from apps.monitoring.consumers import SessionConsumer
from apps.monitoring.models import Camera, CameraStatusLog
from apps.monitoring.worker import CameraWorker
from apps.test_face_attendance import ASHA, BALA, MODEL_NAME, STRANGER, FaceBase, image_upload
from vision.capture import FrameGrabber
from vision.face.engine import FaceBox
from vision.face.tracker import FaceTracker, iou

User = get_user_model()
TEST_KEY = Fernet.generate_key().decode()
TOKEN = 'worker-test-token'
FRAME = np.full((480, 640, 3), 60, dtype=np.uint8)


class TrackerTests(SimpleTestCase):
    def test_iou(self):
        self.assertEqual(iou((0, 0, 10, 10), (20, 20, 30, 30)), 0.0)
        self.assertAlmostEqual(iou((0, 0, 10, 10), (0, 0, 10, 10)), 1.0)

    def test_moving_face_keeps_its_track_and_a_new_face_gets_a_new_one(self):
        tracker = FaceTracker()
        first = tracker.update([(100, 100, 200, 200)], now=0.0)[0]
        moved, newcomer = tracker.update([(110, 105, 210, 205), (400, 100, 500, 200)], now=0.2)
        self.assertEqual(moved.id, first.id)
        self.assertNotEqual(newcomer.id, first.id)

    def test_face_that_leaves_is_forgotten_and_returns_as_a_new_track(self):
        tracker = FaceTracker(max_gap=1.5)
        first = tracker.update([(100, 100, 200, 200)], now=0.0)[0]
        tracker.update([], now=1.0)
        self.assertIn(first.id, tracker.tracks)
        tracker.update([], now=2.0)
        self.assertNotIn(first.id, tracker.tracks)
        again = tracker.update([(100, 100, 200, 200)], now=2.2)[0]
        self.assertNotEqual(again.id, first.id)


class FakeCapture:
    def __init__(self, opened=True, frames=None):
        self.opened = opened
        self.frames = frames  # None means frames forever
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if self.frames is None:
            return True, FRAME
        if self.frames > 0:
            self.frames -= 1
            return True, FRAME
        return False, None

    def get(self, prop):
        return 0

    def release(self):
        self.released = True


class FrameGrabberTests(SimpleTestCase):
    def test_reconnects_after_open_failure_and_after_the_stream_dies(self):
        captures = [FakeCapture(opened=False), FakeCapture(frames=3), FakeCapture()]
        handed_out = []

        def opener(source_type, source):
            capture = captures[min(len(handed_out), len(captures) - 1)]
            handed_out.append(capture)
            return capture

        grabber = FrameGrabber('rtsp', 'rtsp://camera', opener=opener, sleep=lambda seconds: time.sleep(0.001))
        grabber.start()
        try:
            deadline = time.time() + 5
            while time.time() < deadline and not (grabber.reconnects >= 2 and grabber.connected):
                time.sleep(0.01)
            frame, frame_time = grabber.latest()
            self.assertGreaterEqual(grabber.reconnects, 2)
            self.assertTrue(grabber.connected)
            self.assertIsNotNone(frame)
            self.assertGreater(frame_time, 0)
            self.assertTrue(captures[0].released and captures[1].released)
        finally:
            grabber.stop()

    def test_reports_an_error_while_the_camera_is_unavailable(self):
        grabber = FrameGrabber('webcam', '0', opener=lambda *_: FakeCapture(opened=False), sleep=lambda seconds: time.sleep(0.001))
        grabber.start()
        try:
            deadline = time.time() + 3
            while time.time() < deadline and not grabber.last_error:
                time.sleep(0.01)
            self.assertFalse(grabber.connected)
            self.assertIn('could not be opened', grabber.last_error)
            self.assertIsNone(grabber.latest()[0])
        finally:
            grabber.stop()


class BlackFrameTests(SimpleTestCase):
    def test_black_picture_is_reported_as_a_camera_problem_and_recovers(self):
        from vision.capture import BLACK_MESSAGE, is_black

        self.assertTrue(is_black(np.zeros((480, 640, 3), dtype=np.uint8)))
        self.assertFalse(is_black(np.full((480, 640, 3), 40, dtype=np.uint8)))

        class Capture(FakeCapture):
            picture = np.zeros((480, 640, 3), dtype=np.uint8)

            def read(self):
                return True, self.picture

        capture = Capture()
        ticks = iter(range(10_000))
        grabber = FrameGrabber(
            'webcam', '0', opener=lambda *_: capture, sleep=lambda seconds: time.sleep(0.001),
            clock=lambda: next(ticks) * 0.5,  # each read advances the clock by half a second
        )
        grabber.start()
        try:
            deadline = time.time() + 5
            while time.time() < deadline and grabber.reconnects == 0:
                time.sleep(0.01)
            self.assertFalse(grabber.connected)
            self.assertEqual(grabber.last_error, BLACK_MESSAGE)
            self.assertIsNone(grabber.latest()[0])
            self.assertGreaterEqual(grabber.reconnects, 1)  # the camera was closed and opened again

            Capture.picture = np.full((480, 640, 3), 90, dtype=np.uint8)  # the other program lets go
            deadline = time.time() + 5
            while time.time() < deadline and not grabber.connected:
                time.sleep(0.01)
            self.assertTrue(grabber.connected)
            self.assertEqual(grabber.last_error, '')
            self.assertIsNotNone(grabber.latest()[0])
        finally:
            grabber.stop()


class FakeEngine:
    """Returns preset faces; each face's landmarks carry the index of the embedding to hand back."""
    model_name = MODEL_NAME

    def __init__(self, vectors):
        self.vectors = vectors
        self.present = list(range(len(vectors)))
        self.embed_calls = 0

    def detect(self, frame):
        return [
            FaceBox(box=(50 + 200 * index, 100, 150 + 200 * index, 200), score=0.9, landmarks=np.full((5, 2), index))
            for index in self.present
        ]

    def embed(self, frame, landmarks):
        self.embed_calls += 1
        return self.vectors[int(landmarks[0, 0])]


class RecordingPublisher:
    def __init__(self):
        self.states, self.frames = [], []

    def publish_state(self, payload):
        self.states.append(payload)

    def publish_frame(self, camera_id, jpeg):
        self.frames.append((camera_id, jpeg))


class WorkerTests(FaceBase):
    def setUp(self):
        super().setUp()
        self.camera = Camera.objects.get(name='Laptop webcam')
        self.enroll(self.student, ASHA)
        self.now = time.time()

    def worker(self, *vectors):
        self.engine_stub = FakeEngine(list(vectors))
        return CameraWorker(self.camera, self.engine_stub, RecordingPublisher(), grabber=mock.Mock())

    def test_marks_present_after_two_recognitions_and_embeds_once_per_interval(self):
        worker = self.worker(ASHA)
        first = worker.step(FRAME, self.now)
        self.assertEqual(first['faces'][0]['band'], 'confirmed')
        self.assertEqual(first['faces'][0]['student_name'], 'Asha')
        self.assertEqual(first['session'], self.session.id)
        for offset in (0.2, 0.4, 0.6):  # frames inside the interval reuse the identity
            worker.step(FRAME, self.now + offset)
        self.assertEqual(self.engine_stub.embed_calls, 1)
        self.assertEqual(AttendanceRecord.objects.count(), 0)

        second = worker.step(FRAME, self.now + 3.1)
        self.assertEqual(self.engine_stub.embed_calls, 2)
        self.assertEqual(second['changed'], [{'student': self.student.id, 'status': 'present', 'student_name': 'Asha'}])
        record = AttendanceRecord.objects.get()
        self.assertEqual((record.student, record.status, record.source), (self.student, 'present', 'auto'))

    def test_without_an_active_session_nobody_is_identified_or_recorded(self):
        ClassSession.objects.filter(pk=self.session.pk).update(status=ClassSession.Status.CLOSED)
        worker = self.worker(ASHA)
        payload = worker.step(FRAME, self.now)
        self.assertIsNone(payload['session'])
        self.assertEqual(payload['faces'][0]['band'], 'unknown')
        self.assertEqual(self.engine_stub.embed_calls, 0)
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_stranger_stays_unknown(self):
        worker = self.worker(STRANGER)
        worker.step(FRAME, self.now)
        payload = worker.step(FRAME, self.now + 3.1)
        self.assertEqual((payload['faces'][0]['band'], payload['faces'][0]['student']), ('unknown', None))
        self.assertEqual(AttendanceRecord.objects.count(), 0)

    def test_camera_only_serves_the_session_in_its_own_room(self):
        other_room = Room.objects.create(name='R999')
        ClassSession.objects.filter(pk=self.session.pk).update(room=other_room)
        worker = self.worker(ASHA)
        self.assertIsNone(worker.step(FRAME, self.now)['session'])
        Camera.objects.filter(pk=self.camera.pk).update(room=other_room)
        self.camera.refresh_from_db()
        self.assertEqual(self.worker(ASHA).step(FRAME, self.now)['session'], self.session.id)

    def test_second_face_cannot_take_an_identity_already_held(self):
        worker = self.worker(ASHA, ASHA)
        self.engine_stub.present = [0]
        worker.step(FRAME, self.now)
        self.engine_stub.present = [0, 1]  # a second face appears and also matches Asha
        payload = worker.step(FRAME, self.now + 0.5)
        bands = sorted(face['band'] for face in payload['faces'])
        self.assertEqual(bands, ['confirmed', 'review'])

    def test_identities_reset_when_the_session_changes(self):
        worker = self.worker(ASHA)
        worker.step(FRAME, self.now)
        ClassSession.objects.filter(pk=self.session.pk).update(status=ClassSession.Status.CLOSED)
        payload = worker.step(FRAME, self.now + 2.5)  # past the session re-check, inside the recognition interval
        self.assertIsNone(payload['session'])
        self.assertEqual(payload['faces'][0]['band'], 'unknown')

    def test_status_changes_are_logged_once(self):
        worker = self.worker(ASHA)
        worker._set_status(Camera.Status.ONLINE)
        worker._set_status(Camera.Status.ONLINE)
        worker._set_status(Camera.Status.ERROR, 'The camera stopped sending frames.')
        self.assertEqual(list(CameraStatusLog.objects.order_by('at').values_list('status', flat=True)), ['online', 'error'])
        self.camera.refresh_from_db()
        self.assertEqual(self.camera.live_status, 'error')
        self.assertIn('stopped', self.camera.last_error)

    def test_camera_with_a_stale_heartbeat_is_reported_offline(self):
        Camera.objects.filter(pk=self.camera.pk).update(status='online', last_heartbeat=timezone.now() - timedelta(minutes=2))
        data = self.client_for(self.admin).get(f'/api/v1/cameras/{self.camera.id}/').data
        self.assertEqual(data['status'], 'offline')


@override_settings(WORKER_TOKEN=TOKEN)
class WorkerEndpointTests(FaceBase):
    def setUp(self):
        super().setUp()
        live.clear_frames()
        self.camera = Camera.objects.get(name='Laptop webcam')
        self.jpeg = image_upload().read()

    def tearDown(self):
        live.clear_frames()

    def post_frame(self, token):
        headers = {'HTTP_X_WORKER_TOKEN': token} if token is not None else {}
        return self.client.post(
            f'/api/v1/internal/cameras/{self.camera.id}/frame/', data=self.jpeg, content_type='image/jpeg', **headers,
        )

    def test_frame_endpoint_requires_the_worker_token(self):
        self.assertEqual(self.post_frame(None).status_code, 403)
        self.assertEqual(self.post_frame('wrong').status_code, 403)
        self.assertIsNone(live.latest_frame(self.camera.id))
        self.assertEqual(self.post_frame(TOKEN).status_code, 204)
        self.assertEqual(live.latest_frame(self.camera.id), self.jpeg)

    @override_settings(WORKER_TOKEN='')
    def test_unset_token_rejects_everything(self):
        self.assertEqual(self.post_frame('').status_code, 403)

    def test_state_endpoint_broadcasts_and_requires_the_token(self):
        url = f'/api/v1/internal/cameras/{self.camera.id}/state/'
        payload = {'camera': 999, 'session': self.session.id, 'faces': []}
        with mock.patch('apps.monitoring.views.live.broadcast') as broadcast:
            self.assertEqual(self.client.post(url, payload, content_type='application/json').status_code, 403)
            broadcast.assert_not_called()
            response = self.client.post(url, payload, content_type='application/json', HTTP_X_WORKER_TOKEN=TOKEN)
            self.assertEqual(response.status_code, 204)
            sent = broadcast.call_args[0][0]
            self.assertEqual(sent['camera'], self.camera.id)  # taken from the URL, not the body
            self.assertEqual(sent['session'], self.session.id)

    def test_snapshot_is_staff_only_and_expires(self):
        url = f'/api/v1/cameras/{self.camera.id}/snapshot/'
        self.assertEqual(self.client_for(self.admin).get(url).status_code, 404)
        live.store_frame(self.camera.id, self.jpeg)
        response = self.client_for(self.teacher_user).get(url)
        self.assertEqual((response.status_code, response['Content-Type'], response.content), (200, 'image/jpeg', self.jpeg))
        self.assertEqual(self.client_for(self.viewer).get(url).status_code, 403)
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertIsNone(live.latest_frame(self.camera.id, max_age=-1))

    def test_enrolment_can_use_the_worker_camera_frame(self):
        from apps.test_face_attendance import face

        url = f'/api/v1/students/{self.student.id}/face-enrollments/'
        client = self.client_for(self.admin)
        with self.engine(face(ASHA)):
            self.assertEqual(client.post(url, {'camera': self.camera.id}, format='json').status_code, 400)
            live.store_frame(self.camera.id, self.jpeg)
            self.assertEqual(client.post(url, {'camera': self.camera.id}, format='json').status_code, 201)
        self.assertEqual(FaceEnrollment.objects.filter(student=self.student).count(), 1)

    def test_camera_test_reports_a_running_worker_and_is_admin_only(self):
        url = f'/api/v1/cameras/{self.camera.id}/test/'
        self.assertEqual(self.client_for(self.teacher_user).post(url).status_code, 403)
        live.store_frame(self.camera.id, self.jpeg)
        data = self.client_for(self.admin).post(url).data
        self.assertEqual((data['ok'], data['source']), (True, 'worker'))

    def test_camera_test_reports_a_camera_that_will_not_open(self):
        with mock.patch('apps.monitoring.views.open_capture', return_value=FakeCapture(opened=False)):
            data = self.client_for(self.admin).post(f'/api/v1/cameras/{self.camera.id}/test/').data
        self.assertFalse(data['ok'])
        self.assertIn('could not be opened', data['detail'])


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class ConsumerTests(TransactionTestCase):
    def setUp(self):
        def user(name, role):
            account = User.objects.create_user(username=name, password='test-pass-123')
            Profile.objects.create(user=account, role=role)
            return account

        self.admin, self.viewer = user('admin', Role.ADMIN), user('viewer', Role.VIEWER)
        self.owner, self.other = user('owner', Role.TEACHER), user('other', Role.TEACHER)
        teacher = Teacher.objects.create(user=self.owner, employee_code='T1')
        Teacher.objects.create(user=self.other, employee_code='T2')
        group = ClassGroup.objects.create(name='CSE-A', academic_year='2026-27')
        subject = Subject.objects.create(code='MA101', name='Maths')
        self.session = ClassSession.objects.create(
            class_group=group, subject=subject, teacher=teacher, date=timezone.localdate(),
            starts_at=timezone.now(), status=ClassSession.Status.ACTIVE,
        )

    def session_socket(self, user):
        communicator = WebsocketCommunicator(SessionConsumer.as_asgi(), f'/ws/sessions/{self.session.id}/')
        communicator.scope['user'] = user
        communicator.scope['url_route'] = {'kwargs': {'session_id': self.session.id}}
        return communicator

    async def test_session_socket_refuses_anonymous_viewer_and_other_teacher(self):
        from django.contrib.auth.models import AnonymousUser

        for user, code in ((AnonymousUser(), 4401), (self.viewer, 4403), (self.other, 4403)):
            connected, close_code = await self.session_socket(user).connect()
            self.assertFalse(connected)
            self.assertEqual(close_code, code)

    async def test_owner_receives_updates_for_their_session_only(self):
        communicator = self.session_socket(self.owner)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        layer = get_channel_layer()
        await layer.group_send(live.session_group(self.session.id + 1), {'type': 'live.update', 'payload': {'faces': ['other']}})
        await layer.group_send(live.session_group(self.session.id), {'type': 'live.update', 'payload': {'faces': ['mine']}})
        self.assertEqual(await communicator.receive_json_from(), {'faces': ['mine']})
        self.assertTrue(await communicator.receive_nothing())
        await communicator.disconnect()


class NotificationTests(FaceBase):
    def setUp(self):
        super().setUp()
        from django.core import mail

        self.mail = mail
        self.camera = Camera.objects.get(name='Laptop webcam')
        User.objects.filter(pk=self.admin.pk).update(email='admin@example.com')
        User.objects.filter(pk=self.teacher_user.pk).update(email='teacher@example.com')
        User.objects.filter(pk=self.viewer.pk).update(email='viewer@example.com')
        self.worker = CameraWorker(self.camera, FakeEngine([ASHA]), RecordingPublisher(), grabber=mock.Mock())

    def test_error_and_recovery_are_emailed_to_staff_only(self):
        self.worker._set_status(Camera.Status.ONLINE)
        self.assertEqual(len(self.mail.outbox), 0)  # starting up is not news

        self.worker._set_status(Camera.Status.ERROR, 'The camera stopped sending frames.')
        self.assertEqual(len(self.mail.outbox), 1)
        problem = self.mail.outbox[0]
        self.assertEqual(problem.subject, 'Camera problem: Laptop webcam')
        self.assertIn('stopped sending frames', problem.body)
        self.assertEqual(sorted(problem.to), ['admin@example.com', 'teacher@example.com'])

        self.worker._set_status(Camera.Status.ONLINE)
        self.assertEqual(self.mail.outbox[1].subject, 'Camera working again: Laptop webcam')

    def test_a_flapping_camera_does_not_send_a_stream_of_emails(self):
        for _ in range(3):
            self.worker._set_status(Camera.Status.ERROR, 'x')
            self.worker._set_status(Camera.Status.ONLINE)
        problems = [message for message in self.mail.outbox if message.subject.startswith('Camera problem')]
        self.assertEqual(len(problems), 1)

    def test_people_who_switched_alerts_off_are_not_emailed(self):
        from apps.accounts.models import NotificationPreference

        NotificationPreference.objects.create(user=self.admin, camera_offline=False)
        self.worker._set_status(Camera.Status.ERROR, 'x')
        self.assertEqual(self.mail.outbox[0].to, ['teacher@example.com'])

    def test_a_failing_mail_server_does_not_stop_the_worker(self):
        with mock.patch('apps.monitoring.notifications.send_mail', side_effect=OSError('connection refused')):
            self.worker._set_status(Camera.Status.ERROR, 'x')
        self.assertEqual(Camera.objects.get(pk=self.camera.pk).status, 'error')
