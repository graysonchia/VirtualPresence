from pathlib import Path
from urllib.request import urlopen


MODEL_DIR = Path(__file__).resolve().parents[1] / "app" / "services" / "face" / "models"
MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ),
    "face_recognition_sface_2021dec.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ),
    "emotion-ferplus-8.onnx": (
        "https://github.com/PINTO0309/onnx2tf/releases/download/"
        "1.1.1/emotion-ferplus-8.onnx"
    ),
}


def download(url: str, destination: Path) -> None:
    print(f"Downloading {destination.name}...")
    with urlopen(url, timeout=60) as response:
        content = response.read()
    if content.startswith(b"version https://git-lfs.github.com"):
        raise RuntimeError(
            f"{destination.name} resolved to a Git LFS pointer, not an ONNX model."
        )
    destination.write_bytes(content)
    print(f"Saved {destination} ({len(content):,} bytes)")


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in MODELS.items():
        destination = MODEL_DIR / filename
        if destination.exists() and destination.stat().st_size > 100_000:
            print(f"{filename} already exists; skipping.")
            continue
        download(url, destination)


if __name__ == "__main__":
    main()
