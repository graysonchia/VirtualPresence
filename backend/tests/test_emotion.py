import numpy as np
import pytest

from app.services.face.emotion import EmotionDetector, PUBLIC_LABELS


def test_scores_are_mapped_to_requested_emotions() -> None:
    raw_scores = np.array(
        [0.2, 5.0, 0.1, -0.2, -0.3, -0.4, -0.5, 0.0],
        dtype=np.float32,
    )

    result = EmotionDetector.scores_to_result(raw_scores)

    assert result.label == "happy"
    assert set(result.scores) == set(PUBLIC_LABELS)
    assert sum(result.scores.values()) == pytest.approx(1.0)
    assert result.confidence == result.scores["happy"]


def test_contempt_probability_is_folded_into_neutral() -> None:
    raw_scores = np.array(
        [4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.0],
        dtype=np.float32,
    )

    result = EmotionDetector.scores_to_result(raw_scores)

    assert result.label == "neutral"
    assert "contempt" not in result.scores

