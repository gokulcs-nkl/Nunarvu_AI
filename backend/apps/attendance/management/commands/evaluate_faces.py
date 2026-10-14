import csv
from pathlib import Path

import cv2
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from vision.face.engine import ModelNotAvailable, get_engine
from vision.face.evaluation import pair_scores, rates_at, sweep

IMAGE_TYPES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


class Command(BaseCommand):
    help = (
        "Measure face recognition on your own labelled photos. Give a folder that contains one "
        "sub-folder per person, each holding several photos of that person taken with consent. "
        "Nothing is stored; the photos are only read."
    )

    def add_arguments(self, parser):
        parser.add_argument('folder', help="Folder with one sub-folder of images per person")
        parser.add_argument('--csv', help="Also write the threshold table to this CSV file")

    def handle(self, *args, **options):
        root = Path(options['folder'])
        if not root.is_dir():
            raise CommandError(f"Not a folder: {root}")
        try:
            engine = get_engine()
        except ModelNotAvailable as error:
            raise CommandError(str(error))

        embeddings, labels = [], []
        skipped = {'unreadable': 0, 'no face': 0, 'several faces': 0}
        for person in sorted(path for path in root.iterdir() if path.is_dir()):
            for image_path in sorted(path for path in person.iterdir() if path.suffix.lower() in IMAGE_TYPES):
                image = cv2.imread(str(image_path))
                if image is None:
                    skipped['unreadable'] += 1
                    continue
                faces = engine.analyze(image)
                if not faces:
                    skipped['no face'] += 1
                elif len(faces) > 1:
                    skipped['several faces'] += 1
                else:
                    embeddings.append(faces[0].embedding)
                    labels.append(person.name)

        people = sorted(set(labels))
        if len(people) < 2 or len(labels) < 4:
            raise CommandError("Need at least two people with usable photos (two or more photos each) to measure anything.")
        genuine, impostor = pair_scores(embeddings, labels)
        if genuine.size == 0:
            raise CommandError("No person has two usable photos, so there are no same-person pairs to score.")

        self.stdout.write(f"Model: {engine.model_name} on {', '.join(engine.providers)}")
        self.stdout.write(f"People: {len(people)}   usable photos: {len(labels)}   skipped: {skipped}")
        self.stdout.write(f"Same-person pairs: {genuine.size}   different-person pairs: {impostor.size}")
        self.stdout.write(
            f"Same-person scores: min {genuine.min():.2f}, mean {genuine.mean():.2f}.   "
            f"Different-person scores: mean {impostor.mean():.2f}, max {impostor.max():.2f}."
        )
        self.stdout.write("")
        self.stdout.write("Threshold   Misses (same person rejected)   False matches (different person accepted)")
        results = sweep(genuine, impostor)
        for result in results:
            self.stdout.write(f"   {result.threshold:.2f}            {result.false_non_match_rate:7.1%}                        {result.false_match_rate:7.2%}")

        self.stdout.write("")
        for name, value in (('confirm', settings.FACE_MATCH_CONFIRM), ('review', settings.FACE_MATCH_REVIEW)):
            current = rates_at(genuine, impostor, value)
            self.stdout.write(
                f"Current {name} threshold {value:.2f}: misses {current.false_non_match_rate:.1%}, "
                f"false matches {current.false_match_rate:.2%}"
            )
        self.stdout.write(
            "These figures describe this set of photos only. With few people the false-match rate is a "
            "rough estimate; report the number of people and pairs alongside it."
        )

        if options['csv']:
            with open(options['csv'], 'w', newline='', encoding='utf-8') as handle:
                writer = csv.writer(handle)
                writer.writerow(['threshold', 'false_non_match_rate', 'false_match_rate', 'genuine_pairs', 'impostor_pairs', 'people', 'model'])
                for result in results:
                    writer.writerow([result.threshold, round(result.false_non_match_rate, 4), round(result.false_match_rate, 4),
                                     genuine.size, impostor.size, len(people), engine.model_name])
            self.stdout.write(self.style.SUCCESS(f"Wrote {options['csv']}"))
