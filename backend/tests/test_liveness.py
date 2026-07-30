import cv2
import numpy as np

from app.services.face.liveness import LivenessDetector


def _face_image() -> np.ndarray:
    generator = np.random.default_rng(seed=42)
    image = np.full((192, 192, 3), (92, 142, 188), dtype=np.uint8)
    noise = generator.normal(0, 3.0, image.shape).astype(np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    cv2.ellipse(image, (65, 73), (18, 8), 0, 0, 360, (50, 60, 70), 2)
    cv2.ellipse(image, (127, 73), (18, 8), 0, 0, 360, (50, 60, 70), 2)
    cv2.line(image, (96, 82), (92, 116), (70, 105, 145), 3)
    cv2.ellipse(image, (96, 139), (30, 10), 0, 0, 180, (50, 55, 110), 3)
    return image


def _base_landmarks() -> np.ndarray:
    return np.asarray(
        [
            [0.34, 0.38],
            [0.66, 0.38],
            [0.50, 0.56],
            [0.40, 0.73],
            [0.60, 0.73],
        ],
        dtype=np.float32,
    )


def test_empty_face_region_is_not_live() -> None:
    detector = LivenessDetector()

    result = detector.analyze(np.empty((0, 0, 3), dtype=np.uint8))

    assert result.is_live is False
    assert result.confidence == 0.0
    assert result.failure_reasons == ["empty_face_region"]


def test_single_frame_is_always_unverified() -> None:
    detector = LivenessDetector()

    result = detector.analyze(_face_image())

    assert result.is_live is False
    assert result.confidence < 0.5
    assert "need_five_frame_burst" in result.failure_reasons


def test_rigidly_moved_photo_remains_below_fifty_percent() -> None:
    detector = LivenessDetector()
    face = _face_image()
    rigid_frames = [
        cv2.warpAffine(
            face,
            np.asarray([[1.0, 0.0, offset], [0.0, 1.0, offset / 2]]),
            (192, 192),
            borderMode=cv2.BORDER_REFLECT,
        )
        for offset in (2.0, 4.0, 6.0, 8.0)
    ]
    landmarks = [_base_landmarks().copy() for _ in range(5)]

    result = detector.analyze(face, rigid_frames, landmarks)

    assert result.is_live is False
    assert result.confidence < 0.5
    assert result.signals["pose_change"] == 0.0
    assert "head_turn_not_detected" in result.failure_reasons


def test_perspective_rotated_photo_remains_planar_and_fails() -> None:
    detector = LivenessDetector()
    face = _face_image()
    source_corners = np.asarray(
        [[0, 0], [191, 0], [191, 191], [0, 191]],
        dtype=np.float32,
    )
    base_landmarks = _base_landmarks()
    frames = []
    landmarks = [base_landmarks]
    for inset in (3.0, 7.0, 11.0, 15.0):
        target_corners = np.asarray(
            [
                [inset, 2],
                [191 - inset, 0],
                [191 - inset / 2, 191],
                [inset / 2, 189],
            ],
            dtype=np.float32,
        )
        homography = cv2.getPerspectiveTransform(source_corners, target_corners)
        frames.append(
            cv2.warpPerspective(
                face,
                homography,
                (192, 192),
                borderMode=cv2.BORDER_REFLECT,
            )
        )
        pixel_landmarks = base_landmarks * 191.0
        transformed = cv2.perspectiveTransform(
            pixel_landmarks.reshape(1, 5, 2),
            homography,
        ).reshape(5, 2)
        landmarks.append((transformed / 191.0).astype(np.float32))

    result = detector.analyze(face, frames, landmarks)

    assert result.is_live is False
    assert result.confidence < 0.5
    assert result.signals["depth_parallax"] == 0.0


def test_guided_head_turn_scores_above_seventy_percent() -> None:
    detector = LivenessDetector()
    face = _face_image()
    live_frames = []
    landmarks = [_base_landmarks()]
    for index, nose_shift in enumerate((0.015, 0.035, 0.055, 0.075), start=1):
        frame = face.copy()
        cv2.ellipse(
            frame,
            (96 + index, 139),
            (30, 7 + index),
            0,
            0,
            180,
            (45, 50, 105),
            3,
        )
        live_frames.append(frame)
        points = _base_landmarks()
        points[2, 0] += nose_shift
        points[3:, 0] += nose_shift * 0.35
        landmarks.append(points)

    result = detector.analyze(face, live_frames, landmarks)

    assert result.is_live is True
    assert result.confidence >= 0.70
    assert result.signals["pose_change"] >= 0.55
    assert result.signals["depth_parallax"] >= 0.55
    assert result.failure_reasons == []
