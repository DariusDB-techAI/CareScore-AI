from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..local_model_runner import get_classifier
from ..model_registry import MODEL_SPECS, CriterionModelSpec


CriterionEvaluator = Callable[[str], dict[str, Any]]


@dataclass(frozen=True)
class CriterionApiSpec:
    criterion: str
    display_name: str
    owner_hint: str
    evaluator: CriterionEvaluator


def build_result(
    *,
    criterion: str,
    score: int,
    confidence: float,
    summary: str,
    raw_label: str,
    probabilities: dict[str, float],
    status: str,
    model_hint: str,
) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "score": score,
        "confidence": round(confidence, 4),
        "summary": summary,
        "raw_label": raw_label,
        "probabilities": probabilities,
        "status": status,
        "model_hint": model_hint,
    }


def infer_with_local_model(transcript: str, spec: CriterionModelSpec) -> dict[str, Any]:
    classifier = get_classifier(spec.model_dir)
    prediction = classifier.predict(transcript, max_length=spec.max_length)
    raw_label = prediction["label"]
    score = spec.score_map.get(raw_label, 3)
    summary = spec.high_signal if score >= 4 else spec.low_signal
    return build_result(
        criterion=spec.criterion,
        score=score,
        confidence=float(prediction["confidence"]),
        summary=summary,
        raw_label=str(raw_label),
        probabilities=dict(prediction["probabilities"]),
        status="model",
        model_hint=str(spec.model_dir),
    )


def evaluate_with_spec(transcript: str, criterion: str) -> dict[str, Any]:
    spec = MODEL_SPECS[criterion]
    if not transcript.strip():
        return build_result(
            criterion=criterion,
            score=0,
            confidence=0.0,
            summary="Chua co noi dung hoi thoai de danh gia.",
            raw_label="empty",
            probabilities={},
            status="empty",
            model_hint="No transcript available",
        )

    try:
        if spec.is_available:
            return infer_with_local_model(transcript, spec)
    except Exception as exc:
        return build_result(
            criterion=criterion,
            score=0,
            confidence=0.0,
            summary=f"Khong the chay model local: {exc}",
            raw_label="error",
            probabilities={},
            status="error",
            model_hint=str(spec.model_dir),
        )

    return build_result(
        criterion=criterion,
        score=0,
        confidence=0.0,
        summary="Khong tim thay model local cho tieu chi nay.",
        raw_label="missing_model",
        probabilities={},
        status="missing_model",
        model_hint=str(spec.model_dir),
    )
