from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from numpy.typing import NDArray

from app.core.config import settings
from app.core.exceptions import (
    FaceModelsMissingError,
    FaceNotFoundError,
    MultipleFacesError,
)


DETECTOR_FILENAME = "face_detection_yunet_2023mar.onnx"
RECOGNIZER_FILENAME = "face_recognition_sface_2021dec.onnx"


@dataclass(slots=True)
class DetectedFace:
    embedding: list[float]
    region: NDArray[np.uint8]
    bounding_box: tuple[int, int, int, int]
    landmarks: NDArray[np.float32]
    detection_confidence: float


class OpenCVFaceEngine:
    """YuNet detection and SFace embedding extraction using OpenCV DNN."""

    def __init__(
        self,
        model_dir: Path = settings.face_model_dir,
        detection_threshold: float = settings.face_detection_threshold,
    ) -> None:
        detector_path = model_dir / DETECTOR_FILENAME
        recognizer_path = model_dir / RECOGNIZER_FILENAME
        missing = [
            str(path)
            for path in (detector_path, recognizer_path)
            if not path.is_file()
        ]
        if missing:
            raise FaceModelsMissingError(
                "Face model files are missing: "
                + ", ".join(missing)
                + ". Run `python scripts/download_face_models.py` from backend."
            )

        self.detector = cv2.FaceDetectorYN.create(
            str(detector_path),
            "",
            (320, 320),
            score_threshold=detection_threshold,
            nms_threshold=0.3,
            top_k=5000,
        )
        self.recognizer = cv2.FaceRecognizerSF.create(str(recognizer_path), "")
        self._inference_lock = Lock()

    @staticmethod
    def decode_image(image_bytes: bytes) -> NDArray[np.uint8]:
        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            raise ValueError("The uploaded file is not a valid image.")
        return image

    def detect_faces(self, image: NDArray[np.uint8]) -> NDArray[np.float32]:
        height, width = image.shape[:2]
        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(image)
        if faces is None:
            return np.empty((0, 15), dtype=np.float32)
        return faces

    def extract_embeddings(
        self,
        image_bytes: bytes,
        *,
        require_single_face: bool = False,
    ) -> list[list[float]]:
        return [
            face.embedding
            for face in self.analyze_faces(
                image_bytes, require_single_face=require_single_face
            )
        ]

    def analyze_faces(
        self,
        image_bytes: bytes,
        *,
        require_single_face: bool = False,
    ) -> list[DetectedFace]:
        image = self.decode_image(image_bytes)
        # OpenCV DNN objects mutate their input shape and are not thread-safe.
        with self._inference_lock:
            faces = self.detect_faces(image)

            if len(faces) == 0:
                raise FaceNotFoundError(
                    "No face was detected. Face the camera in even lighting and try again."
                )
            if require_single_face and len(faces) > 1:
                raise MultipleFacesError(
                    "Enrollment requires exactly one face in the image."
                )

            detected_faces: list[DetectedFace] = []
            selected_faces = faces[:1] if require_single_face else faces
            for face in selected_faces:
                aligned = self.recognizer.alignCrop(image, face)
                feature = (
                    self.recognizer.feature(aligned)
                    .flatten()
                    .astype(np.float32)
                )
                norm = float(np.linalg.norm(feature))
                if norm == 0:
                    raise ValueError("The face embedding could not be normalized.")
                x, y, width, height = (int(value) for value in face[:4])
                x1 = max(0, x)
                y1 = max(0, y)
                x2 = min(image.shape[1], x + width)
                y2 = min(image.shape[0], y + height)
                region = image[y1:y2, x1:x2].copy()
                if region.size == 0:
                    continue
                landmarks = face[4:14].reshape(5, 2).astype(np.float32)
                landmarks[:, 0] = (landmarks[:, 0] - x1) / max(1, x2 - x1)
                landmarks[:, 1] = (landmarks[:, 1] - y1) / max(1, y2 - y1)
                detected_faces.append(
                    DetectedFace(
                        embedding=(feature / norm).tolist(),
                        region=region,
                        bounding_box=(x1, y1, x2 - x1, y2 - y1),
                        landmarks=landmarks,
                        detection_confidence=float(face[-1]),
                    )
                )

            if not detected_faces:
                raise FaceNotFoundError("No usable face region was detected.")
            detected_faces.sort(
                key=lambda item: item.bounding_box[2] * item.bounding_box[3],
                reverse=True,
            )
            return detected_faces


@lru_cache(maxsize=1)
def get_face_engine() -> OpenCVFaceEngine:
    return OpenCVFaceEngine()
