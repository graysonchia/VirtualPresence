from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from numpy.typing import NDArray

from app.core.config import settings
from app.core.exceptions import FaceModelsMissingError


EMOTION_MODEL_FILENAME = "emotion-ferplus-8.onnx"
MODEL_LABELS = (
    "neutral",
    "happy",
    "surprised",
    "sad",
    "angry",
    "disgusted",
    "fearful",
    "contempt",
)
PUBLIC_LABELS = (
    "happy",
    "sad",
    "angry",
    "surprised",
    "neutral",
    "fearful",
    "disgusted",
)


@dataclass(slots=True)
class EmotionResult:
    label: str
    confidence: float
    scores: dict[str, float]


class EmotionDetector:
    """FER+ facial-expression inference through OpenCV's ONNX runtime."""

    def __init__(self, model_dir: Path = settings.face_model_dir) -> None:
        model_path = model_dir / EMOTION_MODEL_FILENAME
        if not model_path.is_file():
            raise FaceModelsMissingError(
                f"Emotion model is missing: {model_path}. "
                "Run `python scripts/download_face_models.py` from backend."
            )
        self._network = cv2.dnn.readNetFromONNX(str(model_path))
        self._inference_lock = Lock()

    def analyze(self, face_region: NDArray[np.uint8]) -> EmotionResult:
        if face_region.size == 0:
            raise ValueError("Emotion detection requires a non-empty face region.")

        grayscale = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        blob = cv2.dnn.blobFromImage(
            grayscale,
            scalefactor=1.0,
            size=(64, 64),
            mean=(0.0,),
            swapRB=False,
            crop=False,
        )
        with self._inference_lock:
            self._network.setInput(blob)
            raw_scores = self._network.forward().reshape(-1)
        return self.scores_to_result(raw_scores)

    @staticmethod
    def scores_to_result(raw_scores: NDArray[np.floating]) -> EmotionResult:
        if raw_scores.size != len(MODEL_LABELS):
            raise ValueError(
                f"FER+ returned {raw_scores.size} scores; expected {len(MODEL_LABELS)}."
            )

        shifted = raw_scores.astype(np.float64) - float(np.max(raw_scores))
        probabilities = np.exp(shifted)
        probabilities /= float(np.sum(probabilities))
        model_scores = dict(zip(MODEL_LABELS, probabilities, strict=True))

        # FER+ has an eighth "contempt" class. Fold it into neutral so the
        # public result stays within the seven requested emotion labels.
        model_scores["neutral"] += model_scores.pop("contempt")
        scores = {
            label: float(model_scores[label])
            for label in PUBLIC_LABELS
        }
        label = max(scores, key=scores.get)
        return EmotionResult(
            label=label,
            confidence=scores[label],
            scores=scores,
        )


@lru_cache(maxsize=1)
def get_emotion_detector() -> EmotionDetector:
    return EmotionDetector()

