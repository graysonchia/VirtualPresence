"""Simulated edge-optimized YuNet + SFace inference.

This module demonstrates an edge deployment pattern on the same machine as the
standard API. It is deliberately not presented as a separate physical edge
device. YuNet receives a bounded 320 px frame and OpenCV DNN quantizes the
SFace recognizer to INT8 in memory. In a real deployment this service would run
on the camera/kiosk, keeping raw biometric frames inside that device boundary.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import fmean
from threading import Lock
from time import perf_counter

import cv2
import numpy as np
from numpy.typing import NDArray

from app.core.config import settings
from app.core.exceptions import FaceModelsMissingError, FaceNotFoundError
from app.services.face.engine import (
    DETECTOR_FILENAME,
    RECOGNIZER_FILENAME,
    DetectedFace,
    OpenCVFaceEngine,
    get_face_engine,
)


EDGE_MAX_DIMENSION = 320
BENCHMARK_ITERATIONS = 3
ALIGNMENT_TEMPLATE = np.asarray(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


@dataclass(slots=True)
class InferenceProfile:
    model_size_mb: float
    mean_latency_ms: float
    accuracy_percent: float | None
    model_size_metric: str
    precision: str


@dataclass(slots=True)
class EdgeBenchmark:
    standard: InferenceProfile
    edge_optimized: InferenceProfile
    sample_count: int
    samples_source: str
    size_reduction_percent: float
    latency_reduction_percent: float
    accuracy_delta_percentage_points: float | None
    notes: list[str]


class EdgeOpenCVFaceEngine:
    """YuNet + an in-memory INT8 SFace net for an edge-sized CPU workload."""

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
            (EDGE_MAX_DIMENSION, EDGE_MAX_DIMENSION),
            score_threshold=detection_threshold,
            nms_threshold=0.3,
            top_k=5000,
        )

        detector_net = cv2.dnn.readNetFromONNX(str(detector_path))
        detector_parameters, _ = detector_net.getMemoryConsumption(
            [1, 3, EDGE_MAX_DIMENSION, EDGE_MAX_DIMENSION]
        )
        recognizer_source = cv2.dnn.readNetFromONNX(str(recognizer_path))
        standard_parameters, _ = recognizer_source.getMemoryConsumption(
            [1, 3, 112, 112]
        )
        try:
            self.recognizer = recognizer_source.quantize(
                [self._calibration_batch()],
                cv2.CV_32F,
                cv2.CV_32F,
                True,
            )
        except cv2.error as exc:
            raise RuntimeError(
                "This OpenCV build cannot create the in-memory INT8 SFace model."
            ) from exc
        edge_parameters, _ = self.recognizer.getMemoryConsumption(
            [1, 3, 112, 112]
        )
        self.standard_parameter_bytes = int(
            detector_parameters + standard_parameters
        )
        self.edge_parameter_bytes = int(detector_parameters + edge_parameters)
        self._inference_lock = Lock()

    @staticmethod
    def _calibration_batch() -> NDArray[np.float32]:
        """Return deterministic, non-biometric calibration tensors.

        SFace's OpenCV wrapper passes unnormalised 0..255 pixels with RGB channel
        order. Using synthetic tensors prevents calibration from retaining or
        depending on a person's enrollment photo.
        """

        generator = np.random.default_rng(seed=20260804)
        return generator.integers(
            0,
            256,
            size=(8, 3, 112, 112),
            dtype=np.uint8,
        ).astype(np.float32)

    @staticmethod
    def decode_image(image_bytes: bytes) -> NDArray[np.uint8]:
        return OpenCVFaceEngine.decode_image(image_bytes)

    @staticmethod
    def _edge_resize(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        height, width = image.shape[:2]
        scale = min(1.0, EDGE_MAX_DIMENSION / max(height, width))
        if scale == 1.0:
            return image
        return cv2.resize(
            image,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )

    @staticmethod
    def _align_face(
        image: NDArray[np.uint8], landmarks: NDArray[np.float32]
    ) -> NDArray[np.uint8]:
        transform, _ = cv2.estimateAffinePartial2D(
            landmarks,
            ALIGNMENT_TEMPLATE,
            method=cv2.LMEDS,
        )
        if transform is None:
            raise ValueError("The detected face could not be aligned.")
        return cv2.warpAffine(image, transform, (112, 112))

    def _feature(self, aligned: NDArray[np.uint8]) -> list[float]:
        # This matches FaceRecognizerSF: raw 0..255 pixels and RGB channel order.
        blob = cv2.dnn.blobFromImage(
            aligned,
            scalefactor=1.0,
            size=(112, 112),
            mean=(0, 0, 0),
            swapRB=True,
            crop=False,
        )
        self.recognizer.setInput(blob)
        feature = self.recognizer.forward().flatten().astype(np.float32)
        norm = float(np.linalg.norm(feature))
        if norm == 0:
            raise ValueError("The face embedding could not be normalized.")
        return (feature / norm).tolist()

    def analyze_faces(
        self,
        image_bytes: bytes,
        *,
        require_single_face: bool = False,
    ) -> list[DetectedFace]:
        image = self._edge_resize(self.decode_image(image_bytes))
        height, width = image.shape[:2]
        with self._inference_lock:
            self.detector.setInputSize((width, height))
            _, faces = self.detector.detect(image)
            if faces is None or len(faces) == 0:
                raise FaceNotFoundError(
                    "No face was detected. Face the camera in even lighting and try again."
                )

            selected_faces = faces[:1] if require_single_face else faces
            detected_faces: list[DetectedFace] = []
            for face in selected_faces:
                x, y, face_width, face_height = (int(value) for value in face[:4])
                x1, y1 = max(0, x), max(0, y)
                x2 = min(width, x + face_width)
                y2 = min(height, y + face_height)
                region = image[y1:y2, x1:x2].copy()
                if region.size == 0:
                    continue

                absolute_landmarks = face[4:14].reshape(5, 2).astype(np.float32)
                aligned = self._align_face(image, absolute_landmarks)
                relative_landmarks = absolute_landmarks.copy()
                relative_landmarks[:, 0] = (
                    relative_landmarks[:, 0] - x1
                ) / max(1, x2 - x1)
                relative_landmarks[:, 1] = (
                    relative_landmarks[:, 1] - y1
                ) / max(1, y2 - y1)
                detected_faces.append(
                    DetectedFace(
                        embedding=self._feature(aligned),
                        region=region,
                        bounding_box=(x1, y1, x2 - x1, y2 - y1),
                        landmarks=relative_landmarks,
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


def _benchmark_samples(limit: int = 5) -> tuple[list[bytes], str]:
    supported = {".jpg", ".jpeg", ".png", ".webp"}
    if settings.enrollment_storage_dir.is_dir():
        samples = [
            path.read_bytes()
            for path in sorted(settings.enrollment_storage_dir.iterdir())
            if path.suffix.lower() in supported and path.is_file()
        ][:limit]
        if samples:
            return samples, "local enrollment frames (processed locally only)"

    # A benchmark remains available before enrollment. These frames exercise
    # detection only; embedding fidelity is therefore reported as unavailable.
    synthetic: list[bytes] = []
    for seed in range(3):
        generator = np.random.default_rng(seed=seed)
        frame = generator.integers(0, 256, (480, 640, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", frame)
        if ok:
            synthetic.append(encoded.tobytes())
    return synthetic, "deterministic synthetic frames (detection-only)"


def _run_once(engine: object, image_bytes: bytes) -> list[DetectedFace]:
    try:
        return engine.analyze_faces(image_bytes)  # type: ignore[attr-defined]
    except FaceNotFoundError:
        return []


def benchmark_edge_inference(
    standard_engine: OpenCVFaceEngine | None = None,
    edge_engine: EdgeOpenCVFaceEngine | None = None,
) -> EdgeBenchmark:
    """Benchmark warmed inference; model construction/calibration is excluded."""

    standard = standard_engine or get_face_engine()
    edge = edge_engine or get_edge_face_engine()
    samples, source = _benchmark_samples()

    standard_latencies: list[float] = []
    edge_latencies: list[float] = []
    fidelity_scores: list[float] = []
    for sample in samples:
        # Warm each mutable OpenCV DNN path before measuring it.
        _run_once(standard, sample)
        _run_once(edge, sample)
        for _ in range(BENCHMARK_ITERATIONS):
            started = perf_counter()
            _run_once(standard, sample)
            standard_latencies.append((perf_counter() - started) * 1000)

            started = perf_counter()
            _run_once(edge, sample)
            edge_latencies.append((perf_counter() - started) * 1000)

        standard_faces = _run_once(standard, sample)
        edge_faces = _run_once(edge, sample)
        if standard_faces and edge_faces:
            standard_embedding = np.asarray(
                standard_faces[0].embedding, dtype=np.float32
            )
            edge_embedding = np.asarray(edge_faces[0].embedding, dtype=np.float32)
            fidelity_scores.append(
                max(0.0, min(1.0, float(np.dot(standard_embedding, edge_embedding))))
            )

    standard_latency = fmean(standard_latencies) if standard_latencies else 0.0
    edge_latency = fmean(edge_latencies) if edge_latencies else 0.0
    fidelity = fmean(fidelity_scores) * 100 if fidelity_scores else None
    standard_size = edge.standard_parameter_bytes / (1024 * 1024)
    edge_size = edge.edge_parameter_bytes / (1024 * 1024)
    size_reduction = (1 - edge_size / standard_size) * 100
    latency_reduction = (
        (1 - edge_latency / standard_latency) * 100
        if standard_latency > 0
        else 0.0
    )

    return EdgeBenchmark(
        standard=InferenceProfile(
            model_size_mb=round(standard_size, 2),
            mean_latency_ms=round(standard_latency, 2),
            accuracy_percent=100.0 if fidelity is not None else None,
            model_size_metric="OpenCV DNN runtime parameter footprint",
            precision="FP32 YuNet + FP32 SFace",
        ),
        edge_optimized=InferenceProfile(
            model_size_mb=round(edge_size, 2),
            mean_latency_ms=round(edge_latency, 2),
            accuracy_percent=round(fidelity, 2) if fidelity is not None else None,
            model_size_metric="OpenCV DNN runtime parameter footprint",
            precision="FP32 YuNet at <=320 px + INT8 SFace",
        ),
        sample_count=len(samples),
        samples_source=source,
        size_reduction_percent=round(size_reduction, 2),
        latency_reduction_percent=round(latency_reduction, 2),
        accuracy_delta_percentage_points=(
            round(fidelity - 100.0, 2) if fidelity is not None else None
        ),
        notes=[
            "Latency is a warmed local measurement and excludes one-time INT8 calibration.",
            "Accuracy is cosine agreement with FP32 embeddings, not a population accuracy claim.",
            "OpenCV executes the quantized net in memory but does not export it; size is the runtime parameter footprint.",
        ],
    )


@lru_cache(maxsize=1)
def get_edge_face_engine() -> EdgeOpenCVFaceEngine:
    return EdgeOpenCVFaceEngine()
