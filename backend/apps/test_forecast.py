from datetime import date, time, timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from apps.academics.models import ClassSession, Period, Student, Subject, Term, TimetableEntry
from apps.attendance.forecast import classes_needed, forecast, remaining_classes
from apps.attendance.models import AttendanceRecord
from apps.monitoring.models import ClassroomEvent
from apps.tests import MONDAY, BaseData

# A term that starts the Monday the fixtures use and runs four weeks.
TERM_START = MONDAY
TERM_END = MONDAY + timedelta(days=27)


class ClassesNeededTests(SimpleTestCase):
    def test_how_many_more_classes_reach_the_minimum(self):
        # 6 of 10 so far (60%), 10 still to come; 75% of 20 is 15, so 9 more are needed.
        self.assertEqual(classes_needed(6, 10, 10, 75), 9)
        # Already above the line with classes left: none strictly required.
        self.assertEqual(classes_needed(8, 10, 10, 75), 7)
        self.assertEqual(classes_needed(20, 20, 0, 75), 0)
        # Cannot be reached: needs more than remain.
        self.assertGreater(classes_needed(0, 10, 5, 75), 5)


class ForecastBase(BaseData):
    def setUp(self):
        self.term = Term.objects.create(name='Term 1', start_date=TERM_START, end_date=TERM_END, minimum_attendance=75)
        Period.objects.create(number=1, start_time=time(9, 0), end_time=time(9, 50))
        # Maths for CSE-A every Monday, period 1.
        TimetableEntry.objects.create(
            class_group=self.group, subject=self.maths, teacher=self.teacher, weekday=MONDAY.weekday(), period_number=1,
        )
        self.second = Student.objects.create(roll_number='A002', full_name='Chitra')
        self.second.class_groups.add(self.group)

    def past_session(self, days_before_end, marks):
        day = TERM_END - timedelta(days=days_before_end)
        session = ClassSession.objects.create(
            class_group=self.group, subject=self.maths, teacher=self.teacher, date=day, period_number=1,
            starts_at=timezone.now() - timedelta(days=days_before_end), status='closed',
        )
        for student, status in marks.items():
            AttendanceRecord.objects.create(session=session, student=student, status=status)
        return session


class ForecastLogicTests(ForecastBase):
    def test_remaining_counts_future_mondays_only(self):
        # "Today" is the term start; four Mondays fall in a four-week term.
        counts = remaining_classes(self.term, TERM_START)
        self.assertEqual(counts[(self.group.id, self.maths.id)], 4)
        # A holiday on one of those Mondays removes one.
        from apps.academics.models import Holiday

        Holiday.objects.create(date=TERM_START + timedelta(days=7), name='Break')
        self.assertEqual(remaining_classes(self.term, TERM_START)[(self.group.id, self.maths.id)], 3)

    def test_finished_future_session_is_not_counted_as_remaining(self):
        ClassSession.objects.create(
            class_group=self.group, subject=self.maths, date=TERM_START + timedelta(days=7), period_number=1,
            starts_at=timezone.now(), status='cancelled',
        )
        self.assertEqual(remaining_classes(self.term, TERM_START)[(self.group.id, self.maths.id)], 3)

    def test_student_below_the_line_is_flagged_with_the_catch_up_number(self):
        # Asha missed the first two of three held classes; one Monday remains.
        self.past_session(21, {self.student: 'absent', self.second: 'present'})
        self.past_session(14, {self.student: 'absent', self.second: 'present'})
        self.past_session(7, {self.student: 'present', self.second: 'present'})
        as_of = TERM_END - timedelta(days=7)  # after the three sessions, one Monday (term-end week) left
        rows = {row.roll_number: row for row in forecast(self.term, as_of)}
        asha = rows['A001']
        self.assertEqual((asha.attended, asha.held, asha.remaining), (1, 3, 1))
        self.assertEqual(asha.percent, 33.3)
        self.assertEqual(asha.status, 'cannot_reach')  # 1 of 4 even if the last is attended
        self.assertEqual(rows['A002'].status, 'safe')

    def test_pending_records_are_not_counted(self):
        self.past_session(7, {self.student: 'pending'})
        row = next(r for r in forecast(self.term, TERM_END - timedelta(days=7)) if r.roll_number == 'A001')
        self.assertEqual((row.attended, row.held), (0, 0))

    def test_no_term_today_returns_nothing_via_current(self):
        self.assertIsNone(Term.current(TERM_END + timedelta(days=365)))


class ForecastApiTests(ForecastBase):
    def setUp(self):
        super().setUp()
        self.past_session(21, {self.student: 'absent', self.second: 'present'})
        self.past_session(14, {self.student: 'absent', self.second: 'present'})

    def test_forecast_endpoint_scopes_and_filters(self):
        url = f'/api/v1/reports/forecast/?as_of={(TERM_END - timedelta(days=10)).isoformat()}'
        data = self.client_for(self.admin).get(url).data
        self.assertEqual(data['term']['name'], 'Term 1')
        self.assertGreaterEqual(data['counts']['total'], 2)
        risky = self.client_for(self.admin).get(url + '&status=at_risk').data['rows']
        self.assertTrue(all(row['status'] == 'at_risk' for row in risky))
        # The other teacher teaches none of this, so sees nothing.
        self.assertEqual(self.client_for(self.other_teacher_user).get(url).data['counts']['total'], 0)
        self.assertEqual(self.client_for(self.viewer).get(url).status_code, 403)

    def test_term_is_admin_only_to_change(self):
        url = '/api/v1/terms/'
        self.assertEqual(self.client_for(self.teacher_user).get(url).status_code, 200)
        self.assertEqual(self.client_for(self.teacher_user).post(url, {
            'name': 'X', 'start_date': '2030-01-01', 'end_date': '2030-06-01', 'minimum_attendance': 75,
        }, format='json').status_code, 403)
        bad = self.client_for(self.admin).post(url, {
            'name': 'Bad', 'start_date': '2030-06-01', 'end_date': '2030-01-01', 'minimum_attendance': 75,
        }, format='json')
        self.assertEqual(bad.status_code, 400)


class HeatmapApiTests(BaseData):
    def setUp(self):
        self.session = ClassSession.objects.create(
            class_group=self.group, subject=self.maths, teacher=self.teacher, date=MONDAY,
            starts_at=timezone.now(), status='closed',
        )
        now = timezone.now()
        spots = [(0.1, 0.1), (0.15, 0.12), (0.9, 0.9), (0.5, 0.5)]
        for index, (x, y) in enumerate(spots):
            ClassroomEvent.objects.create(
                session=self.session, kind='hand_raise', subject=str(index), started_at=now, confidence=0.9,
                summary='Hand raised', position_x=x, position_y=y,
            )
        # One event with no position must be ignored.
        ClassroomEvent.objects.create(
            session=self.session, kind='hand_raise', subject='np', started_at=now, confidence=0.9, summary='x',
        )

    def test_heatmap_bins_positions_and_names_no_one(self):
        data = self.client_for(self.admin).get('/api/v1/reports/participation/?grid=5').data
        self.assertEqual((data['grid'], data['total']), (5, 4))
        self.assertEqual(data['cells'][0][0], 2)       # two hand raises in the top-left cell
        self.assertEqual(data['cells'][4][4], 1)       # one in the bottom-right
        self.assertEqual(data['peak'], 2)
        body = str(data)
        self.assertNotIn('Asha', body)                 # the room, not individuals

    def test_heatmap_is_scoped_to_a_teachers_sessions(self):
        self.assertEqual(self.client_for(self.other_teacher_user).get('/api/v1/reports/participation/').data['total'], 0)
        self.assertEqual(self.client_for(self.viewer).get('/api/v1/reports/participation/').status_code, 403)

    def test_invalid_kind_is_rejected(self):
        self.assertEqual(self.client_for(self.admin).get('/api/v1/reports/participation/?kind=nonsense').status_code, 400)
