from __future__ import annotations

from .base import build_result
from ..local_model_runner import get_classifier
from ..model_registry import MODEL_SPECS


# Team positivity chi sua file nay.
# Trang tong va agent route "positivity" deu se di qua ham ben duoi.
MODEL_KEY = "positivity"


def evaluate_positivity(transcript: str) -> dict[str, object]:
    """
    Evaluate a conversation only for the positivity criterion.

    Input:
    - transcript: full conversation text, for example:
      "Khach hang: ...\nNhan vien: ..."

    Output schema:
    {
        "criterion": "positivity",
        "score": 1|3|5,
        "confidence": 0.0-1.0,
        "summary": "...",
        "raw_label": "positive|neutral|negative",
        "probabilities": {...},
        "status": "model|error|missing_model|empty",
        "model_hint": "path-or-model-id",
    }

    Current behavior:
    - Use the configured positivity model from model_registry.py
    - Do not call any other criterion model

    Later, the positivity owner can replace the body of this function with
    custom inference logic, as long as the returned dict keeps the same schema.
    """
    spec = MODEL_SPECS[MODEL_KEY]

    if not transcript.strip():
        return build_result(
            criterion=MODEL_KEY,
            score=0,
            confidence=0.0,
            summary="Chua co noi dung hoi thoai de danh gia.",
            raw_label="empty",
            probabilities={},
            status="empty",
            model_hint="No transcript available",
        )

    if not spec.is_available:
        return build_result(
            criterion=MODEL_KEY,
            score=0,
            confidence=0.0,
            summary="Khong tim thay model local cho tieu chi positivity.",
            raw_label="missing_model",
            probabilities={},
            status="missing_model",
            model_hint=str(spec.model_dir),
        )

    try:
        classifier = get_classifier(spec.model_dir)
        prediction = classifier.predict(transcript, max_length=spec.max_length)

        raw_label = prediction["label"]
        score = spec.score_map.get(raw_label, 3)
        summary = spec.high_signal if score >= 4 else spec.low_signal

        return build_result(
            criterion=MODEL_KEY,
            score=score,
            confidence=float(prediction["confidence"]),
            summary=summary,
            raw_label=str(raw_label),
            probabilities=dict(prediction["probabilities"]),
            status="model",
            model_hint=str(spec.model_dir),
        )
    except Exception as exc:
        return build_result(
            criterion=MODEL_KEY,
            score=0,
            confidence=0.0,
            summary=f"Khong the chay model positivity: {exc}",
            raw_label="error",
            probabilities={},
            status="error",
            model_hint=str(spec.model_dir),
        )
