from __future__ import annotations

from .base import evaluate_with_spec


def evaluate_positivity(transcript: str) -> dict[str, object]:
    return evaluate_with_spec(transcript, "positivity")
