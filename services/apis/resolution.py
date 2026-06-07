from __future__ import annotations

from ..model_registry import MODEL_SPECS
from .base import build_result, evaluate_with_spec


RESOLUTION_POSITIVE_MARKERS = [
    "huong xu ly",
    "kiem tra",
    "de xuat",
    "cap nhat",
    "thoi gian",
    "xac nhan",
    "hoan tien",
    "doi tra",
    "ticket",
]
RESOLUTION_NEGATIVE_MARKERS = ["khong biet", "khong ro", "khong the", "khong ho tro", "tu lien he"]


def infer_resolution_fallback(transcript: str) -> dict[str, object]:
    spec = MODEL_SPECS["resolution"]
    lowered = transcript.lower()
    positive_hits = sum(marker in lowered for marker in RESOLUTION_POSITIVE_MARKERS)
    negative_hits = sum(marker in lowered for marker in RESOLUTION_NEGATIVE_MARKERS)
    score = 3
    raw_label = "partially_resolved"
    if positive_hits >= 2 and negative_hits == 0:
        score = 5
        raw_label = "resolved"
    elif positive_hits == 0 or negative_hits >= 2:
        score = 1
        raw_label = "unresolved"

    summary = spec.high_signal if score >= 4 else spec.low_signal
    return build_result(
        criterion=spec.criterion,
        score=score,
        confidence=0.62,
        summary=f"{summary} Dang dung fallback heuristic do chua tim thay local model.",
        raw_label=raw_label,
        probabilities={raw_label: 0.62},
        status="fallback",
        model_hint="Fallback heuristic for missing resolution model",
    )


def evaluate_resolution(transcript: str) -> dict[str, object]:
    base_result = evaluate_with_spec(transcript, "resolution")
    if base_result["status"] in {"missing_model", "error"}:
        try:
            return infer_resolution_fallback(transcript)
        except Exception as exc:
            fallback = infer_resolution_fallback(transcript)
            fallback["summary"] = f"{fallback['summary']} Loi model: {exc}"
            return fallback
    return base_result
