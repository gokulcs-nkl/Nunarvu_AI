import gzip
import io
import json
import tempfile
from pathlib import Path
from unittest import mock

import cv2
import numpy as np
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.test_face_attendance import ASHA, BALA, STRANGER, face, unit
from apps.tests import BaseData
from vision.face.evaluation import pair_scores, rates_at, sweep


class EvaluationMathTests(SimpleTestCase):
    def setUp(self):
        # Two photos each of two people; the second photo of each is slightly different.
        self.embeddings = [ASHA, unit(1, 0.2, 0), BALA, unit(0.3, 1, 0)]
        self.labels = ['asha', 'asha', 'bala', 'bala']

    def test_pairs_are_split_into_same_and_different_people(self):
        genuine, impostor = pair_scores(self.embeddings, self.labels)
        self.assertEqual((genuine.size, impostor.size), (2, 4))
        self.assertTrue((genuine > 0.9).all())
        self.assertTrue((impostor < 0.5).all())

    def test_rates_move_the_right_way_with_the_threshold(self):
        genuine, impostor = pair_scores(self.embeddings, self.labels)
        strict, loose = rates_at(genuine, impostor, 0.99), rates_at(genuine, impostor, 0.1)
        self.assertEqual((strict.false_non_match_rate, strict.false_match_rate), (1.0, 0.0))
        self.assertEqual(loose.false_non_match_rate, 0.0)
        self.assertGreater(loose.false_match_rate, 0.0)
        middle = rates_at(genuine, impostor, 0.6)
        self.assertEqual((middle.false_non_match_rate, middle.false_match_rate), (0.0, 0.0))

    def test_sweep_covers_a_range_of_thresholds(self):
        results = sweep(*pair_scores(self.embeddings, self.labels))
        self.assertEqual((results[0].threshold, results[-1].threshold), (0.2, 0.7))


class FakeEngine:
    model_name = 'fake-model'
    providers = ['CPUExecutionProvider']

    def analyze(self, image):
        # The test images encode who they show in their top-left pixel.
        code = int(image[0, 0, 0])
        if code == 0:
            return []
        if code == 9:
            return [face(ASHA), face(BALA)]
        base = {1: ASHA, 2: BALA, 3: STRANGER}[code]
        return [face(base)]


class EvaluateCommandTests(SimpleTestCase):
    def write(self, folder: Path, person: str, name: str, code: int):
        (folder / person).mkdir(exist_ok=True)
        cv2.imwrite(str(folder / person / name), np.full((8, 8, 3), code, dtype=np.uint8))

    def run_command(self, folder, *extra):
        out = io.StringIO()
        with mock.patch('apps.attendance.management.commands.evaluate_faces.get_engine', return_value=FakeEngine()):
            call_command('evaluate_faces', str(folder), *extra, stdout=out)
        return out.getvalue()

    def test_reports_counts_rates_and_writes_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for person, code in (('asha', 1), ('bala', 2), ('charu', 3)):
                self.write(folder, person, 'one.png', code)
                self.write(folder, person, 'two.png', code)
            self.write(folder, 'asha', 'empty.png', 0)   # no face
            self.write(folder, 'asha', 'group.png', 9)   # two faces
            table = folder / 'result.csv'
            output = self.run_command(folder, '--csv', str(table))
            self.assertIn("People: 3   usable photos: 6   skipped: {'unreadable': 0, 'no face': 1, 'several faces': 1}", output)
            self.assertIn('Same-person pairs: 3   different-person pairs: 12', output)
            self.assertIn('Current confirm threshold 0.50: misses 0.0%, false matches 0.00%', output)
            rows = table.read_text(encoding='utf-8').strip().splitlines()
            self.assertEqual(len(rows), 12)
            self.assertTrue(rows[0].startswith('threshold,false_non_match_rate,false_match_rate'))

    def test_refuses_to_report_on_too_little_data(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            self.write(folder, 'asha', 'one.png', 1)
            with self.assertRaises(CommandError):
                self.run_command(folder)


class BackupTests(BaseData):
    def test_backup_contains_the_data_and_can_be_read_back(self):
        with tempfile.TemporaryDirectory() as temp:
            out = io.StringIO()
            call_command('backup_data', '--out', temp, stdout=out)
            files = list(Path(temp).glob('nunarvu-*.json.gz'))
            self.assertEqual(len(files), 1)
            with gzip.open(files[0], 'rt', encoding='utf-8') as handle:
                rows = json.load(handle)
        models = {row['model'] for row in rows}
        self.assertTrue({'auth.user', 'academics.student', 'academics.classgroup', 'monitoring.camera'} <= models)
        self.assertNotIn('sessions.session', models)
        rolls = {row['fields']['roll_number'] for row in rows if row['model'] == 'academics.student'}
        self.assertEqual(rolls, {'A001', 'B001'})
