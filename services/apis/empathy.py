from __future__ import annotations

from .base import evaluate_with_spec


def evaluate_empathy(transcript: str) -> dict[str, object]:
    return evaluate_with_spec(transcript, "empathy")
