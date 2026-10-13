"""Encrypted storage of face embeddings."""
from __future__ import annotations

import numpy as np
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.academics.models import ClassGroup

from .models import FaceEnrollment


def _cipher() -> Fernet:
    key = settings.FACE_EMBEDDING_KEY
    if not key:
        raise ImproperlyConfigured(
            "FACE_EMBEDDING_KEY is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "and add it to backend/.env."
        )
    return Fernet(key.encode())


def encrypt_embedding(vector: np.ndarray) -> bytes:
    return _cipher().encrypt(np.asarray(vector, dtype=np.float32).tobytes())


def decrypt_embedding(blob: bytes) -> np.ndarray:
    try:
        return np.frombuffer(_cipher().decrypt(bytes(blob)), dtype=np.float32)
    except InvalidToken as error:
        raise ImproperlyConfigured("A stored face embedding cannot be decrypted with FACE_EMBEDDING_KEY.") from error


def gallery_for_class(class_group: ClassGroup, model_name: str) -> dict[int, np.ndarray]:
    """
    Embeddings of consenting, active students enrolled in one class group, keyed by student id.
    Only embeddings produced by `model_name` are used: vectors from different models are not comparable.
    """
    rows = FaceEnrollment.objects.filter(
        student__class_groups=class_group,
        student__is_active=True,
        student__consent_given=True,
        model_name=model_name,
    ).values_list('student_id', 'embedding')
    grouped: dict[int, list[np.ndarray]] = {}
    for student_id, blob in rows:
        grouped.setdefault(student_id, []).append(decrypt_embedding(blob))
    return {student_id: np.stack(vectors) for student_id, vectors in grouped.items()}
