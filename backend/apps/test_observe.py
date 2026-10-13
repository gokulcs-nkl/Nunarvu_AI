import time
from unittest import mock

import numpy as np
from django.test import SimpleTestCase

from apps.accounts.models import AuditLog
from apps.monitoring.models import Camera, ClassroomEvent, ObservationSettings
from apps.monitoring.worker import CameraWorker
from apps.test_face_attendance import ASHA, FaceBase
from apps.test_live import FRAME, FakeEngine, RecordingPublisher
from vision.behavior import analyzer, rules
from vision.behavior.analyzer import BehaviorAnalyzer, Person, Thresholds

BOX = (50, 80, 250, 400)


def pose(nose_y=100.0, left_wrist_y=260.0, right_wrist_y=260.0, shift=0.0, wrist_confidence=0.9):
    """A seated upper body: shoulders 100 px apart at y=180, nose above them, wrists at the desk."""
    keypoints = np.zeros((17, 2), dtype=np.float32)
    confidence = np.full(17, 0.9, dtype=np.float32)
    keypoints[rules.NOSE] = (150, nose_y)
    keypoints[rules.LEFT_SHOULDER] = (200, 180)
    keypoints[rules.RIGHT_SHOULDER] = (100, 180)
    keypoints[rules.LEFT_WRIST] = (210, left_wrist_y)
    keypoints[rules.RIGHT_WRIST] = (90, right_wrist_y)
    keypoints[11] = (190, 330)
    keypoints[12] = (110, 330)
    keypoints[:, 0] += shift
    confidence[[rules.LEFT_WRIST, rules.RIGHT_WRIST]] = wrist_confidence
    return keypoints, confidence


def person(track=1, student=None, box=BOX, **kwargs):
    keypoints, confidence = pose(**kwargs)
    return Person(track, box, keypoints, confidence, student)


class RuleTests(SimpleTestCase):
    def test_hand_raise_measures_the_higher_wrist(self):
        resting = rules.hand_raise(*pose())
        self.assertFalse(resting.met)
        raised = rules.hand_raise(*pose(left_wrist_y=90))
        self.assertTrue(raised.met)
        self.assertAlmostEqual(raised.value, 0.9, places=2)  # 90 px above a 100 px shoulder width
        self.assertEqual(raised.as_dict()['threshold'], rules.HAND_RAISE_HEIGHT)

    def test_hand_raise_ignores_a_wrist_the_model_is_unsure_about(self):
        self.assertIsNone(rules.hand_raise(*pose(left_wrist_y=90, wrist_confidence=0.2)))

    def test_head_down_when_the_nose_drops_to_shoulder_level(self):
        self.assertFalse(rules.head_down(*pose(nose_y=100)).met)
        self.assertTrue(rules.head_down(*pose(nose_y=175)).met)

    def test_no_measurement_without_visible_shoulders(self):
        keypoints, confidence = pose(nose_y=175)
        confidence[rules.LEFT_SHOULDER] = 0.1
        self.assertIsNone(rules.head_down(keypoints, confidence))
        self.assertIsNone(rules.hand_raise(keypoints, confidence))

    def test_movement_speed_is_scaled_by_body_size_and_time(self):
        before, confidence = pose()
        after, _ = pose(shift=50)
        self.assertAlmostEqual(rules.movement_speed(before, after, confidence, 0.5), 1.0, places=2)


class AnalyzerTests(SimpleTestCase):
    def setUp(self):
        self.analyzer = BehaviorAnalyzer(Thresholds(hand_raise_seconds=1.0, head_down_seconds=10.0, phone_seconds=3.0))

    def feed(self, times, **kwargs):
        updates = []
        for now in times:
            updates += self.analyzer.update([person(**kwargs)], [], now)
        return updates

    def test_a_single_frame_does_not_create_an_event(self):
        self.assertEqual(self.analyzer.update([person(left_wrist_y=90)], [], 0.0), [])
        self.assertEqual(self.analyzer.update([person()], [], 0.5), [])

    def test_hand_held_up_becomes_one_event_that_ends_when_lowered(self):
        updates = self.feed([0.0, 0.5, 1.0, 1.5, 2.0], left_wrist_y=90, student=7)
        self.assertEqual([(u.action, u.kind, u.student_id) for u in updates], [('start', analyzer.HAND_RAISE, 7)])
        self.assertEqual(updates[0].at, 0.0)  # the event starts when the hand went up, not when it was confirmed
        self.assertEqual(updates[0].signals[0]['signal'], 'wrist_above_shoulder')

        self.assertEqual(self.feed([2.5, 3.0]), [])          # still inside the grace period
        ended = self.feed([4.5])
        self.assertEqual([(u.action, u.kind) for u in ended], [('end', analyzer.HAND_RAISE)])

    def test_brief_lapse_does_not_split_an_event(self):
        self.feed([0.0, 0.5, 1.0], left_wrist_y=90)
        self.assertEqual(self.feed([1.5]), [])               # one sample with the hand not detected
        self.assertEqual(self.feed([2.0, 2.5], left_wrist_y=90), [])

    def test_cooldown_stops_the_same_event_repeating_at_once(self):
        self.feed([0.0, 1.0], left_wrist_y=90)
        self.feed([3.0])
        self.assertEqual(self.feed([4.0, 5.5], left_wrist_y=90), [])
        again = self.feed([30.0, 31.5], left_wrist_y=90)
        self.assertEqual([u.action for u in again], ['start'])

    def test_head_down_needs_its_full_duration(self):
        self.assertEqual(self.feed(np.arange(0, 9.5, 0.5), nose_y=175), [])
        updates = self.feed([10.0], nose_y=175)
        self.assertEqual([(u.action, u.kind) for u in updates], [('start', analyzer.HEAD_DOWN)])

    def test_phone_inside_a_persons_box_is_attributed_to_them(self):
        phone_here, phone_elsewhere = (100, 300, 140, 360, 0.6), (900, 300, 940, 360, 0.9)
        updates = []
        for now in (0.0, 1.5, 3.0):
            updates += self.analyzer.update([person(student=7)], [phone_here, phone_elsewhere], now)
        self.assertEqual([(u.kind, u.student_id) for u in updates], [(analyzer.PHONE, 7)])
        self.assertAlmostEqual(updates[0].confidence, 0.6, places=2)

        other = BehaviorAnalyzer(Thresholds(phone_seconds=3.0))
        for now in (0.0, 1.5, 3.0):
            self.assertEqual(other.update([person()], [phone_elsewhere], now), [])

    def test_disabled_kinds_never_fire(self):
        quiet = BehaviorAnalyzer(Thresholds(hand_raise_seconds=1.0, enabled=frozenset({analyzer.PHONE})))
        for now in (0.0, 1.0, 2.0):
            self.assertEqual(quiet.update([person(left_wrist_y=90)], [], now), [])

    def test_unusual_activity_needs_two_fast_people_close_together(self):
        thresholds = Thresholds(unusual_activity_seconds=1.0)

        def run(second_box):
            room = BehaviorAnalyzer(thresholds)
            updates = []
            for step in range(6):
                now, shift = step * 0.5, (step % 2) * 160.0   # 160 px per half second = 3.2 shoulder-widths/s
                updates += room.update([
                    person(track=1, shift=shift),
                    person(track=2, shift=shift, box=second_box),
                ], [], now)
            return [(u.kind, u.subject) for u in updates if u.action == 'start']

        self.assertEqual(run((260, 80, 460, 400)), [(analyzer.UNUSUAL_ACTIVITY, analyzer.ROOM)])
        self.assertEqual(run((1500, 80, 1700, 400)), [])  # far apart

    def test_person_leaving_the_view_ends_their_event(self):
        self.feed([0.0, 1.0], left_wrist_y=90)
        ended = self.analyzer.update([], [], 3.0)
        self.assertEqual([(u.action, u.kind) for u in ended], [('end', analyzer.HAND_RAISE)])


class FakePose:
    def __init__(self):
        self.kwargs = {}
        self.calls = 0

    def detect(self, frame):
        self.calls += 1
        keypoints, confidence = pose(**self.kwargs)
        return [((40, 60, 260, 420), keypoints, confidence)]


class WorkerObservationTests(FaceBase):
    def setUp(self):
        super().setUp()
        self.camera = Camera.objects.get(name='Laptop webcam')
        self.enroll(self.student, ASHA)
        ObservationSettings.objects.update_or_create(pk=1, defaults={'hand_raise_seconds': 1.0})
        self.pose = FakePose()
        self.worker = CameraWorker(
            self.camera, FakeEngine([ASHA]), RecordingPublisher(), grabber=mock.Mock(), pose=self.pose, phones=None,
        )
        self.now = time.time()

    def test_hand_raise_is_stored_once_with_the_student_and_wording(self):
        self.pose.kwargs = {'left_wrist_y': 90}
        payloads = [self.worker.step(FRAME, self.now + offset) for offset in (0.0, 0.6, 1.2, 1.8)]
        events = [event for payload in payloads for event in payload['events']]
        self.assertEqual(len(events), 1)
        stored = ClassroomEvent.objects.get()
        self.assertEqual((stored.kind, stored.student, stored.review_status), ('hand_raise', self.student, 'unreviewed'))
        self.assertEqual(stored.summary, 'Hand raised above shoulder height.')
        self.assertEqual(stored.signals[0]['signal'], 'wrist_above_shoulder')
        self.assertIsNone(stored.ended_at)
        self.assertEqual(payloads[-1]['people'], 1)

        self.pose.kwargs = {}
        self.worker.step(FRAME, self.now + 4.0)
        stored.refresh_from_db()
        self.assertIsNotNone(stored.ended_at)

    def test_observations_run_below_the_frame_rate(self):
        for offset in (0.0, 0.1, 0.2, 0.3):
            self.worker.step(FRAME, self.now + offset)
        self.assertEqual(self.pose.calls, 1)

    def test_switched_off_observations_are_not_run(self):
        ObservationSettings.objects.filter(pk=1).update(
            hand_raise_enabled=False, head_down_enabled=False, phone_enabled=False, unusual_activity_enabled=False,
        )
        self.pose.kwargs = {'left_wrist_y': 90}
        for offset in (0.0, 0.6, 1.2, 1.8):
            self.worker.step(FRAME, self.now + offset)
        self.assertEqual((self.pose.calls, ClassroomEvent.objects.count()), (0, 0))

    def test_head_down_wording_asks_for_verification(self):
        ObservationSettings.objects.filter(pk=1).update(head_down_seconds=2.0)
        self.pose.kwargs = {'nose_y': 175}
        for offset in (0.0, 0.6, 1.2, 1.8, 2.4):
            self.worker.step(FRAME, self.now + offset)
        summary = ClassroomEvent.objects.get(kind='head_down').summary
        self.assertIn('Possible sleeping-like posture; teacher verification required.', summary)

    def test_open_events_close_when_the_session_ends(self):
        self.pose.kwargs = {'left_wrist_y': 90}
        for offset in (0.0, 0.6, 1.2):
            self.worker.step(FRAME, self.now + offset)
        self.session.status = 'closed'
        self.session.save()
        self.worker.step(FRAME, self.now + 3.5)
        self.assertIsNotNone(ClassroomEvent.objects.get().ended_at)


class EventApiTests(FaceBase):
    def setUp(self):
        super().setUp()
        from django.utils import timezone

        self.event = ClassroomEvent.objects.create(
            session=self.session, kind='phone', subject='3', student=self.student, started_at=timezone.now(),
            confidence=0.6, summary='Phone-like object visible near this person for over 5 s.', signals=[],
        )

    def test_listing_is_scoped_and_filtered(self):
        url = f'/api/v1/events/?session={self.session.id}'
        self.assertEqual(self.client_for(self.teacher_user).get(url).data['count'], 1)
        self.assertEqual(self.client_for(self.other_teacher_user).get(url).data['count'], 0)
        self.assertEqual(self.client_for(self.viewer).get(url).status_code, 403)
        self.assertEqual(self.client_for(self.admin).get(url + '&kind=hand_raise').data['count'], 0)

    def test_review_records_who_decided_and_is_audited(self):
        client = self.client_for(self.teacher_user)
        response = client.post(f'/api/v1/events/{self.event.id}/review/', {'status': 'dismissed'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.data['review_status'], response.data['reviewed_by_username']), ('dismissed', 'teacher'))
        self.assertEqual(AuditLog.objects.get(action='review_event').detail, {'from': 'unreviewed', 'to': 'dismissed'})
        self.assertEqual(client.post(f'/api/v1/events/{self.event.id}/review/', {'status': 'guilty'}, format='json').status_code, 400)
        other = self.client_for(self.other_teacher_user)
        self.assertEqual(other.post(f'/api/v1/events/{self.event.id}/review/', {'status': 'confirmed'}, format='json').status_code, 404)

    def test_events_cannot_be_edited_or_deleted_directly(self):
        client = self.client_for(self.admin)
        self.assertEqual(client.patch(f'/api/v1/events/{self.event.id}/', {'summary': 'x'}, format='json').status_code, 405)
        self.assertEqual(client.delete(f'/api/v1/events/{self.event.id}/').status_code, 405)

    def test_settings_are_admin_only_to_change_and_validated(self):
        url = '/api/v1/settings/observations/'
        self.assertTrue(self.client_for(self.teacher_user).get(url).data['phone_enabled'])
        self.assertEqual(self.client_for(self.teacher_user).put(url, {'phone_enabled': False}, format='json').status_code, 403)
        admin = self.client_for(self.admin)
        self.assertEqual(admin.put(url, {'head_down_seconds': 0}, format='json').status_code, 400)
        saved = admin.put(url, {'phone_enabled': False, 'head_down_seconds': 90}, format='json')
        self.assertEqual((saved.status_code, saved.data['phone_enabled'], saved.data['head_down_seconds']), (200, False, 90.0))
