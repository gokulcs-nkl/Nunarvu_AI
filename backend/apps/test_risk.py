from datetime import time, timedelta

from django.core import mail
from django.utils import timezone

from apps.academics.models import ClassSession, Period, PrivacySettings, Student, Term, TimetableEntry
from apps.accounts.models import AuditLog
from apps.attendance.models import AttendanceRecord, GuardianNotice
from apps.attendance.notices import COOLING_OFF, compose, pending_notices, send_notices
from apps.attendance.risk import HIGH, LOW, MEDIUM, assess, band_for, consecutive_absences
from apps.tests import MONDAY, BaseData

TERM_START = MONDAY - timedelta(days=60)
TERM_END = MONDAY + timedelta(days=30)
TODAY = MONDAY


class RiskBase(BaseData):
    def setUp(self):
        self.term = Term.objects.create(name='Term 1', start_date=TERM_START, end_date=TERM_END, minimum_attendance=75)
        Period.objects.create(number=1, start_time=time(9, 0), end_time=time(9, 50))
        TimetableEntry.objects.create(
            class_group=self.group, subject=self.maths, teacher=self.teacher, weekday=MONDAY.weekday(), period_number=1,
        )

    def sessions_for(self, student, statuses, start_offset=50):
        """Create one closed session per status, oldest first, ending a few days before TODAY."""
        for index, status in enumerate(statuses):
            day = TERM_START + timedelta(days=start_offset - len(statuses) + index)
            session = ClassSession.objects.create(
                class_group=self.group, subject=self.maths, teacher=self.teacher, date=day,
                starts_at=timezone.now() - timedelta(days=100 - index), status='closed',
            )
            AttendanceRecord.objects.create(session=session, student=student, status=status)


class ScoringTests(RiskBase):
    def test_bands_follow_the_score(self):
        self.assertEqual((band_for(0), band_for(30), band_for(80)), (LOW, MEDIUM, HIGH))

    def test_a_student_attending_everything_is_not_flagged(self):
        self.sessions_for(self.student, ['present'] * 20)
        rows = {row.roll_number: row for row in assess(self.term, TODAY)}
        self.assertNotIn(self.student.roll_number, rows)  # no signals, so not reported

    def test_low_attendance_and_a_run_of_absences_raise_the_score_with_reasons(self):
        # 8 of 24 attended (33%), and the most recent four missed.
        self.sessions_for(self.student, ['present'] * 8 + ['absent'] * 12 + ['absent'] * 4)
        row = next(row for row in assess(self.term, TODAY) if row.roll_number == self.student.roll_number)
        names = {signal['name'] for signal in row.signals}
        self.assertIn('below_minimum', names)
        self.assertIn('well_below_minimum', names)
        self.assertIn('consecutive_absences', names)
        self.assertEqual(row.band, HIGH)
        self.assertEqual(row.consecutive_absences, 16)
        # Every point is explained by a signal.
        self.assertEqual(row.score, min(sum(signal['points'] for signal in row.signals), 100))

    def test_a_falling_trend_is_noticed_even_above_the_minimum(self):
        # Good early on, poor recently: 10 early present, then 10 recent with only 3 present.
        self.sessions_for(self.student, ['present'] * 10 + ['present'] * 3 + ['absent'] * 7)
        row = next(row for row in assess(self.term, TODAY) if row.roll_number == self.student.roll_number)
        self.assertIn('falling', {signal['name'] for signal in row.signals})

    def test_consecutive_absences_stop_at_the_first_attendance(self):
        self.sessions_for(self.student, ['absent', 'absent', 'present', 'absent', 'absent'])
        self.assertEqual(consecutive_absences(self.student.id, self.term, TODAY), 2)

    def test_scores_are_capped_and_sorted_highest_first(self):
        other = Student.objects.create(roll_number='A009', full_name='Deepa')
        other.class_groups.add(self.group)
        self.sessions_for(self.student, ['absent'] * 24)
        self.sessions_for(other, ['present'] * 12 + ['absent'] * 8)
        rows = assess(self.term, TODAY)
        self.assertLessEqual(rows[0].score, 100)
        self.assertGreaterEqual(rows[0].score, rows[-1].score)

    def test_teacher_sees_only_their_own_classes(self):
        self.sessions_for(self.student, ['absent'] * 20)
        self.assertTrue(assess(self.term, TODAY, teacher_user=self.teacher_user))
        self.assertEqual(assess(self.term, TODAY, teacher_user=self.other_teacher_user), [])


class GuardianNoticeTests(RiskBase):
    def setUp(self):
        super().setUp()
        PrivacySettings.objects.update_or_create(pk=1, defaults={'guardian_notices_enabled': True})
        self.student.guardian_contact = 'guardian@example.com'
        self.student.guardian_name = 'R. Kumar'
        self.student.save()
        self.sessions_for(self.student, ['present'] * 4 + ['absent'] * 20)

    def test_a_high_risk_student_with_a_guardian_email_is_pending(self):
        pending = pending_notices(self.term, today=TODAY)
        self.assertEqual([row.roll_number for row in pending], [self.student.roll_number])

    def test_the_message_states_the_figures_and_does_not_accuse(self):
        row = pending_notices(self.term, today=TODAY)[0]
        subject, body = compose(row, self.term)
        self.assertIn(self.student.full_name, subject)
        self.assertIn('minimum required is 75%', body)
        self.assertIn('please contact the class teacher', body)
        for word in ('lazy', 'failure', 'will drop out', 'punish'):
            self.assertNotIn(word, body.lower())

    def test_sending_records_the_notice_and_does_not_repeat_it(self):
        result = send_notices(self.term, today=TODAY)
        self.assertEqual((result['sent'], result['failed']), (1, 0))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['guardian@example.com'])
        notice = GuardianNotice.objects.get()
        self.assertEqual((notice.student, notice.kind), (self.student, 'high_risk'))

        again = send_notices(self.term, today=TODAY)
        self.assertEqual(again['sent'], 0)  # inside the cooling-off period

        GuardianNotice.objects.update(sent_at=timezone.now() - COOLING_OFF - timedelta(days=1))
        self.assertEqual(send_notices(self.term, today=TODAY)['sent'], 1)

    def test_a_dry_run_sends_nothing(self):
        result = send_notices(self.term, today=TODAY, dry_run=True)
        self.assertEqual((result['sent'], result['skipped']), (0, 1))
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(GuardianNotice.objects.count(), 0)

    def test_nothing_is_sent_when_the_feature_is_off_or_there_is_no_contact(self):
        PrivacySettings.objects.update(guardian_notices_enabled=False)
        self.assertTrue(send_notices(self.term, today=TODAY)['disabled'])
        self.assertEqual(len(mail.outbox), 0)

        PrivacySettings.objects.update(guardian_notices_enabled=True)
        Student.objects.filter(pk=self.student.pk).update(guardian_contact='not-an-email')
        self.assertEqual(send_notices(self.term, today=TODAY)['sent'], 0)

    def test_a_failing_mail_server_is_counted_not_raised(self):
        from unittest import mock

        with mock.patch('apps.attendance.notices.send_mail', side_effect=OSError('refused')):
            result = send_notices(self.term, today=TODAY)
        self.assertEqual((result['sent'], result['failed']), (0, 1))
        self.assertEqual(GuardianNotice.objects.count(), 0)  # nothing recorded as sent


class RiskApiTests(RiskBase):
    def setUp(self):
        super().setUp()
        self.student.guardian_contact = 'guardian@example.com'
        self.student.save()
        self.sessions_for(self.student, ['present'] * 4 + ['absent'] * 20)

    def test_risk_endpoint_lists_reasons_and_is_scoped(self):
        url = f'/api/v1/reports/risk/?as_of={TODAY.isoformat()}'
        data = self.client_for(self.admin).get(url).data
        self.assertEqual(data['term']['name'], 'Term 1')
        self.assertGreaterEqual(data['counts']['high'], 1)
        row = data['rows'][0]
        self.assertTrue(row['signals'])
        self.assertIn('detail', row['signals'][0])
        self.assertEqual(self.client_for(self.other_teacher_user).get(url).data['counts']['total'], 0)
        self.assertEqual(self.client_for(self.viewer).get(url).status_code, 403)

    def test_band_filter(self):
        url = f'/api/v1/reports/risk/?as_of={TODAY.isoformat()}&band=low'
        self.assertTrue(all(row['band'] == 'low' for row in self.client_for(self.admin).get(url).data['rows']))

    def test_guardian_notice_endpoint_previews_and_sends(self):
        PrivacySettings.objects.update_or_create(pk=1, defaults={'guardian_notices_enabled': True})
        admin = self.client_for(self.admin)
        preview = admin.get('/api/v1/notices/guardian/').data
        self.assertTrue(preview['enabled'])
        self.assertEqual(preview['pending'][0]['roll_number'], self.student.roll_number)

        self.assertEqual(self.client_for(self.teacher_user).post('/api/v1/notices/guardian/', {}, format='json').status_code, 403)
        sent = admin.post('/api/v1/notices/guardian/', {}, format='json')
        self.assertEqual((sent.status_code, sent.data['sent']), (200, 1))
        self.assertEqual(AuditLog.objects.filter(action='send_guardian_notices').count(), 1)
        self.assertEqual(len(admin.get('/api/v1/notices/guardian/').data['sent']), 1)
