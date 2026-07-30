from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np
from numpy.typing import NDArray

from app.core.config import settings


MINIMUM_BURST_FRAMES = 5
MINIMUM_CHALLENGE_SCORE = 0.55


@dataclass(slots=True)
class LivenessResult:
    is_live: bool
    confidence: float
    signals: dict[str, float]
    frames_analyzed: int
    failure_reasons: list[str]


class LivenessDetector:
    """Active five-frame anti-spoofing with secondary spatial PAD cues.

    The primary signal is a challenge response: normalized YuNet landmarks
    must show non-rigid head-pose change. A detected blink adds limited support
    but cannot pass alone. Face crops are affine-aligned to measure residual
    non-rigid motion. Spatial cues penalize
    moire, display chroma, unnatural edge sharpness, and broad glare, but never
    establish liveness by themselves.
    """

    def __init__(self, threshold: float = settings.liveness_threshold) -> None:
        self.threshold = threshold
        self._eye_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
        )

    def analyze(
        self,
        face_region: NDArray[np.uint8],
        additional_regions: list[NDArray[np.uint8]] | None = None,
        landmark_sequence: list[NDArray[np.float32]] | None = None,
    ) -> LivenessResult:
        if face_region.size == 0:
            return LivenessResult(
                is_live=False,
                confidence=0.0,
                signals={},
                frames_analyzed=0,
                failure_reasons=["empty_face_region"],
            )

        regions = [face_region, *(additional_regions or [])]
        frames_analyzed = len(regions)
        resized = cv2.resize(face_region, (192, 192), interpolation=cv2.INTER_AREA)
        grayscale = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        focus_score, edge_score = self._edge_quality(grayscale)
        color_score, chroma_score = self._color_quality(resized)
        moire_score = self._moire_quality(resized)
        specular_score = self._specular_quality(resized)
        spatial_score = float(
            0.18 * focus_score
            + 0.14 * edge_score
            + 0.16 * color_score
            + 0.18 * chroma_score
            + 0.20 * moire_score
            + 0.14 * specular_score
        )

        landmarks = landmark_sequence or []
        pose_score = self._pose_change_score(landmarks)
        depth_score = self._depth_parallax_score(landmarks)
        head_turn_score = float(np.sqrt(pose_score * depth_score))
        blink_score = self._blink_score(regions)
        challenge_score = max(head_turn_score, 0.25 * blink_score)
        nonrigid_score = self._nonrigid_motion_score(grayscale, regions[1:])

        # A rigidly moved photo can score well spatially and produce pixel
        # motion. Capping spatial/non-rigid influence at 35% keeps such an
        # attack below 50% unless it also satisfies the active challenge.
        confidence = float(
            0.15 * spatial_score
            + 0.65 * challenge_score
            + 0.20 * nonrigid_score
        )
        confidence = max(0.0, min(1.0, confidence))

        failure_reasons: list[str] = []
        if frames_analyzed < MINIMUM_BURST_FRAMES:
            failure_reasons.append("need_five_frame_burst")
        if challenge_score < MINIMUM_CHALLENGE_SCORE:
            failure_reasons.append("head_turn_not_detected")
        if confidence < self.threshold:
            failure_reasons.append("confidence_below_threshold")

        signals = {
            "focus": focus_score,
            "edge": edge_score,
            "color": color_score,
            "chroma": chroma_score,
            "moire": moire_score,
            "specular": specular_score,
            "pose_change": pose_score,
            "depth_parallax": depth_score,
            "head_turn": head_turn_score,
            "blink": blink_score,
            "nonrigid_motion": nonrigid_score,
            "spatial": spatial_score,
            "challenge": challenge_score,
        }
        return LivenessResult(
            is_live=not failure_reasons,
            confidence=confidence,
            signals=signals,
            frames_analyzed=frames_analyzed,
            failure_reasons=failure_reasons,
        )

    @classmethod
    def _edge_quality(
        cls,
        grayscale: NDArray[np.uint8],
    ) -> tuple[float, float]:
        laplacian_variance = float(
            cv2.Laplacian(grayscale, cv2.CV_64F).var()
        )
        focus_floor = cls._smoothstep(laplacian_variance, 20.0, 130.0)
        oversharpen_penalty = 1.0 - cls._smoothstep(
            laplacian_variance, 850.0, 2200.0
        )
        focus_score = focus_floor * oversharpen_penalty

        edges = cv2.Canny(grayscale, 70, 160)
        edge_density = float(np.mean(edges > 0))
        edge_floor = cls._smoothstep(edge_density, 0.025, 0.09)
        edge_excess_penalty = 1.0 - cls._smoothstep(
            edge_density, 0.24, 0.42
        )
        return focus_score, edge_floor * edge_excess_penalty

    @classmethod
    def _color_quality(
        cls,
        image: NDArray[np.uint8],
    ) -> tuple[float, float]:
        ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        _, cr, cb = cv2.split(ycrcb)
        skin_mask = (
            (cr >= 128)
            & (cr <= 185)
            & (cb >= 72)
            & (cb <= 145)
        )
        skin_ratio = float(np.mean(skin_mask))
        skin_floor = cls._smoothstep(skin_ratio, 0.04, 0.28)
        uniform_color_penalty = 1.0 - cls._smoothstep(
            skin_ratio, 0.92, 0.995
        )
        color_score = skin_floor * uniform_color_penalty

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        _, channel_a, channel_b = cv2.split(lab)
        chroma_residuals = []
        for channel in (channel_a, channel_b):
            blurred = cv2.GaussianBlur(channel, (0, 0), 1.0)
            chroma_residuals.append(
                float(np.std(channel.astype(np.float32) - blurred))
            )
        chroma_noise = float(np.mean(chroma_residuals))
        chroma_floor = cls._smoothstep(chroma_noise, 0.15, 0.9)
        display_noise_penalty = 1.0 - cls._smoothstep(
            chroma_noise, 3.8, 10.0
        )
        return color_score, chroma_floor * display_noise_penalty

    @classmethod
    def _moire_quality(cls, image: NDArray[np.uint8]) -> float:
        blue, green, red = cv2.split(image.astype(np.float32))
        opponent_channels = (red - green, blue - green)
        peak_strengths: list[float] = []

        height, width = image.shape[:2]
        y_grid, x_grid = np.ogrid[:height, :width]
        center_y, center_x = height // 2, width // 2
        radius = np.sqrt((y_grid - center_y) ** 2 + (x_grid - center_x) ** 2)
        frequency_mask = (
            (radius >= min(height, width) * 0.12)
            & (radius <= min(height, width) * 0.46)
        )
        window = np.outer(np.hanning(height), np.hanning(width))

        for channel in opponent_channels:
            spectrum = np.log1p(
                np.abs(np.fft.fftshift(np.fft.fft2(channel * window)))
            )
            values = spectrum[frequency_mask]
            median = float(np.median(values))
            deviation = float(np.median(np.abs(values - median)))
            robust_scale = max(1e-6, 1.4826 * deviation)
            peak_strengths.append(
                float((np.percentile(values, 99.8) - median) / robust_scale)
            )

        periodic_peak_strength = max(peak_strengths)
        return 1.0 - cls._smoothstep(periodic_peak_strength, 10.0, 28.0)

    @classmethod
    def _specular_quality(cls, image: NDArray[np.uint8]) -> float:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        _, saturation, value = cv2.split(hsv)
        glare_mask = ((value >= 238) & (saturation <= 42)).astype(np.uint8)
        glare_ratio = float(np.mean(glare_mask))

        largest_blob_ratio = 0.0
        count, _, stats, _ = cv2.connectedComponentsWithStats(
            glare_mask, connectivity=8
        )
        if count > 1:
            largest_blob_ratio = float(
                np.max(stats[1:, cv2.CC_STAT_AREA]) / glare_mask.size
            )

        glare_penalty = cls._smoothstep(glare_ratio, 0.025, 0.14)
        reflection_penalty = cls._smoothstep(
            largest_blob_ratio, 0.012, 0.09
        )
        return 1.0 - max(glare_penalty, reflection_penalty)

    @classmethod
    def _pose_change_score(
        cls,
        landmarks: list[NDArray[np.float32]],
    ) -> float:
        if len(landmarks) < MINIMUM_BURST_FRAMES:
            return 0.0

        features = [cls._landmark_features(points) for points in landmarks]
        reference = features[0]
        changes = [
            float(np.linalg.norm(feature - reference))
            for feature in features[1:]
        ]
        pose_change = float(np.percentile(changes, 80))
        return cls._smoothstep(pose_change, 0.035, 0.14)

    @staticmethod
    def _landmark_features(
        landmarks: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        if landmarks.shape != (5, 2):
            return np.zeros(5, dtype=np.float32)

        eye_a, eye_b, nose, mouth_a, mouth_b = landmarks
        eye_midpoint = (eye_a + eye_b) / 2.0
        mouth_midpoint = (mouth_a + mouth_b) / 2.0
        eye_distance = max(1e-4, float(np.linalg.norm(eye_a - eye_b)))
        mouth_distance = float(np.linalg.norm(mouth_a - mouth_b))
        return np.asarray(
            [
                (nose[0] - eye_midpoint[0]) / eye_distance,
                (nose[1] - eye_midpoint[1]) / eye_distance,
                (mouth_midpoint[0] - nose[0]) / eye_distance,
                eye_distance,
                mouth_distance,
            ],
            dtype=np.float32,
        )

    @classmethod
    def _depth_parallax_score(
        cls,
        landmarks: list[NDArray[np.float32]],
    ) -> float:
        if len(landmarks) < MINIMUM_BURST_FRAMES:
            return 0.0

        reference = landmarks[0]
        if reference.shape != (5, 2):
            return 0.0
        plane_indices = [0, 1, 3, 4]
        plane_reference = reference[plane_indices].astype(np.float32)
        nose_reference = reference[2].reshape(1, 1, 2).astype(np.float32)
        nose_residuals: list[float] = []

        for current in landmarks[1:]:
            if current.shape != (5, 2):
                continue
            homography = cv2.getPerspectiveTransform(
                plane_reference,
                current[plane_indices].astype(np.float32),
            )
            predicted_nose = cv2.perspectiveTransform(
                nose_reference,
                homography,
            ).reshape(2)
            nose_residuals.append(
                float(np.linalg.norm(predicted_nose - current[2]))
            )

        if not nose_residuals:
            return 0.0
        parallax = float(np.percentile(nose_residuals, 80))
        return cls._smoothstep(parallax, 0.006, 0.035)

    def _blink_score(
        self,
        regions: list[NDArray[np.uint8]],
    ) -> float:
        if len(regions) < MINIMUM_BURST_FRAMES or self._eye_detector.empty():
            return 0.0

        eye_counts: list[int] = []
        for region in regions:
            resized = cv2.resize(region, (192, 192), interpolation=cv2.INTER_AREA)
            grayscale = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            upper_face = cv2.equalizeHist(grayscale[:115, :])
            eyes = self._eye_detector.detectMultiScale(
                upper_face,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(18, 18),
                maxSize=(72, 72),
            )
            eye_counts.append(min(2, len(eyes)))

        open_before = eye_counts[0] >= 2 or eye_counts[1] >= 2
        closed_middle = any(count == 0 for count in eye_counts[1:-1])
        open_after = eye_counts[-1] >= 2 or eye_counts[-2] >= 2
        return 1.0 if open_before and closed_middle and open_after else 0.0

    @classmethod
    def _nonrigid_motion_score(
        cls,
        reference: NDArray[np.uint8],
        additional_regions: list[NDArray[np.uint8]],
    ) -> float:
        if len(additional_regions) < MINIMUM_BURST_FRAMES - 1:
            return 0.0

        residuals: list[float] = []
        height, width = reference.shape
        mask = np.zeros_like(reference, dtype=np.uint8)
        cv2.ellipse(
            mask,
            (width // 2, height // 2),
            (int(width * 0.34), int(height * 0.42)),
            0,
            0,
            360,
            255,
            -1,
        )
        criteria = (
            cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
            40,
            1e-4,
        )

        for region in additional_regions:
            if region.size == 0:
                continue
            resized = cv2.resize(region, (width, height), interpolation=cv2.INTER_AREA)
            grayscale = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            warp = np.eye(2, 3, dtype=np.float32)
            try:
                _, warp = cv2.findTransformECC(
                    reference,
                    grayscale,
                    warp,
                    cv2.MOTION_AFFINE,
                    criteria,
                    mask,
                    3,
                )
                aligned = cv2.warpAffine(
                    grayscale,
                    warp,
                    (width, height),
                    flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                    borderMode=cv2.BORDER_REFLECT,
                )
            except cv2.error:
                aligned = grayscale

            difference = cv2.absdiff(reference, aligned)
            residuals.append(float(np.mean(difference[mask > 0])))

        if not residuals:
            return 0.0
        residual = float(np.percentile(residuals, 70))
        meaningful_change = cls._smoothstep(residual, 2.5, 11.0)
        excessive_change_penalty = 1.0 - cls._smoothstep(
            residual, 32.0, 58.0
        )
        return meaningful_change * excessive_change_penalty

    @staticmethod
    def _smoothstep(value: float, low: float, high: float) -> float:
        if high <= low:
            return 0.0
        normalized = max(0.0, min(1.0, (value - low) / (high - low)))
        return normalized * normalized * (3.0 - 2.0 * normalized)


@lru_cache(maxsize=1)
def get_liveness_detector() -> LivenessDetector:
    return LivenessDetector()
