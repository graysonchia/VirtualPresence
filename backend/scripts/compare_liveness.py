import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import cv2

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.face.engine import DetectedFace, get_face_engine  # noqa: E402
from app.services.face.liveness import (  # noqa: E402
    MINIMUM_BURST_FRAMES,
    LivenessResult,
    get_liveness_detector,
)


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
LIVE_TARGET = 0.70
SPOOF_TARGET = 0.50


def load_burst(directory: Path) -> list[DetectedFace]:
    paths = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if len(paths) < MINIMUM_BURST_FRAMES:
        raise ValueError(
            f"{directory} needs at least {MINIMUM_BURST_FRAMES} image frames."
        )

    engine = get_face_engine()
    return [engine.analyze_faces(path.read_bytes())[0] for path in paths]


def analyze_burst(faces: list[DetectedFace]) -> LivenessResult:
    detector = get_liveness_detector()
    return detector.analyze(
        faces[0].region,
        [face.region for face in faces[1:]],
        [face.landmarks for face in faces],
    )


def capture_comparison(camera_index: int) -> tuple[list[DetectedFace], list[DetectedFace]]:
    camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not camera.isOpened():
        raise RuntimeError(f"Could not open camera {camera_index}.")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    engine = get_face_engine()

    def capture(label: str) -> list[DetectedFace]:
        input(
            f"\nPrepare the {label} presentation, center the face, "
            "then press Enter. During capture, turn it gently left or right."
        )
        frames: list[DetectedFace] = []
        for index in range(MINIMUM_BURST_FRAMES):
            success, frame = camera.read()
            if not success:
                raise RuntimeError("The camera stopped returning frames.")
            encoded, buffer = cv2.imencode(".jpg", frame)
            if not encoded:
                raise RuntimeError("A camera frame could not be encoded.")
            frames.append(engine.analyze_faces(buffer.tobytes())[0])
            print(f"Captured {label} frame {index + 1}/{MINIMUM_BURST_FRAMES}")
            time.sleep(0.32)
        return frames

    try:
        for _ in range(8):
            camera.read()
        live_faces = capture("GENUINE LIVE FACE")
        spoof_faces = capture("HELD PHOTO OR SCREEN")
        return live_faces, spoof_faces
    finally:
        camera.release()


def result_payload(result: LivenessResult) -> dict[str, Any]:
    return {
        "is_live": result.is_live,
        "confidence": round(result.confidence, 4),
        "frames_analyzed": result.frames_analyzed,
        "signals": {
            name: round(value, 4)
            for name, value in result.signals.items()
        },
        "failure_reasons": result.failure_reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare five-frame genuine and presentation-attack captures. "
            "During the genuine burst, turn your head gently."
        )
    )
    parser.add_argument(
        "--live",
        type=Path,
        help="Directory containing at least five genuine live frames.",
    )
    parser.add_argument(
        "--spoof",
        type=Path,
        help="Directory containing at least five held-photo/screen frames.",
    )
    parser.add_argument(
        "--camera",
        type=int,
        help="Interactively capture both bursts from this camera index.",
    )
    args = parser.parse_args()

    if args.camera is not None:
        if args.live or args.spoof:
            parser.error("--camera cannot be combined with --live or --spoof.")
        live_faces, spoof_faces = capture_comparison(args.camera)
    else:
        if not args.live or not args.spoof:
            parser.error("provide both --live and --spoof, or use --camera.")
        live_faces = load_burst(args.live)
        spoof_faces = load_burst(args.spoof)

    live_result = analyze_burst(live_faces)
    spoof_result = analyze_burst(spoof_faces)
    calibration_passed = (
        live_result.confidence >= LIVE_TARGET
        and live_result.is_live
        and spoof_result.confidence < SPOOF_TARGET
        and not spoof_result.is_live
    )
    print(
        json.dumps(
            {
                "targets": {
                    "live_minimum": LIVE_TARGET,
                    "spoof_maximum": SPOOF_TARGET,
                },
                "live": result_payload(live_result),
                "spoof": result_payload(spoof_result),
                "calibration_passed": calibration_passed,
            },
            indent=2,
        )
    )
    return 0 if calibration_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
