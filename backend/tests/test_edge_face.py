import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.face import edge_inference
from app.services.face.edge_inference import benchmark_edge_inference
from app.services.face.engine import DetectedFace


class _FakeEngine:
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding

    def analyze_faces(self, _: bytes) -> list[DetectedFace]:
        return [
            DetectedFace(
                embedding=self.embedding,
                region=np.zeros((8, 8, 3), dtype=np.uint8),
                bounding_box=(0, 0, 8, 8),
                landmarks=np.zeros((5, 2), dtype=np.float32),
                detection_confidence=0.99,
            )
        ]


class _FakeEdgeEngine(_FakeEngine):
    standard_parameter_bytes = 40 * 1024 * 1024
    edge_parameter_bytes = 10 * 1024 * 1024


def test_architecture_summary_is_explicit_about_demo_and_privacy() -> None:
    with TestClient(app) as client:
        response = client.get("/edge-face/architecture-summary")

    assert response.status_code == 200
    body = response.json()
    assert "Single-machine demonstration" in body["deployment_scope"]
    assert any("Raw face frames" in item for item in body["privacy_boundary"])
    assert any("sensitive biometric" in item for item in body["privacy_boundary"])
    assert "deliberately deprioritized gap" in body["project_status"]


def test_benchmark_reports_size_and_embedding_fidelity(monkeypatch) -> None:
    monkeypatch.setattr(
        edge_inference,
        "_benchmark_samples",
        lambda: ([b"local-frame"], "test frame"),
    )
    standard = _FakeEngine([1.0, 0.0])
    edge = _FakeEdgeEngine([0.8, 0.6])

    result = benchmark_edge_inference(standard, edge)

    assert result.standard.model_size_mb == 40.0
    assert result.edge_optimized.model_size_mb == 10.0
    assert result.size_reduction_percent == 75.0
    assert result.standard.accuracy_percent == 100.0
    assert result.edge_optimized.accuracy_percent == 80.0
    assert result.accuracy_delta_percentage_points == -20.0
    assert result.sample_count == 1


def test_calibration_batch_is_deterministic_and_non_biometric() -> None:
    first = edge_inference.EdgeOpenCVFaceEngine._calibration_batch()
    second = edge_inference.EdgeOpenCVFaceEngine._calibration_batch()

    assert first.shape == (8, 3, 112, 112)
    assert first.dtype == np.float32
    assert np.array_equal(first, second)
    assert float(first.min()) >= 0.0
    assert float(first.max()) <= 255.0
