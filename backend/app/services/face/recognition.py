import asyncio
from dataclasses import dataclass
from uuid import uuid4

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.exceptions import FaceNotFoundError
from app.models.face_embedding import FaceEmbedding
from app.models.recognition_event import RecognitionEvent, RecognitionOutcome
from app.models.user import User
from app.services.face.emotion import EmotionDetector
from app.services.face.engine import DetectedFace, OpenCVFaceEngine
from app.services.face.liveness import LivenessDetector


@dataclass(slots=True)
class RecognitionResult:
    outcome: RecognitionOutcome
    confidence: float
    user: User | None
    faces_detected: int
    detected_emotion: str | None
    emotion_confidence: float | None
    emotion_scores: dict[str, float]
    is_live: bool
    liveness_confidence: float


async def identify_user(
    db: AsyncSession,
    engine: OpenCVFaceEngine,
    emotion_detector: EmotionDetector,
    liveness_detector: LivenessDetector,
    *,
    image_bytes: bytes,
    additional_frame_bytes: list[bytes] | None = None,
) -> RecognitionResult:
    try:
        detected_faces = await asyncio.to_thread(
            engine.analyze_faces, image_bytes
        )
    except FaceNotFoundError:
        result = RecognitionResult(
            outcome=RecognitionOutcome.UNRECOGNIZED,
            confidence=0.0,
            user=None,
            faces_detected=0,
            detected_emotion=None,
            emotion_confidence=None,
            emotion_scores={},
            is_live=False,
            liveness_confidence=0.0,
        )
        await _log_result(db, result)
        return result
    except ValueError:
        # Accepted uploads that cannot be decoded still count as attempts.
        await _log_result(
            db,
            RecognitionResult(
                outcome=RecognitionOutcome.UNRECOGNIZED,
                confidence=0.0,
                user=None,
                faces_detected=0,
                detected_emotion=None,
                emotion_confidence=None,
                emotion_scores={},
                is_live=False,
                liveness_confidence=0.0,
            ),
        )
        raise

    rows = await db.execute(
        select(FaceEmbedding).options(joinedload(FaceEmbedding.user))
    )
    enrolled = list(rows.scalars().all())

    best_score = -1.0
    best_user: User | None = None
    best_face_index = 0
    for face_index, detected_face in enumerate(detected_faces):
        query = np.asarray(detected_face.embedding, dtype=np.float32)
        for candidate in enrolled:
            stored = np.asarray(candidate.embedding_vector, dtype=np.float32)
            score = float(np.dot(query, stored))
            if score > best_score:
                best_score = score
                best_user = candidate.user
                best_face_index = face_index

    confidence = max(0.0, min(1.0, best_score))
    identity_recognized = (
        best_user is not None and best_score >= settings.face_match_threshold
    )
    analysis_face = detected_faces[best_face_index]
    additional_faces = await _extract_additional_faces(
        engine,
        additional_frame_bytes or [],
    )
    additional_regions = [face.region for face in additional_faces]
    landmark_sequence = [
        analysis_face.landmarks,
        *(face.landmarks for face in additional_faces),
    ]
    emotion, liveness = await asyncio.gather(
        asyncio.to_thread(emotion_detector.analyze, analysis_face.region),
        asyncio.to_thread(
            liveness_detector.analyze,
            analysis_face.region,
            additional_regions,
            landmark_sequence,
        ),
    )

    if not liveness.is_live:
        outcome = RecognitionOutcome.SPOOF_DETECTED
    elif identity_recognized:
        outcome = RecognitionOutcome.RECOGNIZED
    else:
        outcome = RecognitionOutcome.UNRECOGNIZED

    result = RecognitionResult(
        outcome=outcome,
        confidence=confidence,
        user=best_user if identity_recognized else None,
        faces_detected=len(detected_faces),
        detected_emotion=emotion.label,
        emotion_confidence=emotion.confidence,
        emotion_scores=emotion.scores,
        is_live=liveness.is_live,
        liveness_confidence=liveness.confidence,
    )
    await _log_result(db, result)
    return result


async def _log_result(db: AsyncSession, result: RecognitionResult) -> None:
    db.add(
        RecognitionEvent(
            id=str(uuid4()),
            user_id=result.user.id if result.user else None,
            confidence=result.confidence,
            detected_emotion=result.detected_emotion,
            emotion_confidence=result.emotion_confidence,
            is_live=result.is_live,
            liveness_confidence=result.liveness_confidence,
            outcome=result.outcome,
        )
    )
    await db.commit()


async def _extract_additional_faces(
    engine: OpenCVFaceEngine,
    frame_bytes: list[bytes],
) -> list[DetectedFace]:
    detected_faces: list[DetectedFace] = []
    for frame in frame_bytes:
        try:
            faces = await asyncio.to_thread(engine.analyze_faces, frame)
        except (FaceNotFoundError, ValueError):
            continue
        detected_faces.append(faces[0])
    return detected_faces
